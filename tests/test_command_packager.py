"""CommandPackager 集成测试。

使用 Mock TTS 服务来测试指令包装器的完整逻辑。
"""

import pytest
from typing import AsyncIterator
from core.models import ActionTag, ParsedSentence
from services.command_packager import CommandPackager
from services.sound_tag_converter import SoundTagConverter
from services.fallback_inference_service import RuleBasedFallbackService


class MockTTSService:
    """模拟 TTS 服务，返回固定的音频数据。"""

    async def synthesize_stream(
        self, text: str, emotion_instruction: str = "", voice_id: str = ""
    ) -> AsyncIterator[bytes]:
        yield b"mock_audio_" + text.encode("utf-8")[:20]


async def _sentence_stream(sentences):
    """辅助函数：将句子列表转换为异步迭代器。"""
    for s in sentences:
        yield s


@pytest.mark.asyncio
async def test_basic_packaging():
    """测试基本的句子打包。"""
    packager = CommandPackager(
        tts_service=MockTTSService(),
        sound_converter=SoundTagConverter(),
    )
    sentences = [
        ParsedSentence(
            text="你好！",
            tags=[ActionTag(tag_type="emotion", value="happy", instruction="开心")],
        ),
    ]

    results = []
    async for segment in packager.package_stream(_sentence_stream(sentences)):
        results.append(segment)

    assert len(results) == 1
    assert results[0].emotion == "happy"
    assert results[0].audio_content != b""
    assert "你好" in results[0].text


@pytest.mark.asyncio
async def test_sound_conversion_in_packaging():
    """测试音效标签在打包过程中被内生化。"""
    packager = CommandPackager(
        tts_service=MockTTSService(),
        sound_converter=SoundTagConverter(),
    )
    sentences = [
        ParsedSentence(
            text="哈哈哈！",
            tags=[
                ActionTag(tag_type="emotion", value="happy"),
                ActionTag(tag_type="sound", value="laugh"),
            ],
        ),
    ]

    results = []
    async for segment in packager.package_stream(_sentence_stream(sentences)):
        results.append(segment)

    assert len(results) == 1
    assert "[laughter]" in results[0].text
    # sound:laugh 不应出现在 actions 中（已被内生化）
    assert "sound:laugh" not in results[0].actions


@pytest.mark.asyncio
async def test_fallback_inference_triggered():
    """测试无情感标签时触发兜底推理。"""
    packager = CommandPackager(
        tts_service=MockTTSService(),
        sound_converter=SoundTagConverter(),
        fallback_service=RuleBasedFallbackService(),
    )
    sentences = [
        ParsedSentence(
            text="太棒了，我好开心！",
            tags=[],  # 无情感标签
        ),
    ]

    results = []
    async for segment in packager.package_stream(_sentence_stream(sentences)):
        results.append(segment)

    assert len(results) == 1
    assert results[0].emotion == "happy"  # 兜底推理应推断为 happy


@pytest.mark.asyncio
async def test_actions_extracted():
    """测试非情感动作被正确提取到 actions 列表。"""
    packager = CommandPackager(
        tts_service=MockTTSService(),
        sound_converter=SoundTagConverter(),
    )
    sentences = [
        ParsedSentence(
            text="你好！",
            tags=[
                ActionTag(tag_type="emotion", value="happy"),
                ActionTag(tag_type="expression", value="smile"),
                ActionTag(tag_type="animation", value="wave"),
            ],
        ),
    ]

    results = []
    async for segment in packager.package_stream(_sentence_stream(sentences)):
        results.append(segment)

    assert len(results) == 1
    assert "expression:smile" in results[0].actions
    assert "animation:wave" in results[0].actions


@pytest.mark.asyncio
async def test_empty_text_skipped():
    """测试空文本句子被跳过。"""
    packager = CommandPackager(
        tts_service=MockTTSService(),
        sound_converter=SoundTagConverter(),
    )
    sentences = [
        ParsedSentence(text="", tags=[]),
        ParsedSentence(text="   ", tags=[]),
        ParsedSentence(text="有内容。", tags=[]),
    ]

    results = []
    async for segment in packager.package_stream(_sentence_stream(sentences)):
        results.append(segment)

    assert len(results) == 1
    assert "有内容" in results[0].text


@pytest.mark.asyncio
async def test_multiple_sentences():
    """测试多句话的打包。"""
    packager = CommandPackager(
        tts_service=MockTTSService(),
        sound_converter=SoundTagConverter(),
    )
    sentences = [
        ParsedSentence(
            text="你好！",
            tags=[ActionTag(tag_type="emotion", value="happy")],
        ),
        ParsedSentence(
            text="再见。",
            tags=[ActionTag(tag_type="emotion", value="sad")],
            is_final=True,
        ),
    ]

    results = []
    async for segment in packager.package_stream(_sentence_stream(sentences)):
        results.append(segment)

    assert len(results) == 2
    assert results[0].emotion == "happy"
    assert results[1].emotion == "sad"
    assert results[1].is_final is True
