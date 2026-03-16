"""
Emotions-System — 指令包装器实现

将解析后的 ParsedSentence 流结合 TTS 合成的音频，
打包成标准的 MultimodalSegment 对象。

核心逻辑：
1. 接收 ActionParser 输出的 ParsedSentence 流
2. 通过 SoundTagConverter 转换音效标签
3. 提取情感标签（emotion + instruction）
4. 如果没有情感标签，调用兜底推理服务
5. 调用 CosyVoice TTS 合成音频
6. 组装成 MultimodalSegment
"""

from __future__ import annotations

import base64
import logging
from typing import AsyncIterator, List, Optional

from core.interfaces import IFallbackInferenceService, ITTSService
from core.models import ActionTag, MultimodalSegment, ParsedSentence
from services.sound_tag_converter import SoundTagConverter

logger = logging.getLogger(__name__)


class CommandPackager:
    """指令包装器。

    将 ParsedSentence 流转换为 MultimodalSegment 流，
    中间经过音效标签转换和 TTS 合成。
    """

    def __init__(
        self,
        tts_service: ITTSService,
        sound_converter: SoundTagConverter,
        fallback_service: Optional[IFallbackInferenceService] = None,
        default_voice_id: str = "",
    ) -> None:
        """初始化指令包装器。

        Args:
            tts_service: TTS 服务实例。
            sound_converter: 音效标签转换器。
            fallback_service: 兜底推理服务（可选）。
            default_voice_id: 默认音色 ID。
        """
        self.tts_service = tts_service
        self.sound_converter = sound_converter
        self.fallback_service = fallback_service
        self.default_voice_id = default_voice_id

    async def package_stream(
        self,
        sentence_stream: AsyncIterator[ParsedSentence],
    ) -> AsyncIterator[MultimodalSegment]:
        """将 ParsedSentence 流打包成 MultimodalSegment 流。

        Args:
            sentence_stream: ActionParser 输出的句子流。

        Yields:
            组装完成的 MultimodalSegment 对象。
        """
        async for sentence in sentence_stream:
            segment = await self._build_segment(sentence)
            if segment:
                yield segment

    async def _build_segment(
        self, sentence: ParsedSentence
    ) -> Optional[MultimodalSegment]:
        """为一个句子构建 MultimodalSegment。

        Args:
            sentence: 解析后的句子。

        Returns:
            组装完成的 MultimodalSegment，或 None（如果文本为空）。
        """
        if not sentence.text.strip():
            return None

        # Step 1: 音效标签转换（[sound:laugh] → [laughter]）
        converted = self.sound_converter.convert(sentence)

        # Step 2: 提取情感信息
        emotion_base, emotion_instruction = self._extract_emotion(
            converted.tags
        )

        # Step 3: 如果没有情感标签，调用兜底推理
        if emotion_base == "neutral" and not emotion_instruction:
            has_emotion_tag = any(
                t.tag_type == "emotion" for t in converted.tags
            )
            if not has_emotion_tag and self.fallback_service:
                logger.info(
                    f"LLM 未提供情感标签，启用兜底推理。"
                    f"文本: {converted.text[:50]}"
                )
                try:
                    inferred = await self.fallback_service.infer_emotion(
                        converted.text
                    )
                    emotion_base = inferred.value
                    emotion_instruction = inferred.instruction
                except Exception as e:
                    logger.warning(f"兜底推理失败: {e}")

        # Step 4: 调用 TTS 合成音频
        audio_data = b""
        try:
            async for chunk in self.tts_service.synthesize_stream(
                text=converted.text,
                emotion_instruction=emotion_instruction,
                voice_id=self.default_voice_id,
            ):
                audio_data += chunk
        except Exception as e:
            logger.error(f"TTS 合成失败: {e}")

        # Step 5: 提取非情感动作列表
        actions = [
            f"{t.tag_type}:{t.value}"
            for t in converted.tags
            if t.tag_type != "emotion"
        ]

        segment = MultimodalSegment(
            audio_content=audio_data,
            text=converted.text,
            emotion=emotion_base,
            actions=actions,
            is_final=converted.is_final,
        )

        logger.info(
            f"组装片段: emotion={emotion_base}, "
            f"instruction={emotion_instruction[:30] if emotion_instruction else 'N/A'}..., "
            f"actions={len(actions)}, "
            f"audio={len(audio_data)} bytes, "
            f"text={converted.text[:30]}..."
        )
        return segment

    @staticmethod
    def _extract_emotion(
        tags: List[ActionTag],
    ) -> tuple[str, str]:
        """从标签列表中提取情感信息。

        优先使用最后一个 emotion 类型的标签。

        Args:
            tags: 标签列表。

        Returns:
            (基础情感枚举, 自然语言指令) 元组。
        """
        emotion_base = "neutral"
        emotion_instruction = ""

        for tag in tags:
            if tag.tag_type == "emotion":
                emotion_base = tag.value
                emotion_instruction = tag.instruction

        return emotion_base, emotion_instruction
