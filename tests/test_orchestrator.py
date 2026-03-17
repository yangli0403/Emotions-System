"""Orchestrator 单元测试。

使用 mock 模拟各依赖服务，测试编排器的协调逻辑。
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from core.models import ActionTag, ParsedSentence, MultimodalSegment
from services.orchestrator import Orchestrator
from services.action_parser import ActionParser
from services.command_packager import CommandPackager


def _make_mock_orchestrator(
    llm_tokens=None,
    parsed_sentences=None,
    segments=None,
    adapted_messages=None,
):
    """创建一个带有 mock 依赖的 Orchestrator。"""
    # Mock LLM Service
    mock_llm = AsyncMock()
    if llm_tokens is not None:
        async def mock_llm_stream(prompt, history):
            for token in llm_tokens:
                yield token
        mock_llm.generate_response_stream = mock_llm_stream

    # Mock ActionParser
    mock_parser = MagicMock(spec=ActionParser)
    if parsed_sentences is not None:
        async def mock_parse_stream(token_stream):
            for s in parsed_sentences:
                yield s
        mock_parser.parse_stream = mock_parse_stream

    # Mock CommandPackager
    mock_packager = MagicMock(spec=CommandPackager)
    if segments is not None:
        async def mock_package_stream(sentence_stream):
            for seg in segments:
                yield seg
        mock_packager.package_stream = mock_package_stream

    # Mock ProtocolAdapter
    mock_adapter = MagicMock()
    if adapted_messages is not None:
        mock_adapter.adapt = MagicMock(side_effect=adapted_messages)
    else:
        mock_adapter.adapt = MagicMock(
            return_value={"type": "audio", "text": "test"}
        )

    return Orchestrator(
        llm_service=mock_llm,
        action_parser=mock_parser,
        command_packager=mock_packager,
        protocol_adapter=mock_adapter,
    )


def test_init():
    """测试编排器初始化。"""
    orch = _make_mock_orchestrator()
    assert orch._histories == {}


def test_get_history_new_session():
    """测试获取新会话的历史（应返回空列表）。"""
    orch = _make_mock_orchestrator()
    history = orch.get_history("session_1")
    assert history == []
    assert "session_1" in orch._histories


def test_get_history_existing_session():
    """测试获取已有会话的历史。"""
    orch = _make_mock_orchestrator()
    orch._histories["session_1"] = [
        {"role": "user", "content": "你好"}
    ]
    history = orch.get_history("session_1")
    assert len(history) == 1
    assert history[0]["content"] == "你好"


def test_clear_history():
    """测试清除会话历史。"""
    orch = _make_mock_orchestrator()
    orch._histories["session_1"] = [
        {"role": "user", "content": "你好"}
    ]
    orch.clear_history("session_1")
    assert "session_1" not in orch._histories


def test_clear_history_nonexistent():
    """测试清除不存在的会话历史（不应报错）。"""
    orch = _make_mock_orchestrator()
    orch.clear_history("nonexistent")  # 不应抛出异常


@pytest.mark.asyncio
async def test_handle_text_input_empty():
    """测试空文本输入返回提示信息。"""
    orch = _make_mock_orchestrator()
    results = []
    async for msg in orch.handle_text_input("s1", ""):
        results.append(msg)
    assert len(results) == 1
    assert results[0]["type"] == "info"


@pytest.mark.asyncio
async def test_handle_text_input_whitespace():
    """测试纯空白文本输入返回提示信息。"""
    orch = _make_mock_orchestrator()
    results = []
    async for msg in orch.handle_text_input("s1", "   "):
        results.append(msg)
    assert len(results) == 1
    assert results[0]["type"] == "info"


@pytest.mark.asyncio
async def test_handle_text_input_success():
    """测试正常文本输入的完整流程。"""
    segment = MultimodalSegment(
        audio_content=b"fake_audio",
        text="你好呀！",
        emotion="happy",
    )
    adapted_msg = {
        "type": "audio",
        "text": "你好呀！",
        "emotion": "happy",
    }

    orch = _make_mock_orchestrator(
        llm_tokens=["你好", "呀！"],
        parsed_sentences=[
            ParsedSentence(text="你好呀！", tags=[], is_final=True)
        ],
        segments=[segment],
        adapted_messages=[adapted_msg],
    )

    results = []
    async for msg in orch.handle_text_input("s1", "你好"):
        results.append(msg)

    # 应该有 adapted_msg + end 标记
    assert len(results) == 2
    assert results[0]["type"] == "audio"
    assert results[0]["text"] == "你好呀！"
    assert results[1]["type"] == "end"

    # 验证对话历史已更新
    history = orch.get_history("s1")
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "你好"
    assert history[1]["role"] == "assistant"
    assert history[1]["content"] == "你好呀！"


@pytest.mark.asyncio
async def test_handle_text_input_multiple_segments():
    """测试多个片段的输出。"""
    seg1 = MultimodalSegment(
        audio_content=b"audio1", text="第一句。", emotion="happy"
    )
    seg2 = MultimodalSegment(
        audio_content=b"audio2", text="第二句。", emotion="sad", is_final=True
    )

    msg1 = {"type": "audio", "text": "第一句。"}
    msg2 = {"type": "audio", "text": "第二句。"}

    orch = _make_mock_orchestrator(
        llm_tokens=["第一句。", "第二句。"],
        parsed_sentences=[
            ParsedSentence(text="第一句。", tags=[]),
            ParsedSentence(text="第二句。", tags=[], is_final=True),
        ],
        segments=[seg1, seg2],
        adapted_messages=[msg1, msg2],
    )

    results = []
    async for msg in orch.handle_text_input("s1", "说两句"):
        results.append(msg)

    # 2 个 audio + 1 个 end
    assert len(results) == 3
    assert results[2]["type"] == "end"


@pytest.mark.asyncio
async def test_handle_text_input_llm_error():
    """测试 LLM 调用失败时返回错误消息。"""
    mock_llm = AsyncMock()
    mock_llm.generate_response_stream = MagicMock(
        side_effect=Exception("API 错误")
    )

    orch = Orchestrator(
        llm_service=mock_llm,
        action_parser=MagicMock(),
        command_packager=MagicMock(),
        protocol_adapter=MagicMock(),
    )

    results = []
    async for msg in orch.handle_text_input("s1", "你好"):
        results.append(msg)

    assert len(results) == 1
    assert results[0]["type"] == "error"
    assert "AI 生成失败" in results[0]["message"]


@pytest.mark.asyncio
async def test_handle_text_input_updates_history():
    """测试对话历史在多轮对话中正确更新。"""
    seg = MultimodalSegment(
        audio_content=b"audio", text="回复1", emotion="neutral"
    )

    orch = _make_mock_orchestrator(
        llm_tokens=["回复1"],
        parsed_sentences=[
            ParsedSentence(text="回复1", tags=[], is_final=True)
        ],
        segments=[seg],
    )

    # 第一轮
    async for _ in orch.handle_text_input("s1", "问题1"):
        pass

    history = orch.get_history("s1")
    assert len(history) == 2
    assert history[0]["content"] == "问题1"
    assert history[1]["content"] == "回复1"
