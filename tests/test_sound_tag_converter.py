"""SoundTagConverter 单元测试。"""

import pytest
from core.models import ActionTag, ParsedSentence
from services.sound_tag_converter import SoundTagConverter


def test_laugh_internalized():
    """测试 laugh 音效被内生化为 [laughter]。"""
    converter = SoundTagConverter()
    sentence = ParsedSentence(
        text="哈哈哈！",
        tags=[ActionTag(tag_type="sound", value="laugh")],
    )
    result = converter.convert(sentence)

    assert "[laughter]" in result.text
    assert not any(t.tag_type == "sound" and t.value == "laugh" for t in result.tags)


def test_sigh_internalized():
    """测试 sigh 音效被内生化为 [breath]。"""
    converter = SoundTagConverter()
    sentence = ParsedSentence(
        text="唉。",
        tags=[ActionTag(tag_type="sound", value="sigh")],
    )
    result = converter.convert(sentence)

    assert "[breath]" in result.text
    assert not any(t.tag_type == "sound" for t in result.tags)


def test_breath_internalized():
    """测试 breath 音效被内生化为 [breath]。"""
    converter = SoundTagConverter()
    sentence = ParsedSentence(
        text="深呼吸。",
        tags=[ActionTag(tag_type="sound", value="breath")],
    )
    result = converter.convert(sentence)

    assert "[breath]" in result.text


def test_unsupported_sound_passthrough():
    """测试不支持内生化的音效被保留给前端。"""
    converter = SoundTagConverter()
    sentence = ParsedSentence(
        text="掌声响起。",
        tags=[ActionTag(tag_type="sound", value="applause")],
    )
    result = converter.convert(sentence)

    assert "[laughter]" not in result.text
    assert "[breath]" not in result.text
    assert any(t.tag_type == "sound" and t.value == "applause" for t in result.tags)


def test_non_sound_tags_preserved():
    """测试非音效标签被原样保留。"""
    converter = SoundTagConverter()
    sentence = ParsedSentence(
        text="你好！",
        tags=[
            ActionTag(tag_type="emotion", value="happy", instruction="开心"),
            ActionTag(tag_type="expression", value="smile"),
            ActionTag(tag_type="sound", value="laugh"),
        ],
    )
    result = converter.convert(sentence)

    assert any(t.tag_type == "emotion" for t in result.tags)
    assert any(t.tag_type == "expression" for t in result.tags)
    assert not any(t.tag_type == "sound" and t.value == "laugh" for t in result.tags)
    assert "[laughter]" in result.text


def test_multiple_sounds():
    """测试多个音效标签同时处理。"""
    converter = SoundTagConverter()
    sentence = ParsedSentence(
        text="哈哈。",
        tags=[
            ActionTag(tag_type="sound", value="laugh"),
            ActionTag(tag_type="sound", value="sigh"),
            ActionTag(tag_type="sound", value="applause"),
        ],
    )
    result = converter.convert(sentence)

    assert "[laughter]" in result.text
    assert "[breath]" in result.text
    assert any(t.tag_type == "sound" and t.value == "applause" for t in result.tags)


def test_no_tags():
    """测试无标签的句子不被修改。"""
    converter = SoundTagConverter()
    sentence = ParsedSentence(text="普通文本。", tags=[])
    result = converter.convert(sentence)

    assert result.text == "普通文本。"
    assert result.tags == []
