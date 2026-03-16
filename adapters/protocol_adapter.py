"""
Emotions-System — 协议适配器实现

将内部标准的 MultimodalSegment 对象转换为
前端兼容的 WebSocket JSON 消息格式。

支持 Open-LLM-VTuber 协议格式。
"""

from __future__ import annotations

import base64
import logging
from typing import Dict, List, Optional

from core.interfaces import IProtocolAdapter
from core.models import MultimodalSegment

logger = logging.getLogger(__name__)


class OpenLLMVTuberAdapter(IProtocolAdapter):
    """Open-LLM-VTuber 前端协议适配器。

    负责将内部的 MultimodalSegment 转换为 Open-LLM-VTuber
    前端 WebSocket 协议所期望的 JSON 格式。

    输出格式示例：
    {
        "type": "audio",
        "audio": "<base64_audio>",
        "audio_format": "wav",
        "text": "...",
        "emotion": "happy",
        "emotion_instruction": "语气活泼俏皮",
        "actions": ["expression:smile", "gesture:thumbs_up"],
        "is_final": false
    }
    """

    # 动作类型分类
    ACTION_CATEGORIES = {
        "expression", "animation", "gesture", "posture",
        "locomotion", "sound",
    }

    def adapt(self, segment: MultimodalSegment) -> dict:
        """将 MultimodalSegment 转换为前端兼容的 JSON。

        Args:
            segment: 内部标准格式的多模态片段。

        Returns:
            符合 WebSocket 协议的 JSON 字典。
        """
        # Base64 编码音频
        audio_b64 = ""
        if segment.audio_content:
            audio_b64 = base64.b64encode(
                segment.audio_content
            ).decode("utf-8")

        # 构建前端兼容的消息
        message: dict = {
            "type": "audio",
            "text": segment.text,
            "emotion": segment.emotion,
            "is_final": segment.is_final,
        }

        # 音频数据
        if audio_b64:
            message["audio"] = audio_b64
            message["audio_format"] = "wav"

        # 按类型分组动作
        categorized = self._categorize_actions(segment.actions)
        for category, value in categorized.items():
            message[category] = value

        # 完整动作列表（供前端高级处理）
        if segment.actions:
            message["actions"] = segment.actions

        logger.debug(
            f"协议适配: emotion={segment.emotion}, "
            f"actions={len(segment.actions)}, "
            f"audio={len(segment.audio_content)} bytes, "
            f"text={segment.text[:30]}..."
        )
        return message

    @staticmethod
    def _categorize_actions(
        actions: List[str],
    ) -> Dict[str, str]:
        """将动作列表按类型分组，每个类型取最后一个值。

        Args:
            actions: 动作字符串列表，格式为 "type:value"。

        Returns:
            {类型: 值} 字典。
        """
        result: Dict[str, str] = {}
        for action_str in actions:
            if ":" in action_str:
                parts = action_str.split(":", 1)
                action_type = parts[0].strip()
                action_value = parts[1].strip()
                result[action_type] = action_value
        return result
