"""ProtocolAdapter 单元测试。"""

import base64
import pytest
from core.models import MultimodalSegment
from adapters.protocol_adapter import OpenLLMVTuberAdapter


def test_basic_adaptation():
    """测试基本的多模态片段适配。"""
    adapter = OpenLLMVTuberAdapter()
    segment = MultimodalSegment(
        audio_content=b"\x00\x01\x02\x03",
        text="你好！",
        emotion="happy",
        actions=["expression:smile"],
        is_final=False,
    )
    result = adapter.adapt(segment)

    assert result["type"] == "audio"
    assert result["text"] == "你好！"
    assert result["emotion"] == "happy"
    assert result["is_final"] is False
    assert "audio" in result
    assert result["audio_format"] == "wav"


def test_audio_base64_encoding():
    """测试音频数据被正确 Base64 编码。"""
    adapter = OpenLLMVTuberAdapter()
    audio_bytes = b"test_audio_data"
    segment = MultimodalSegment(
        audio_content=audio_bytes,
        text="测试",
        emotion="neutral",
    )
    result = adapter.adapt(segment)

    decoded = base64.b64decode(result["audio"])
    assert decoded == audio_bytes


def test_empty_audio():
    """测试空音频时不包含 audio 字段。"""
    adapter = OpenLLMVTuberAdapter()
    segment = MultimodalSegment(
        audio_content=b"",
        text="无音频",
        emotion="neutral",
    )
    result = adapter.adapt(segment)

    assert "audio" not in result
    assert "audio_format" not in result


def test_actions_categorized():
    """测试动作被正确分类。"""
    adapter = OpenLLMVTuberAdapter()
    segment = MultimodalSegment(
        audio_content=b"data",
        text="你好",
        emotion="happy",
        actions=["expression:smile", "animation:wave", "gesture:thumbs_up"],
    )
    result = adapter.adapt(segment)

    assert result["expression"] == "smile"
    assert result["animation"] == "wave"
    assert result["gesture"] == "thumbs_up"
    assert result["actions"] == ["expression:smile", "animation:wave", "gesture:thumbs_up"]


def test_is_final_flag():
    """测试 is_final 标志正确传递。"""
    adapter = OpenLLMVTuberAdapter()
    segment = MultimodalSegment(
        audio_content=b"data",
        text="最后一句",
        emotion="neutral",
        is_final=True,
    )
    result = adapter.adapt(segment)

    assert result["is_final"] is True


def test_no_actions():
    """测试无动作时 actions 字段不存在。"""
    adapter = OpenLLMVTuberAdapter()
    segment = MultimodalSegment(
        audio_content=b"data",
        text="无动作",
        emotion="neutral",
        actions=[],
    )
    result = adapter.adapt(segment)

    assert "actions" not in result
