"""Emotions-System 核心模块：数据模型与接口定义。"""

from .models import ActionTag, ParsedSentence, MultimodalSegment, VoiceCloneConfig
from .interfaces import (
    ILLMService,
    ITTSService,
    IVoiceCloningService,
    IFallbackInferenceService,
    IProtocolAdapter,
)

__all__ = [
    "ActionTag",
    "ParsedSentence",
    "MultimodalSegment",
    "VoiceCloneConfig",
    "ILLMService",
    "ITTSService",
    "IVoiceCloningService",
    "IFallbackInferenceService",
    "IProtocolAdapter",
]
