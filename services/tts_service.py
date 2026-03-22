"""
Emotions-System — CosyVoice TTS 服务实现

基于阿里百炼 DashScope SDK 的 CosyVoice 语音合成服务。
支持：
- 情感自然语言指令控制（instruction）
- 双向流式合成（基于 ResultCallback）
- 复刻音色调用
- [laughter] / [breath] 内生标记
- 多版本模型切换（v1 / v3-flash / v3.5-flash / v3.5-plus）
"""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import AsyncIterator, Dict, List, Optional

from core.interfaces import ITTSService

logger = logging.getLogger(__name__)

# 基础情感枚举 → 默认自然语言指令的映射
# 当 LLM 只提供了基础枚举而没有 instruction 时使用
DEFAULT_EMOTION_INSTRUCTIONS: Dict[str, str] = {
    "neutral": "用平静温和的语气说话。",
    "happy": "用开心愉悦的语气说话，带着笑意。",
    "sad": "用低沉哀伤的语气说话，带有轻微叹息。",
    "angry": "用严厉不满的语气说话，带有压抑的怒意。",
    "surprised": "用充满惊讶的语气说话，语调上扬。",
    "fearful": "用紧张颤抖的语气说话，充满恐惧。",
    "disgusted": "用厌恶不屑的语气说话。",
}

# 各版本模型的默认音色映射
MODEL_DEFAULT_VOICES: Dict[str, str] = {
    "cosyvoice-v1": "longxiaochun",
    "cosyvoice-v2": "longxiaochun_v2",
    "cosyvoice-v3-flash": "longanyang",
    "cosyvoice-v3-plus": "longanyang",
    "cosyvoice-v3.5-flash": "",   # 无系统音色，需复刻音色
    "cosyvoice-v3.5-plus": "",    # 无系统音色，需复刻音色
}


class CosyVoiceTTSService(ITTSService):
    """基于阿里百炼 CosyVoice API 的 TTS 服务实现。

    使用 DashScope SDK 调用 CosyVoice 模型进行语音合成。
    支持双向流式合成以降低首字响应延迟。
    支持通过 model_override 参数临时切换模型版本进行对比测试。
    """

    def __init__(
        self,
        api_key: str = "",
        model: str = "cosyvoice-v1",
        default_voice: str = "longxiaochun",
    ) -> None:
        """初始化 CosyVoice TTS 服务。

        Args:
            api_key: DashScope API 密钥。
            model: CosyVoice 模型版本。
            default_voice: 默认音色 ID。
        """
        self.api_key = api_key
        self.model = model
        self.default_voice = default_voice
        logger.info(
            f"CosyVoice TTS 服务初始化: model={model}, "
            f"default_voice={default_voice}"
        )

    def _get_instruction(
        self, emotion_instruction: str, emotion_base: str = "neutral"
    ) -> str:
        """获取最终的情感指令文本。

        优先使用 LLM 提供的自然语言指令，如果没有则使用默认映射。

        Args:
            emotion_instruction: LLM 提供的自然语言情感指令。
            emotion_base: 基础情感枚举值。

        Returns:
            最终的情感指令文本（不超过100字符）。
        """
        if emotion_instruction and emotion_instruction.strip():
            instruction = emotion_instruction.strip()
        else:
            instruction = DEFAULT_EMOTION_INSTRUCTIONS.get(
                emotion_base, DEFAULT_EMOTION_INSTRUCTIONS["neutral"]
            )
        # CosyVoice instruction 限制 100 字符
        return instruction[:100]

    def _resolve_voice(self, voice_id: str, model: str) -> str:
        """根据模型版本解析实际使用的音色。

        Args:
            voice_id: 用户指定的音色 ID。
            model: 当前使用的模型版本。

        Returns:
            实际使用的音色 ID。
        """
        if voice_id:
            return voice_id
        # 如果用户没指定音色，使用对应版本的默认音色
        default = MODEL_DEFAULT_VOICES.get(model, "")
        if default:
            return default
        # v3.5 没有系统音色，回退到 v1 默认音色
        return self.default_voice

    async def synthesize_stream(
        self,
        text: str,
        emotion_instruction: str = "",
        voice_id: str = "",
        model_override: Optional[str] = None,
    ) -> AsyncIterator[bytes]:
        """双向流式合成语音。

        使用 DashScope SDK 的 SpeechSynthesizer + ResultCallback 进行流式合成。
        文本中可包含 [laughter]、[breath] 等 CosyVoice 内生标记。

        Args:
            text: 要合成的文本（可能包含 CosyVoice 标记）。
            emotion_instruction: 情感自然语言指令。
            voice_id: 复刻音色 ID 或系统内置音色 ID。
            model_override: 临时覆盖的模型版本（用于 A/B 对比测试）。

        Yields:
            音频数据块（WAV 格式）。
        """
        if not text or not text.strip():
            logger.warning("TTS 收到空文本，跳过合成")
            return

        # 确定实际使用的模型版本
        actual_model = model_override if model_override else self.model
        voice = self._resolve_voice(voice_id, actual_model)
        instruction = self._get_instruction(emotion_instruction)

        logger.info(
            f"CosyVoice 流式合成: model={actual_model}, voice={voice}, "
            f"instruction={instruction[:30]}..., "
            f"text={text[:50]}..."
        )

        try:
            import dashscope
            from dashscope.audio.tts_v2 import (
                SpeechSynthesizer,
                AudioFormat,
                ResultCallback,
            )

            if self.api_key:
                dashscope.api_key = self.api_key

            # 使用 ResultCallback 收集音频数据
            class _AudioCollector(ResultCallback):
                def __init__(self):
                    self.audio_chunks: List[bytes] = []
                    self.error: Optional[str] = None
                    self.completed = threading.Event()

                def on_open(self):
                    logger.debug("CosyVoice 流已打开")

                def on_data(self, data, **kwargs):
                    if data:
                        self.audio_chunks.append(data)

                def on_complete(self):
                    logger.debug("CosyVoice 流已完成")
                    self.completed.set()

                def on_error(self, message, **kwargs):
                    self.error = str(message)
                    logger.error(f"CosyVoice 流错误: {message}")
                    self.completed.set()

                def on_close(self):
                    logger.debug("CosyVoice 流已关闭")
                    self.completed.set()

                def on_event(self, message, **kwargs):
                    pass

            collector = _AudioCollector()

            # 构建 SpeechSynthesizer 参数
            synth_kwargs = dict(
                model=actual_model,
                voice=voice,
                format=AudioFormat.WAV_22050HZ_MONO_16BIT,
                callback=collector,
            )

            # instruction 参数支持情况：
            # v1: 支持（系统音色）
            # v3-flash: 支持（复刻音色 + 部分系统音色）
            # v3.5-flash/plus: 支持（仅复刻/设计音色）
            if instruction:
                synth_kwargs["instruction"] = instruction

            synthesizer = SpeechSynthesizer(**synth_kwargs)

            # 分片发送文本以实现流式效果
            chunk_size = 20
            text_chunks = [
                text[i:i + chunk_size]
                for i in range(0, len(text), chunk_size)
            ]

            for chunk in text_chunks:
                synthesizer.streaming_call(chunk)
                await asyncio.sleep(0)  # 让出事件循环

            # 完成发送
            synthesizer.streaming_complete()

            # 等待回调完成
            collector.completed.wait(timeout=30)

            if collector.error:
                logger.error(f"CosyVoice 合成错误 (model={actual_model}): {collector.error}")
                raise RuntimeError(
                    f"CosyVoice 合成失败 (model={actual_model}): {collector.error}"
                )

            # 合并所有音频块
            if collector.audio_chunks:
                audio_data = b"".join(collector.audio_chunks)
                yield audio_data
                logger.info(
                    f"CosyVoice 合成完成: model={actual_model}, "
                    f"{len(audio_data)} bytes, "
                    f"{len(collector.audio_chunks)} chunks"
                )
            else:
                logger.warning(f"CosyVoice 合成返回空音频 (model={actual_model})")

        except ImportError:
            logger.error(
                "dashscope 未安装，请执行: pip install dashscope"
            )
            raise RuntimeError("dashscope SDK 未安装")
        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"CosyVoice 合成失败 (model={actual_model}): {e}", exc_info=True)
            raise RuntimeError(f"CosyVoice 合成失败 (model={actual_model}): {e}") from e

    async def synthesize_full(
        self,
        text: str,
        emotion_instruction: str = "",
        voice_id: str = "",
        model_override: Optional[str] = None,
    ) -> bytes:
        """非流式完整合成语音（用于短文本或测试）。

        Args:
            text: 要合成的文本。
            emotion_instruction: 情感自然语言指令。
            voice_id: 音色 ID。
            model_override: 临时覆盖的模型版本（用于 A/B 对比测试）。

        Returns:
            完整的音频数据（WAV 格式）。
        """
        audio_chunks = []
        async for chunk in self.synthesize_stream(
            text, emotion_instruction, voice_id, model_override
        ):
            audio_chunks.append(chunk)
        return b"".join(audio_chunks)

    async def synthesize_to_file(
        self,
        text: str,
        output_path: str,
        emotion_instruction: str = "",
        voice_id: str = "",
        model_override: Optional[str] = None,
    ) -> str:
        """合成语音并保存为独立的音频文件。

        Args:
            text: 要合成的文本（可包含 [laughter]、[breath] 等标记）。
            output_path: 输出音频文件的完整路径。
            emotion_instruction: 情感自然语言指令。
            voice_id: 复刻音色 ID 或系统内置音色 ID。
            model_override: 临时覆盖的模型版本。

        Returns:
            实际保存的文件路径。

        Raises:
            RuntimeError: 合成或写入失败时抛出。
        """
        from pathlib import Path

        audio_data = await self.synthesize_full(
            text, emotion_instruction, voice_id, model_override
        )

        if not audio_data:
            raise RuntimeError(f"合成结果为空，无法保存文件: {output_path}")

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        with open(out, "wb") as f:
            f.write(audio_data)

        logger.info(
            f"音频已保存: {output_path} ({len(audio_data)} bytes)"
        )
        return str(out)
