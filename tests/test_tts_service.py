"""CosyVoiceTTSService 单元测试。"""

import pytest
from services.tts_service import CosyVoiceTTSService, DEFAULT_EMOTION_INSTRUCTIONS


def test_init():
    """测试 TTS 服务初始化。"""
    service = CosyVoiceTTSService(
        api_key="test_key",
        model="cosyvoice-v2",
        default_voice="longxiaochun",
    )
    assert service.api_key == "test_key"
    assert service.model == "cosyvoice-v2"
    assert service.default_voice == "longxiaochun"


def test_get_instruction_with_custom():
    """测试自定义情感指令优先。"""
    service = CosyVoiceTTSService()
    instruction = service._get_instruction("语气活泼俏皮", "happy")
    assert instruction == "语气活泼俏皮"


def test_get_instruction_fallback():
    """测试无自定义指令时使用默认映射。"""
    service = CosyVoiceTTSService()
    instruction = service._get_instruction("", "happy")
    assert instruction == DEFAULT_EMOTION_INSTRUCTIONS["happy"]


def test_get_instruction_unknown_emotion():
    """测试未知情感枚举时使用 neutral 默认。"""
    service = CosyVoiceTTSService()
    instruction = service._get_instruction("", "unknown_emotion")
    assert instruction == DEFAULT_EMOTION_INSTRUCTIONS["neutral"]


def test_get_instruction_truncation():
    """测试超长指令被截断到100字符。"""
    service = CosyVoiceTTSService()
    long_instruction = "这是一段非常长的情感指令" * 20
    instruction = service._get_instruction(long_instruction)
    assert len(instruction) <= 100


def test_default_emotion_instructions_complete():
    """测试所有7种基础情感都有默认指令。"""
    expected_emotions = {
        "neutral", "happy", "sad", "angry",
        "surprised", "fearful", "disgusted",
    }
    assert set(DEFAULT_EMOTION_INSTRUCTIONS.keys()) == expected_emotions


@pytest.mark.asyncio
async def test_synthesize_stream_empty_text():
    """测试空文本不产生音频。"""
    service = CosyVoiceTTSService(api_key="test")
    chunks = []
    async for chunk in service.synthesize_stream("", "", ""):
        chunks.append(chunk)
    assert len(chunks) == 0


@pytest.mark.asyncio
async def test_synthesize_stream_whitespace():
    """测试纯空白文本不产生音频。"""
    service = CosyVoiceTTSService(api_key="test")
    chunks = []
    async for chunk in service.synthesize_stream("   ", "", ""):
        chunks.append(chunk)
    assert len(chunks) == 0
