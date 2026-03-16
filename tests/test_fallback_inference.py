"""FallbackInferenceService 单元测试。"""

import pytest
from services.fallback_inference_service import (
    RuleBasedFallbackService,
    BERTFallbackService,
    SegmentAwareFallbackService,
)


@pytest.mark.asyncio
async def test_happy_keywords():
    """测试开心关键词推断。"""
    service = RuleBasedFallbackService()
    result = await service.infer_emotion("太棒了，我真的好开心！")
    assert result.tag_type == "emotion"
    assert result.value == "happy"
    assert result.instruction != ""


@pytest.mark.asyncio
async def test_sad_keywords():
    """测试悲伤关键词推断。"""
    service = RuleBasedFallbackService()
    result = await service.infer_emotion("真的好难过，太伤心了。")
    assert result.value == "sad"


@pytest.mark.asyncio
async def test_angry_keywords():
    """测试愤怒关键词推断。"""
    service = RuleBasedFallbackService()
    result = await service.infer_emotion("太过分了，真是岂有此理！")
    assert result.value == "angry"


@pytest.mark.asyncio
async def test_surprised_keywords():
    """测试惊讶关键词推断。"""
    service = RuleBasedFallbackService()
    result = await service.infer_emotion("哇，真的吗？没想到！")
    assert result.value == "surprised"


@pytest.mark.asyncio
async def test_fearful_keywords():
    """测试恐惧关键词推断。"""
    service = RuleBasedFallbackService()
    result = await service.infer_emotion("好害怕，太恐怖了。")
    assert result.value == "fearful"


@pytest.mark.asyncio
async def test_disgusted_keywords():
    """测试厌恶关键词推断。"""
    service = RuleBasedFallbackService()
    result = await service.infer_emotion("太恶心了，受不了。")
    assert result.value == "disgusted"


@pytest.mark.asyncio
async def test_neutral_no_match():
    """测试无匹配关键词时返回 neutral。"""
    service = RuleBasedFallbackService()
    result = await service.infer_emotion("今天是星期一。")
    assert result.value == "neutral"


@pytest.mark.asyncio
async def test_empty_text():
    """测试空文本返回 neutral。"""
    service = RuleBasedFallbackService()
    result = await service.infer_emotion("")
    assert result.value == "neutral"


@pytest.mark.asyncio
async def test_whitespace_text():
    """测试纯空白文本返回 neutral。"""
    service = RuleBasedFallbackService()
    result = await service.infer_emotion("   ")
    assert result.value == "neutral"


@pytest.mark.asyncio
async def test_bert_not_implemented():
    """测试 BERT 服务抛出 NotImplementedError。"""
    service = BERTFallbackService()
    with pytest.raises(NotImplementedError):
        await service.infer_emotion("测试文本")


@pytest.mark.asyncio
async def test_segment_aware_not_implemented():
    """测试 SegmentAware 服务抛出 NotImplementedError。"""
    service = SegmentAwareFallbackService()
    with pytest.raises(NotImplementedError):
        await service.infer_emotion("测试文本")
