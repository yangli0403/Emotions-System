"""Core Models 单元测试。"""

import pytest
from core.models import ActionTag, ParsedSentence, MultimodalSegment, VoiceCloneConfig


def test_action_tag_defaults():
    """测试 ActionTag 默认值。"""
    tag = ActionTag(tag_type="emotion", value="happy")
    assert tag.instruction == ""


def test_action_tag_with_instruction():
    """测试 ActionTag 带 instruction。"""
    tag = ActionTag(
        tag_type="emotion",
        value="happy",
        instruction="语气活泼俏皮",
    )
    assert tag.instruction == "语气活泼俏皮"


def test_parsed_sentence_defaults():
    """测试 ParsedSentence 默认值。"""
    sentence = ParsedSentence(text="你好")
    assert sentence.tags == []
    assert sentence.is_final is False


def test_parsed_sentence_with_tags():
    """测试 ParsedSentence 带标签。"""
    tags = [
        ActionTag(tag_type="emotion", value="happy"),
        ActionTag(tag_type="sound", value="laugh"),
    ]
    sentence = ParsedSentence(text="你好！", tags=tags, is_final=True)
    assert len(sentence.tags) == 2
    assert sentence.is_final is True


def test_multimodal_segment_defaults():
    """测试 MultimodalSegment 默认值。"""
    segment = MultimodalSegment(audio_content=b"data", text="你好")
    assert segment.emotion == "neutral"
    assert segment.actions == []
    assert segment.is_final is False


def test_multimodal_segment_full():
    """测试 MultimodalSegment 完整构造。"""
    segment = MultimodalSegment(
        audio_content=b"\x00\x01",
        text="你好！",
        emotion="happy",
        actions=["expression:smile", "animation:wave"],
        is_final=True,
    )
    assert segment.emotion == "happy"
    assert len(segment.actions) == 2
    assert segment.is_final is True


def test_voice_clone_config():
    """测试 VoiceCloneConfig。"""
    config = VoiceCloneConfig(
        voice_id="v123",
        name="Alice",
        description="Test voice",
    )
    assert config.voice_id == "v123"
    assert config.name == "Alice"


def test_voice_clone_config_defaults():
    """测试 VoiceCloneConfig 默认值。"""
    config = VoiceCloneConfig(voice_id="v1", name="Test")
    assert config.description == ""


def test_model_serialization():
    """测试模型序列化为字典。"""
    tag = ActionTag(tag_type="emotion", value="happy", instruction="开心")
    data = tag.model_dump()
    assert data["tag_type"] == "emotion"
    assert data["value"] == "happy"
    assert data["instruction"] == "开心"


def test_voice_clone_config_serialization():
    """测试 VoiceCloneConfig 序列化。"""
    config = VoiceCloneConfig(
        voice_id="v1", name="Alice", description="desc"
    )
    data = config.model_dump()
    assert data["voice_id"] == "v1"
    assert data["name"] == "Alice"
