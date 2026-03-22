"""
Emotions-System — 主入口

FastAPI 应用，提供 WebSocket 和 REST API 接口。
支持多种 LLM 后端：OpenAI 兼容 API、字节火山引擎 Ark SDK。
"""

from __future__ import annotations

import os
from dotenv import load_dotenv
load_dotenv()  # 加载 .env 文件

import json
import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from config import AppConfig
from services.llm_service import OpenAILLMService, ArkLLMService
from services.tts_service import CosyVoiceTTSService
from services.voice_cloning_service import DashScopeVoiceCloningService
from services.action_parser import ActionParser
from services.sound_tag_converter import SoundTagConverter
from services.command_packager import CommandPackager
from services.fallback_inference_service import RuleBasedFallbackService
from services.orchestrator import Orchestrator
from adapters.protocol_adapter import OpenLLMVTuberAdapter

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

# 全局组件引用
orchestrator: Optional[Orchestrator] = None
voice_cloning_service: Optional[DashScopeVoiceCloningService] = None
tts_service: Optional[CosyVoiceTTSService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。"""
    global orchestrator, voice_cloning_service, tts_service

    logger.info("Emotions-System 启动中...")

    # 加载配置
    config = AppConfig.from_env()

    # 根据 backend 类型初始化 LLM 服务
    if config.llm.backend == "ark":
        logger.info("使用字节火山引擎 Ark SDK 作为 LLM 后端")
        llm_service = ArkLLMService(
            api_key=config.llm.api_key,
            model=config.llm.model,
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens,
        )
    else:
        logger.info("使用 OpenAI 兼容 API 作为 LLM 后端")
        llm_service = OpenAILLMService(
            api_key=config.llm.api_key,
            base_url=config.llm.base_url,
            model=config.llm.model,
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens,
        )

    tts_service = CosyVoiceTTSService(
        api_key=config.tts.api_key,
        model=config.tts.model,
        default_voice=config.tts.default_voice,
    )

    voice_cloning_service = DashScopeVoiceCloningService(
        api_key=config.voice_clone.api_key,
        config_path=config.voice_clone.config_path,
    )

    action_parser = ActionParser()
    sound_converter = SoundTagConverter()
    fallback_service = RuleBasedFallbackService()

    command_packager = CommandPackager(
        tts_service=tts_service,
        sound_converter=sound_converter,
        fallback_service=fallback_service,
        default_voice_id=config.tts.default_voice,
    )

    protocol_adapter = OpenLLMVTuberAdapter()

    orchestrator = Orchestrator(
        llm_service=llm_service,
        action_parser=action_parser,
        command_packager=command_packager,
        protocol_adapter=protocol_adapter,
    )

    logger.info("Emotions-System 启动完成")
    yield
    logger.info("Emotions-System 关闭")


app = FastAPI(
    title="Emotions-System",
    description="情感驱动的多模态语音合成系统",
    version="1.0.0",
    lifespan=lifespan,
)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 端点，处理实时对话。"""
    await websocket.accept()
    session_id = str(uuid.uuid4())
    logger.info(f"WebSocket 连接建立: session={session_id}")

    try:
        while True:
            # 接收用户消息
            data = await websocket.receive_text()
            message = json.loads(data)

            user_text = message.get("text", "")
            if not user_text:
                await websocket.send_json({
                    "type": "info",
                    "message": "请输入文本",
                })
                continue

            # 处理并流式返回
            async for response in orchestrator.handle_text_input(
                session_id, user_text
            ):
                await websocket.send_json(response)

    except WebSocketDisconnect:
        logger.info(f"WebSocket 连接断开: session={session_id}")
        orchestrator.clear_history(session_id)
    except Exception as e:
        logger.error(f"WebSocket 错误: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e),
            })
        except Exception:
            pass


# ========== REST API: 声音复刻管理 ==========

@app.post("/api/voice/clone")
async def clone_voice(
    audio: UploadFile = File(...),
    name: str = Form(...),
):
    """上传音频并创建复刻音色。"""
    if not voice_cloning_service:
        return JSONResponse(
            status_code=503,
            content={"error": "声音复刻服务未初始化"},
        )

    upload_dir = Path("data/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    temp_path = upload_dir / f"{uuid.uuid4()}{Path(audio.filename).suffix}"

    try:
        content = await audio.read()
        with open(temp_path, "wb") as f:
            f.write(content)

        config = await voice_cloning_service.clone_voice(
            str(temp_path), name
        )

        return JSONResponse(content={
            "success": True,
            "voice_id": config.voice_id,
            "name": config.name,
            "description": config.description,
        })

    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)},
        )
    except RuntimeError as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )


@app.get("/api/voice/list")
async def list_voices():
    """获取所有可用的复刻音色。"""
    if not voice_cloning_service:
        return JSONResponse(
            status_code=503,
            content={"error": "声音复刻服务未初始化"},
        )

    voices = await voice_cloning_service.list_voices()
    return JSONResponse(content={
        "voices": [v.model_dump() for v in voices],
    })


@app.delete("/api/voice/{voice_id}")
async def delete_voice(voice_id: str):
    """删除一个复刻音色。"""
    if not voice_cloning_service:
        return JSONResponse(
            status_code=503,
            content={"error": "声音复刻服务未初始化"},
        )

    success = await voice_cloning_service.delete_voice(voice_id)
    if success:
        return JSONResponse(content={"success": True})
    else:
        return JSONResponse(
            status_code=404,
            content={"error": f"音色 {voice_id} 不存在"},
        )


# ========== REST API: 单独合成音频文件 ==========

@app.post("/api/tts/synthesize")
async def synthesize_audio(
    text: str = Form(...),
    emotion_instruction: str = Form(""),
    voice_id: str = Form(""),
    tts_model: str = Form(""),
):
    """单独合成一段音频并返回 WAV 文件。支持通过 tts_model 参数临时切换模型版本。"""
    from fastapi.responses import Response

    if not tts_service:
        return JSONResponse(
            status_code=503,
            content={"error": "TTS 服务未初始化"},
        )

    try:
        audio_data = await tts_service.synthesize_full(
            text=text,
            emotion_instruction=emotion_instruction,
            voice_id=voice_id,
            model_override=tts_model if tts_model else None,
        )
        if not audio_data:
            return JSONResponse(
                status_code=500,
                content={"error": "合成结果为空"},
            )
        return Response(
            content=audio_data,
            media_type="audio/wav",
            headers={
                "Content-Disposition": "attachment; filename=synthesized.wav"
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )


@app.post("/api/tts/synthesize-to-file")
async def synthesize_to_file(
    text: str = Form(...),
    output_filename: str = Form("output.wav"),
    emotion_instruction: str = Form(""),
    voice_id: str = Form(""),
):
    """合成音频并保存到服务器本地文件。"""
    if not tts_service:
        return JSONResponse(
            status_code=503,
            content={"error": "TTS 服务未初始化"},
        )

    output_path = Path("data/output") / output_filename
    try:
        saved_path = await tts_service.synthesize_to_file(
            text=text,
            output_path=str(output_path),
            emotion_instruction=emotion_instruction,
            voice_id=voice_id,
        )
        return JSONResponse(content={
            "success": True,
            "file_path": saved_path,
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )


@app.get("/api/tts/models")
async def list_tts_models():
    """获取可用的 TTS 模型版本列表。"""
    return JSONResponse(content={
        "models": [
            {
                "id": "cosyvoice-v1",
                "name": "CosyVoice v1",
                "description": "支持 instruction 情感指令，性价比最高（1元/万字符）",
                "voices": ["longxiaochun", "longwan", "longhua", "longyuan",
                           "longxiaoxia", "longshuo", "longjing", "longmiao",
                           "longfei", "longyue"],
                "supports_instruction": True,
                "supports_system_voice": True,
            },
            {
                "id": "cosyvoice-v3-flash",
                "name": "CosyVoice v3 Flash",
                "description": "支持 instruction、SSML、多语种，速度快",
                "voices": ["longanyang", "longxiaocheng", "longshu",
                           "longyingjing_v3", "longlaotie_v3"],
                "supports_instruction": True,
                "supports_system_voice": True,
            },
            {
                "id": "cosyvoice-v3.5-flash",
                "name": "CosyVoice v3.5 Flash (最新)",
                "description": "最新版本，任意指令控制，仅支持复刻/设计音色",
                "voices": [],
                "supports_instruction": True,
                "supports_system_voice": False,
            },
            {
                "id": "cosyvoice-v3.5-plus",
                "name": "CosyVoice v3.5 Plus (最新)",
                "description": "最新版本，最高质量，仅支持复刻/设计音色",
                "voices": [],
                "supports_instruction": True,
                "supports_system_voice": False,
            },
        ],
        "current_default": tts_service.model if tts_service else "cosyvoice-v1",
    })


@app.get("/health")
async def health_check():
    """健康检查端点。"""
    return {"status": "ok", "service": "Emotions-System"}


# 挂载静态文件目录（Web 测试前端）
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
