"""VoiceCloningService 单元测试。"""

import json
import os
import tempfile
import pytest
from services.voice_cloning_service import DashScopeVoiceCloningService
from core.models import VoiceCloneConfig


@pytest.fixture
def temp_config_dir():
    """创建临时配置目录。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield os.path.join(tmpdir, "voice_configs.json")


def test_init_empty(temp_config_dir):
    """测试空配置初始化。"""
    service = DashScopeVoiceCloningService(
        api_key="test", config_path=temp_config_dir
    )
    assert service._voices == []


def test_load_existing_configs(temp_config_dir):
    """测试从已有配置文件加载。"""
    configs = [
        {"voice_id": "v1", "name": "Alice", "description": "Test voice 1"},
        {"voice_id": "v2", "name": "Bob", "description": "Test voice 2"},
    ]
    os.makedirs(os.path.dirname(temp_config_dir), exist_ok=True)
    with open(temp_config_dir, "w") as f:
        json.dump(configs, f)

    service = DashScopeVoiceCloningService(
        api_key="test", config_path=temp_config_dir
    )
    assert len(service._voices) == 2
    assert service._voices[0].voice_id == "v1"
    assert service._voices[1].name == "Bob"


@pytest.mark.asyncio
async def test_list_voices(temp_config_dir):
    """测试列出音色。"""
    configs = [
        {"voice_id": "v1", "name": "Alice", "description": ""},
    ]
    os.makedirs(os.path.dirname(temp_config_dir), exist_ok=True)
    with open(temp_config_dir, "w") as f:
        json.dump(configs, f)

    service = DashScopeVoiceCloningService(
        api_key="test", config_path=temp_config_dir
    )
    voices = await service.list_voices()
    assert len(voices) == 1
    assert voices[0].voice_id == "v1"


@pytest.mark.asyncio
async def test_get_voice(temp_config_dir):
    """测试根据 ID 获取音色。"""
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
    voice = await service.get_voice("v2")
    assert voice is not None
    assert voice.name == "Bob"

    missing = await service.get_voice("v999")
    assert missing is None


@pytest.mark.asyncio
async def test_delete_voice(temp_config_dir):
    """测试删除音色。"""
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

    result = await service.delete_voice("v1")
    assert result is True
    assert len(service._voices) == 1

    result = await service.delete_voice("v999")
    assert result is False


def test_validate_audio_nonexistent(temp_config_dir):
    """测试验证不存在的音频文件。"""
    service = DashScopeVoiceCloningService(
        api_key="test", config_path=temp_config_dir
    )
    with pytest.raises(ValueError, match="不存在"):
        service._validate_audio_file("/nonexistent/file.wav")


def test_validate_audio_wrong_format(temp_config_dir):
    """测试验证不支持的音频格式。"""
    service = DashScopeVoiceCloningService(
        api_key="test", config_path=temp_config_dir
    )
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        f.write(b"not audio")
        tmp_path = f.name

    try:
        with pytest.raises(ValueError, match="不支持"):
            service._validate_audio_file(tmp_path)
    finally:
        os.unlink(tmp_path)
