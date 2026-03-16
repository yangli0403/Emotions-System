"""Config 模块单元测试。"""

import os
import pytest
from config import AppConfig, LLMConfig, TTSConfig, VoiceCloneConfig, ServerConfig


def test_llm_config_defaults():
    """测试 LLM 配置默认值。"""
    config = LLMConfig()
    assert config.model == "gpt-4"
    assert config.temperature == 0.7
    assert config.max_tokens == 1024


def test_tts_config_defaults():
    """测试 TTS 配置默认值。"""
    config = TTSConfig()
    assert config.model == "cosyvoice-v2"
    assert config.default_voice == "longxiaochun"


def test_server_config_defaults():
    """测试服务器配置默认值。"""
    config = ServerConfig()
    assert config.host == "0.0.0.0"
    assert config.port == 8000
    assert config.ws_path == "/ws"


def test_app_config_from_env(monkeypatch):
    """测试从环境变量加载配置。"""
    monkeypatch.setenv("LLM_MODEL", "gpt-3.5-turbo")
    monkeypatch.setenv("LLM_TEMPERATURE", "0.5")
    monkeypatch.setenv("TTS_MODEL", "cosyvoice-v3")
    monkeypatch.setenv("SERVER_PORT", "9000")

    config = AppConfig.from_env()
    assert config.llm.model == "gpt-3.5-turbo"
    assert config.llm.temperature == 0.5
    assert config.tts.model == "cosyvoice-v3"
    assert config.server.port == 9000


def test_voice_clone_config_defaults():
    """测试声音复刻配置默认值。"""
    config = VoiceCloneConfig()
    assert config.config_path == "data/voice_configs.json"
