"""
Emotions-System — 音效标签转换器

将 EE 格式的音效标签（如 [sound:laugh]）转换为 CosyVoice 可识别的
文本内标记（如 [laughter]），让音效直接融入语音流中。

对于 CosyVoice 不支持的音效，保留原始标签供前端独立播放。
"""

from __future__ import annotations

import logging
from typing import List

from core.models import ActionTag, ParsedSentence

logger = logging.getLogger(__name__)


class SoundTagConverter:
    """音效标签转换器。

    拦截 ParsedSentence 中的 sound 类型标签，将支持的音效
    转换为 CosyVoice 的文本内标记，附加到句子文本中。
    """

    # EE 音效标签 → CosyVoice 文本内标记 的映射
    # CosyVoice 支持 [laughter] 和 [breath] 两种内生标记
    COSYVOICE_SOUND_MAP = {
        "laugh": "[laughter]",
        "chuckle": "[laughter]",
        "giggle": "[laughter]",
        "sigh": "[breath]",
        "gasp": "[breath]",
        "breath": "[breath]",
    }

    # 不支持内生化的音效，保留给前端独立播放
    PASSTHROUGH_SOUNDS = {
        "applause", "heartbeat", "wind", "sparkle",
        "thunder", "whoosh", "rain", "bell",
    }

    def convert(self, sentence: ParsedSentence) -> ParsedSentence:
        """转换句子中的音效标签。

        对于可内生化的音效（laugh → [laughter]），将标记附加到文本末尾，
        并从标签列表中移除该音效标签。
        对于不可内生化的音效，保留在标签列表中。

        Args:
            sentence: 包含音效标签的解析句子。

        Returns:
            转换后的 ParsedSentence（新对象）。
        """
        converted_tags: List[ActionTag] = []
        text_suffix = ""

        for tag in sentence.tags:
            if tag.tag_type == "sound":
                cosyvoice_marker = self.COSYVOICE_SOUND_MAP.get(
                    tag.value.lower()
                )
                if cosyvoice_marker:
                    # 将音效标记附加到文本末尾
                    text_suffix += cosyvoice_marker
                    logger.info(
                        f"音效内生化: [sound:{tag.value}] → {cosyvoice_marker}"
                    )
                else:
                    # 不支持内生化，保留标签
                    converted_tags.append(tag)
                    logger.debug(
                        f"音效保留给前端: [sound:{tag.value}]"
                    )
            else:
                # 非音效标签，原样保留
                converted_tags.append(tag)

        # 构建新的文本：原文本 + 内生化的音效标记
        new_text = sentence.text
        if text_suffix:
            new_text = sentence.text + text_suffix

        return ParsedSentence(
            text=new_text,
            tags=converted_tags,
            is_final=sentence.is_final,
        )
