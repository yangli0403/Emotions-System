"""
Emotions-System — 动作解析器实现

从 LLM 的流式文本输出中解析多模态动作标签。
支持新的复合情感标签格式：[emotion:happy|instruction:语气活泼俏皮]
以及原有的 [tag:value] 格式。
"""

from __future__ import annotations

import logging
import re
from typing import AsyncIterator, List, Optional

from core.models import ActionTag, ParsedSentence

logger = logging.getLogger(__name__)


class ActionParser:
    """基于文本标签的动作解析器。

    解析 LLM 输出中的标签，将其转换为 ActionTag 对象。
    支持的标签格式：
        - [emotion:happy|instruction:语气活泼俏皮]  → 复合情感标签
        - [emotion:happy]                           → 简单情感标签
        - [sound:laugh]                             → 音效标签
        - [action:wave]                             → 动作标签
        - [expression:smile]                        → 表情标签
        - [pause:1.5]                               → 暂停标签
    """

    # 句子结束标点
    SENTENCE_DELIMITERS = {"。", "！", "？", "；", ".", "!", "?", ";", "\n"}

    # 复合情感标签正则：[emotion:value|instruction:text]
    COMPOUND_EMOTION_PATTERN = re.compile(
        r"\[emotion:(\w+)\|instruction:([^\]]+)\]"
    )

    # 简单标签正则：[tag:value]
    SIMPLE_TAG_PATTERN = re.compile(r"\[(\w+):([^\]|]+)\]")

    # 支持的标签类型
    KNOWN_TAG_TYPES = {
        "emotion", "sound", "sfx", "action", "expression", "expr",
        "animation", "anim", "gesture", "gest", "posture", "pose",
        "locomotion", "loco", "move", "pause", "wait",
    }

    # 标签类型归一化映射
    TAG_TYPE_NORMALIZE = {
        "expr": "expression",
        "anim": "animation",
        "gest": "gesture",
        "pose": "posture",
        "loco": "locomotion",
        "move": "locomotion",
        "sfx": "sound",
        "wait": "pause",
    }

    async def parse_stream(
        self, token_stream: AsyncIterator[str]
    ) -> AsyncIterator[ParsedSentence]:
        """解析 LLM 的流式输出，按句子边界切分并提取标签。

        Args:
            token_stream: LLM 输出的 Token 流。

        Yields:
            解析后的 ParsedSentence 对象。
        """
        buffer = ""
        current_tags: List[ActionTag] = []

        async for token in token_stream:
            buffer += token

            # 持续检查是否有完整的句子可以输出
            while True:
                # 先尝试提取所有完整的标签
                tags_extracted, buffer = self._extract_tags(buffer, current_tags)

                # 检查是否有未闭合的标签（等待更多 token）
                open_bracket = buffer.rfind("[")
                if open_bracket != -1 and "]" not in buffer[open_bracket:]:
                    break

                # 检查句子边界
                sentence_end_idx = self._find_sentence_end(buffer)
                if sentence_end_idx == -1:
                    break

                # 提取句子文本（不含标签）
                sentence_text = buffer[:sentence_end_idx + 1].strip()
                buffer = buffer[sentence_end_idx + 1:]

                if sentence_text:
                    yield ParsedSentence(
                        text=sentence_text,
                        tags=list(current_tags),
                        is_final=False,
                    )
                    current_tags = []

        # 处理剩余的 buffer
        if buffer.strip():
            tags_extracted, buffer = self._extract_tags(buffer, current_tags)
            if buffer.strip():
                yield ParsedSentence(
                    text=buffer.strip(),
                    tags=list(current_tags),
                    is_final=True,
                )

    def _extract_tags(
        self, text: str, tags_list: List[ActionTag]
    ) -> tuple[bool, str]:
        """从文本中提取所有完整的标签，返回剩余的纯文本。

        Args:
            text: 可能包含标签的文本。
            tags_list: 将提取到的标签追加到此列表。

        Returns:
            (是否提取到标签, 去除标签后的文本)
        """
        extracted = False

        # 先处理复合情感标签
        for match in self.COMPOUND_EMOTION_PATTERN.finditer(text):
            emotion_value = match.group(1).strip()
            instruction = match.group(2).strip()
            tags_list.append(ActionTag(
                tag_type="emotion",
                value=emotion_value,
                instruction=instruction,
            ))
            extracted = True
            logger.debug(
                f"解析到复合情感标签: emotion={emotion_value}, "
                f"instruction={instruction}"
            )

        text = self.COMPOUND_EMOTION_PATTERN.sub("", text)

        # 再处理简单标签
        for match in self.SIMPLE_TAG_PATTERN.finditer(text):
            tag_type = match.group(1).strip().lower()
            tag_value = match.group(2).strip()

            if tag_type not in self.KNOWN_TAG_TYPES:
                continue

            # 归一化标签类型
            normalized_type = self.TAG_TYPE_NORMALIZE.get(tag_type, tag_type)

            tags_list.append(ActionTag(
                tag_type=normalized_type,
                value=tag_value,
            ))
            extracted = True
            logger.debug(f"解析到标签: [{normalized_type}:{tag_value}]")

        text = self.SIMPLE_TAG_PATTERN.sub("", text)

        return extracted, text

    def _find_sentence_end(self, text: str) -> int:
        """查找文本中第一个句子结束标点的位置。

        Args:
            text: 待检查的文本。

        Returns:
            句子结束标点的索引，未找到返回 -1。
        """
        for i, char in enumerate(text):
            if char in self.SENTENCE_DELIMITERS:
                return i
        return -1
