"""OpenAILLMService 单元测试。

使用 mock 模拟 AsyncOpenAI 客户端，避免真实 API 调用。
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.llm_service import OpenAILLMService


def test_init_defaults():
    """测试 LLM 服务默认初始化。"""
    with patch("services.llm_service.AsyncOpenAI"):
        service = OpenAILLMService()
    assert service.model == "gpt-4"
    assert service.temperature == 0.7
    assert service.max_tokens == 1024
    assert "复合标签格式" in service.system_prompt


def test_init_custom_params():
    """测试自定义参数初始化。"""
    with patch("services.llm_service.AsyncOpenAI"):
        service = OpenAILLMService(
            api_key="test_key",
            base_url="http://localhost:11434/v1",
            model="gpt-4o",
            temperature=0.5,
            max_tokens=2048,
            system_prompt="自定义提示词",
        )
    assert service.model == "gpt-4o"
    assert service.temperature == 0.5
    assert service.max_tokens == 2048
    assert service.system_prompt == "自定义提示词"


def test_init_custom_system_prompt():
    """测试自定义系统提示词。"""
    with patch("services.llm_service.AsyncOpenAI"):
        service = OpenAILLMService(system_prompt="你是一个助手")
    assert service.system_prompt == "你是一个助手"


def test_default_system_prompt_content():
    """测试默认系统提示词包含关键内容。"""
    prompt = OpenAILLMService._default_system_prompt()
    # 应包含复合标签格式说明
    assert "[emotion:" in prompt
    assert "instruction:" in prompt
    # 应包含所有7种基础情感
    for emotion in ["neutral", "happy", "sad", "angry", "surprised", "fearful", "disgusted"]:
        assert emotion in prompt
    # 应包含音效标签说明
    assert "[sound:laugh]" in prompt
    # 应包含示例
    assert "示例" in prompt


@pytest.mark.asyncio
async def test_generate_response_stream_success():
    """测试流式生成成功场景。"""
    # 模拟 OpenAI 流式响应
    mock_chunk_1 = MagicMock()
    mock_chunk_1.choices = [MagicMock()]
    mock_chunk_1.choices[0].delta.content = "你好"

    mock_chunk_2 = MagicMock()
    mock_chunk_2.choices = [MagicMock()]
    mock_chunk_2.choices[0].delta.content = "世界"

    mock_chunk_3 = MagicMock()
    mock_chunk_3.choices = []  # 空 choices，应被跳过

    async def mock_stream():
        for chunk in [mock_chunk_1, mock_chunk_2, mock_chunk_3]:
            yield chunk

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_stream())

    with patch("services.llm_service.AsyncOpenAI", return_value=mock_client):
        service = OpenAILLMService(api_key="test")

    service.client = mock_client

    tokens = []
    async for token in service.generate_response_stream("你好", []):
        tokens.append(token)

    assert tokens == ["你好", "世界"]


@pytest.mark.asyncio
async def test_generate_response_stream_with_history():
    """测试带对话历史的流式生成。"""
    mock_chunk = MagicMock()
    mock_chunk.choices = [MagicMock()]
    mock_chunk.choices[0].delta.content = "回复"

    async def mock_stream():
        yield mock_chunk

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_stream())

    with patch("services.llm_service.AsyncOpenAI", return_value=mock_client):
        service = OpenAILLMService(api_key="test")

    service.client = mock_client

    history = [
        {"role": "user", "content": "之前的消息"},
        {"role": "assistant", "content": "之前的回复"},
    ]

    tokens = []
    async for token in service.generate_response_stream("新消息", history):
        tokens.append(token)

    assert tokens == ["回复"]

    # 验证 messages 构建正确
    call_args = mock_client.chat.completions.create.call_args
    messages = call_args.kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert messages[1] == history[0]
    assert messages[2] == history[1]
    assert messages[3]["role"] == "user"
    assert messages[3]["content"] == "新消息"


@pytest.mark.asyncio
async def test_generate_response_stream_api_error():
    """测试 API 调用失败时抛出 RuntimeError。"""
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=Exception("API 连接失败")
    )

    with patch("services.llm_service.AsyncOpenAI", return_value=mock_client):
        service = OpenAILLMService(api_key="test")

    service.client = mock_client

    with pytest.raises(RuntimeError, match="LLM 流式生成失败"):
        async for _ in service.generate_response_stream("测试", []):
            pass


@pytest.mark.asyncio
async def test_generate_response_stream_empty_delta():
    """测试 delta.content 为 None 的 chunk 被跳过。"""
    mock_chunk = MagicMock()
    mock_chunk.choices = [MagicMock()]
    mock_chunk.choices[0].delta.content = None

    async def mock_stream():
        yield mock_chunk

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_stream())

    with patch("services.llm_service.AsyncOpenAI", return_value=mock_client):
        service = OpenAILLMService(api_key="test")

    service.client = mock_client

    tokens = []
    async for token in service.generate_response_stream("测试", []):
        tokens.append(token)

    assert tokens == []
