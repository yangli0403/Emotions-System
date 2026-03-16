"""
Emotions-System — 主入口

FastAPI 应用，提供 WebSocket 和 REST API 接口。
"""

from __future__ import annotations

import json
import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.responses import JSONResponse

from config import AppConfig
from services.llm_service import OpenAILLMService
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。"""
    global orchestrator, voice_cloning_service

    logger.info("Emotions-System 启动中...")

    # 加载配置
    config = AppConfig.from_env()

    # 初始化各服务
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
    """上传音频并创建复刻音色。

    Args:
        audio: 参考音频文件（WAV/MP3，3-10秒清晰人声）。
        name: 自定义音色名称。
    """
    if not voice_cloning_service:
        return JSONResponse(
            status_code=503,
            content={"error": "声音复刻服务未初始化"},
        )

    # 保存上传的音频到临时文件
    upload_dir = Path("data/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    temp_path = upload_dir / f"{uuid.uuid4()}{Path(audio.filename).suffix}"

    try:
        content = await audio.read()
        with open(temp_path, "wb") as f:
            f.write(content)

        # 调用复刻服务
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


@app.get("/health")
async def health_check():
    """健康检查端点。"""
    return {"status": "ok", "service": "Emotions-System"}
