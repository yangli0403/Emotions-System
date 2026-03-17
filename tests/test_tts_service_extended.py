"""CosyVoiceTTSService 扩展测试。

覆盖 synthesize_stream（含 dashscope mock）、synthesize_full、
synthesize_to_file 以及错误处理路径。
"""

import os
import tempfile
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from services.tts_service import CosyVoiceTTSService, DEFAULT_EMOTION_INSTRUCTIONS


# ========== synthesize_stream 测试（使用 mock dashscope） ==========

@pytest.mark.asyncio
async def test_synthesize_stream_with_mock_dashscope():
    """测试使用 mock dashscope 的流式合成。"""
    mock_synthesizer = MagicMock()
    mock_synthesizer.streaming_call = MagicMock()
    mock_synthesizer.streaming_complete = MagicMock(return_value=b"fake_audio_data")

    mock_audio_format = MagicMock()
    mock_audio_format.WAV_22050HZ_MONO_16BIT = "wav_22050"

    mock_speech_synthesizer_cls = MagicMock(return_value=mock_synthesizer)

    mock_dashscope = MagicMock()
    mock_tts_v2 = MagicMock()
    mock_tts_v2.SpeechSynthesizer = mock_speech_synthesizer_cls
    mock_tts_v2.AudioFormat = mock_audio_format

    with patch.dict("sys.modules", {
        "dashscope": mock_dashscope,
        "dashscope.audio": MagicMock(),
        "dashscope.audio.tts_v2": mock_tts_v2,
    }):
        service = CosyVoiceTTSService(api_key="test_key", model="cosyvoice-v2")
        chunks = []
        async for chunk in service.synthesize_stream(
            "你好世界", "用开心的语气说话", "voice_123"
        ):
            chunks.append(chunk)

    assert len(chunks) == 1
    assert chunks[0] == b"fake_audio_data"
    # 验证 streaming_call 被调用
    assert mock_synthesizer.streaming_call.called
    assert mock_synthesizer.streaming_complete.called


@pytest.mark.asyncio
async def test_synthesize_stream_empty_audio_result():
    """测试 dashscope 返回空音频时不产生输出。"""
    mock_synthesizer = MagicMock()
    mock_synthesizer.streaming_call = MagicMock()
    mock_synthesizer.streaming_complete = MagicMock(return_value=None)

    mock_audio_format = MagicMock()
    mock_audio_format.WAV_22050HZ_MONO_16BIT = "wav_22050"

    mock_speech_synthesizer_cls = MagicMock(return_value=mock_synthesizer)

    mock_dashscope = MagicMock()
    mock_tts_v2 = MagicMock()
    mock_tts_v2.SpeechSynthesizer = mock_speech_synthesizer_cls
    mock_tts_v2.AudioFormat = mock_audio_format

    with patch.dict("sys.modules", {
        "dashscope": mock_dashscope,
        "dashscope.audio": MagicMock(),
        "dashscope.audio.tts_v2": mock_tts_v2,
    }):
        service = CosyVoiceTTSService(api_key="test_key")
        chunks = []
        async for chunk in service.synthesize_stream("你好", "", ""):
            chunks.append(chunk)

    assert len(chunks) == 0


@pytest.mark.asyncio
async def test_synthesize_stream_dashscope_not_installed():
    """测试 dashscope 未安装时抛出 RuntimeError。"""
    service = CosyVoiceTTSService(api_key="test_key")

    with patch.dict("sys.modules", {"dashscope": None}):
        with patch("builtins.__import__", side_effect=ImportError("No module named 'dashscope'")):
            with pytest.raises(RuntimeError, match="dashscope"):
                async for _ in service.synthesize_stream("你好", "", ""):
                    pass


@pytest.mark.asyncio
async def test_synthesize_stream_api_exception():
    """测试 dashscope API 调用异常时抛出 RuntimeError。"""
    mock_audio_format = MagicMock()
    mock_audio_format.WAV_22050HZ_MONO_16BIT = "wav_22050"

    mock_speech_synthesizer_cls = MagicMock(
        side_effect=Exception("API 连接超时")
    )

    mock_dashscope = MagicMock()
    mock_tts_v2 = MagicMock()
    mock_tts_v2.SpeechSynthesizer = mock_speech_synthesizer_cls
    mock_tts_v2.AudioFormat = mock_audio_format

    with patch.dict("sys.modules", {
        "dashscope": mock_dashscope,
        "dashscope.audio": MagicMock(),
        "dashscope.audio.tts_v2": mock_tts_v2,
    }):
        service = CosyVoiceTTSService(api_key="test_key")
        with pytest.raises(RuntimeError, match="CosyVoice 合成失败"):
            async for _ in service.synthesize_stream("你好", "", ""):
                pass


@pytest.mark.asyncio
async def test_synthesize_stream_uses_default_voice():
    """测试未指定 voice_id 时使用默认音色。"""
    mock_synthesizer = MagicMock()
    mock_synthesizer.streaming_call = MagicMock()
    mock_synthesizer.streaming_complete = MagicMock(return_value=b"audio")

    mock_audio_format = MagicMock()
    mock_audio_format.WAV_22050HZ_MONO_16BIT = "wav_22050"

    mock_speech_synthesizer_cls = MagicMock(return_value=mock_synthesizer)

    mock_dashscope = MagicMock()
    mock_tts_v2 = MagicMock()
    mock_tts_v2.SpeechSynthesizer = mock_speech_synthesizer_cls
    mock_tts_v2.AudioFormat = mock_audio_format

    with patch.dict("sys.modules", {
        "dashscope": mock_dashscope,
        "dashscope.audio": MagicMock(),
        "dashscope.audio.tts_v2": mock_tts_v2,
    }):
        service = CosyVoiceTTSService(
            api_key="test_key", default_voice="my_voice"
        )
        async for _ in service.synthesize_stream("你好", "", ""):
            pass

    # 验证使用了 default_voice
    call_kwargs = mock_speech_synthesizer_cls.call_args.kwargs
    assert call_kwargs["voice"] == "my_voice"


# ========== synthesize_full 测试 ==========

@pytest.mark.asyncio
async def test_synthesize_full():
    """测试非流式完整合成。"""
    service = CosyVoiceTTSService(api_key="test")

    async def mock_stream(text, emotion_instruction, voice_id):
        yield b"chunk1"
        yield b"chunk2"

    with patch.object(service, "synthesize_stream", side_effect=mock_stream):
        result = await service.synthesize_full("你好", "开心", "v1")

    assert result == b"chunk1chunk2"


@pytest.mark.asyncio
async def test_synthesize_full_empty():
    """测试空文本的完整合成返回空字节。"""
    service = CosyVoiceTTSService(api_key="test")

    async def mock_stream(text, emotion_instruction, voice_id):
        return
        yield  # make it a generator

    with patch.object(service, "synthesize_stream", side_effect=mock_stream):
        result = await service.synthesize_full("", "", "")

    assert result == b""


# ========== synthesize_to_file 测试 ==========

@pytest.mark.asyncio
async def test_synthesize_to_file_success():
    """测试合成并保存文件。"""
    service = CosyVoiceTTSService(api_key="test")

    with patch.object(
        service, "synthesize_full",
        new_callable=AsyncMock,
        return_value=b"wav_audio_data",
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output", "test.wav")
            result = await service.synthesize_to_file(
                "你好", output_path, "开心", "v1"
            )

            assert os.path.exists(result)
            with open(result, "rb") as f:
                assert f.read() == b"wav_audio_data"


@pytest.mark.asyncio
async def test_synthesize_to_file_empty_audio():
    """测试合成结果为空时抛出 RuntimeError。"""
    service = CosyVoiceTTSService(api_key="test")

    with patch.object(
        service, "synthesize_full",
        new_callable=AsyncMock,
        return_value=b"",
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test.wav")
            with pytest.raises(RuntimeError, match="合成结果为空"):
                await service.synthesize_to_file("你好", output_path)


@pytest.mark.asyncio
async def test_synthesize_to_file_creates_directory():
    """测试合成文件时自动创建目录。"""
    service = CosyVoiceTTSService(api_key="test")

    with patch.object(
        service, "synthesize_full",
        new_callable=AsyncMock,
        return_value=b"audio",
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "deep", "nested", "dir", "test.wav")
            result = await service.synthesize_to_file("你好", output_path)
            assert os.path.exists(result)


# ========== _get_instruction 边界测试 ==========

def test_get_instruction_whitespace_only():
    """测试纯空白指令时使用默认映射。"""
    service = CosyVoiceTTSService()
    instruction = service._get_instruction("   ", "sad")
    assert instruction == DEFAULT_EMOTION_INSTRUCTIONS["sad"]


def test_get_instruction_with_leading_trailing_spaces():
    """测试带前后空格的指令被正确 strip。"""
    service = CosyVoiceTTSService()
    instruction = service._get_instruction("  语气活泼  ", "happy")
    assert instruction == "语气活泼"
