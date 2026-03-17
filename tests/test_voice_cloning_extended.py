"""VoiceCloningService 扩展测试。

覆盖 _save_configs、_validate_audio_file（文件过大）、
clone_voice（使用 mock dashscope）等路径。
"""

import json
import os
import tempfile
import pytest
from unittest.mock import MagicMock, patch

from services.voice_cloning_service import DashScopeVoiceCloningService
from core.models import VoiceCloneConfig


@pytest.fixture
def temp_config_dir():
    """创建临时配置目录。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield os.path.join(tmpdir, "voice_configs.json")


def test_save_configs(temp_config_dir):
    """测试保存音色配置到文件。"""
    service = DashScopeVoiceCloningService(
        api_key="test", config_path=temp_config_dir
    )
    service._voices = [
        VoiceCloneConfig(voice_id="v1", name="Alice", description="Test"),
    ]
    service._save_configs()

    assert os.path.exists(temp_config_dir)
    with open(temp_config_dir, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data) == 1
    assert data[0]["voice_id"] == "v1"
    assert data[0]["name"] == "Alice"


def test_load_configs_invalid_json(temp_config_dir):
    """测试加载损坏的 JSON 配置文件。"""
    os.makedirs(os.path.dirname(temp_config_dir), exist_ok=True)
    with open(temp_config_dir, "w") as f:
        f.write("not valid json {{{")

    service = DashScopeVoiceCloningService(
        api_key="test", config_path=temp_config_dir
    )
    assert service._voices == []


def test_validate_audio_file_too_large(temp_config_dir):
    """测试验证过大的音频文件。"""
    service = DashScopeVoiceCloningService(
        api_key="test", config_path=temp_config_dir
    )

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        # 写入超过 10MB 的数据
        f.write(b"x" * (11 * 1024 * 1024))
        tmp_path = f.name

    try:
        with pytest.raises(ValueError, match="过大"):
            service._validate_audio_file(tmp_path)
    finally:
        os.unlink(tmp_path)


def test_validate_audio_file_valid(temp_config_dir):
    """测试验证合法的音频文件（不应抛出异常）。"""
    service = DashScopeVoiceCloningService(
        api_key="test", config_path=temp_config_dir
    )

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(b"RIFF" + b"\x00" * 1000)  # 模拟小型 WAV 文件
        tmp_path = f.name

    try:
        service._validate_audio_file(tmp_path)  # 不应抛出异常
    finally:
        os.unlink(tmp_path)


def test_validate_audio_supported_formats(temp_config_dir):
    """测试所有支持的音频格式。"""
    service = DashScopeVoiceCloningService(
        api_key="test", config_path=temp_config_dir
    )

    for ext in [".wav", ".mp3", ".flac", ".pcm"]:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
            f.write(b"audio_data")
            tmp_path = f.name
        try:
            service._validate_audio_file(tmp_path)  # 不应抛出异常
        finally:
            os.unlink(tmp_path)


@pytest.mark.asyncio
async def test_clone_voice_with_mock_dashscope(temp_config_dir):
    """测试使用 mock dashscope 的声音复刻。"""
    service = DashScopeVoiceCloningService(
        api_key="test_key", config_path=temp_config_dir
    )

    # 创建临时音频文件
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(b"RIFF" + b"\x00" * 1000)
        audio_path = f.name

    mock_voice_clone_manager = MagicMock()
    mock_voice_clone_manager.upload = MagicMock(return_value="cloned_voice_id_123")

    mock_dashscope = MagicMock()
    mock_tts_v2 = MagicMock()
    mock_tts_v2.VoiceCloneManager = mock_voice_clone_manager

    try:
        with patch.dict("sys.modules", {
            "dashscope": mock_dashscope,
            "dashscope.audio": MagicMock(),
            "dashscope.audio.tts_v2": mock_tts_v2,
        }):
            config = await service.clone_voice(audio_path, "TestVoice")

        assert config.voice_id == "cloned_voice_id_123"
        assert config.name == "TestVoice"
        assert len(service._voices) == 1

        # 验证配置已持久化
        assert os.path.exists(temp_config_dir)
    finally:
        # 文件可能已被 clone_voice 清理
        if os.path.exists(audio_path):
            os.unlink(audio_path)


@pytest.mark.asyncio
async def test_clone_voice_dashscope_not_installed(temp_config_dir):
    """测试 dashscope 未安装时抛出 RuntimeError。"""
    service = DashScopeVoiceCloningService(
        api_key="test_key", config_path=temp_config_dir
    )

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(b"RIFF" + b"\x00" * 1000)
        audio_path = f.name

    try:
        with patch("builtins.__import__", side_effect=ImportError("No module")):
            with pytest.raises(RuntimeError, match="dashscope"):
                await service.clone_voice(audio_path, "TestVoice")
    finally:
        if os.path.exists(audio_path):
            os.unlink(audio_path)


@pytest.mark.asyncio
async def test_clone_voice_api_returns_empty_id(temp_config_dir):
    """测试 API 返回空 voice_id 时抛出 RuntimeError。"""
    service = DashScopeVoiceCloningService(
        api_key="test_key", config_path=temp_config_dir
    )

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(b"RIFF" + b"\x00" * 1000)
        audio_path = f.name

    mock_voice_clone_manager = MagicMock()
    mock_voice_clone_manager.upload = MagicMock(return_value="")

    mock_dashscope = MagicMock()
    mock_tts_v2 = MagicMock()
    mock_tts_v2.VoiceCloneManager = mock_voice_clone_manager

    try:
        with patch.dict("sys.modules", {
            "dashscope": mock_dashscope,
            "dashscope.audio": MagicMock(),
            "dashscope.audio.tts_v2": mock_tts_v2,
        }):
            with pytest.raises(RuntimeError, match="未返回有效"):
                await service.clone_voice(audio_path, "TestVoice")
    finally:
        if os.path.exists(audio_path):
            os.unlink(audio_path)


@pytest.mark.asyncio
async def test_clone_voice_invalid_file(temp_config_dir):
    """测试使用无效文件路径进行声音复刻。"""
    service = DashScopeVoiceCloningService(
        api_key="test_key", config_path=temp_config_dir
    )

    with pytest.raises(ValueError, match="不存在"):
        await service.clone_voice("/nonexistent/audio.wav", "TestVoice")


@pytest.mark.asyncio
async def test_delete_voice_and_persist(temp_config_dir):
    """测试删除音色后配置被持久化。"""
    configs = [
        {"voice_id": "v1", "name": "Alice", "description": ""},
        {"voice_id": "v2", "name": "Bob", "description": ""},
    ]
    os.makedirs(os.path.dirname(temp_config_dir), exist_ok=True)
    with open(temp_config_dir, "w") as f:
        json.dump(configs, f)

    service = DashScopeVoiceCloningService(
        api_key="test", config_path=temp_config_dir
    )

    await service.delete_voice("v1")

    # 验证文件已更新
    with open(temp_config_dir, "r") as f:
        data = json.load(f)
    assert len(data) == 1
    assert data[0]["voice_id"] == "v2"


@pytest.mark.asyncio
async def test_get_voice_not_found(temp_config_dir):
    """测试获取不存在的音色返回 None。"""
    service = DashScopeVoiceCloningService(
        api_key="test", config_path=temp_config_dir
    )
    result = await service.get_voice("nonexistent")
    assert result is None
