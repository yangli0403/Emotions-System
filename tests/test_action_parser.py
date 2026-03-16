"""ActionParser 单元测试。"""

import pytest
from services.action_parser import ActionParser


async def _tokens_from_text(text: str):
    """辅助函数：将文本逐字符模拟为 token 流。"""
    for char in text:
        yield char


@pytest.mark.asyncio
async def test_simple_emotion_tag():
    """测试简单情感标签解析。"""
    parser = ActionParser()
    text = "[emotion:happy]你好呀！"
    results = []
    async for sentence in parser.parse_stream(_tokens_from_text(text)):
        results.append(sentence)

    assert len(results) == 1
    assert "你好呀" in results[0].text
    assert any(t.tag_type == "emotion" and t.value == "happy" for t in results[0].tags)


@pytest.mark.asyncio
async def test_compound_emotion_tag():
    """测试复合情感标签 [emotion:happy|instruction:...] 解析。"""
    parser = ActionParser()
    text = "[emotion:happy|instruction:语气活泼俏皮]今天天气真好！"
    results = []
    async for sentence in parser.parse_stream(_tokens_from_text(text)):
        results.append(sentence)

    assert len(results) == 1
    emotion_tags = [t for t in results[0].tags if t.tag_type == "emotion"]
    assert len(emotion_tags) == 1
    assert emotion_tags[0].value == "happy"
    assert emotion_tags[0].instruction == "语气活泼俏皮"


@pytest.mark.asyncio
async def test_sound_tag():
    """测试音效标签解析。

    音效标签应放在句子结束标点之前，模拟 LLM 的实际输出格式。
    """
    parser = ActionParser()
    text = "[sound:laugh]哈哈哈！"
    results = []
    async for sentence in parser.parse_stream(_tokens_from_text(text)):
        results.append(sentence)

    assert len(results) >= 1
    all_tags = []
    for r in results:
        all_tags.extend(r.tags)
    assert any(t.tag_type == "sound" and t.value == "laugh" for t in all_tags)


@pytest.mark.asyncio
async def test_multiple_sentences():
    """测试多句话的切分。"""
    parser = ActionParser()
    text = "[emotion:happy]你好！[emotion:sad]再见。"
    results = []
    async for sentence in parser.parse_stream(_tokens_from_text(text)):
        results.append(sentence)

    assert len(results) == 2
    assert "你好" in results[0].text
    assert "再见" in results[1].text


@pytest.mark.asyncio
async def test_action_and_expression_tags():
    """测试动作和表情标签解析。"""
    parser = ActionParser()
    text = "[expression:smile][animation:wave]你好呀！"
    results = []
    async for sentence in parser.parse_stream(_tokens_from_text(text)):
        results.append(sentence)

    assert len(results) == 1
    tag_types = {t.tag_type for t in results[0].tags}
    assert "expression" in tag_types
    assert "animation" in tag_types


@pytest.mark.asyncio
async def test_tag_type_normalization():
    """测试标签类型归一化（如 expr → expression）。"""
    parser = ActionParser()
    text = "[expr:smile]你好！"
    results = []
    async for sentence in parser.parse_stream(_tokens_from_text(text)):
        results.append(sentence)

    assert len(results) == 1
    assert any(t.tag_type == "expression" for t in results[0].tags)


@pytest.mark.asyncio
async def test_no_tags():
    """测试纯文本（无标签）的解析。"""
    parser = ActionParser()
    text = "这是一段普通的文本。"
    results = []
    async for sentence in parser.parse_stream(_tokens_from_text(text)):
        results.append(sentence)

    assert len(results) == 1
    assert results[0].tags == []
    assert "普通的文本" in results[0].text


@pytest.mark.asyncio
async def test_empty_input():
    """测试空输入。"""
    parser = ActionParser()
    text = ""
    results = []
    async for sentence in parser.parse_stream(_tokens_from_text(text)):
        results.append(sentence)

    assert len(results) == 0


@pytest.mark.asyncio
async def test_unknown_tag_ignored():
    """测试未知标签类型被忽略。"""
    parser = ActionParser()
    text = "[unknown:value]你好！"
    results = []
    async for sentence in parser.parse_stream(_tokens_from_text(text)):
        results.append(sentence)

    assert len(results) == 1
    assert all(t.tag_type != "unknown" for t in results[0].tags)
