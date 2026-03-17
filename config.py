"""
Emotions-System — 配置管理

从环境变量或 .env 文件加载系统配置。
支持多种 LLM 后端：openai、ark（字节火山引擎）。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class LLMConfig:
    """LLM 服务配置。"""
    backend: str = "openai"  # "openai" 或 "ark"
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 1024

    @classmethod
    def from_env(cls) -> "LLMConfig":
        return cls(
            backend=os.getenv("LLM_BACKEND", "openai"),
            api_key=os.getenv("LLM_API_KEY", ""),
            base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
            model=os.getenv("LLM_MODEL", "gpt-4"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "1024")),
        )


@dataclass
class TTSConfig:
    """TTS 服务配置。"""
    api_key: str = ""
    model: str = "cosyvoice-v2"
    default_voice: str = "longxiaochun"

    @classmethod
    def from_env(cls) -> "TTSConfig":
        return cls(
            api_key=os.getenv("DASHSCOPE_API_KEY", ""),
            model=os.getenv("TTS_MODEL", "cosyvoice-v2"),
            default_voice=os.getenv("TTS_DEFAULT_VOICE", "longxiaochun"),
        )


@dataclass
class VoiceCloneConfig:
    """声音复刻服务配置。"""
    api_key: str = ""
    config_path: str = "data/voice_configs.json"

    @classmethod
    def from_env(cls) -> "VoiceCloneConfig":
        return cls(
            api_key=os.getenv("DASHSCOPE_API_KEY", ""),
            config_path=os.getenv(
                "VOICE_CONFIG_PATH", "data/voice_configs.json"
            ),
        )


@dataclass
class ServerConfig:
    """服务器配置。"""
    host: str = "0.0.0.0"
    port: int = 8000
    ws_path: str = "/ws"

    @classmethod
    def from_env(cls) -> "ServerConfig":
        return cls(
            host=os.getenv("SERVER_HOST", "0.0.0.0"),
            port=int(os.getenv("SERVER_PORT", "8000")),
            ws_path=os.getenv("SERVER_WS_PATH", "/ws"),
        )


@dataclass
class AppConfig:
    """应用总配置。"""
    llm: LLMConfig = field(default_factory=LLMConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    voice_clone: VoiceCloneConfig = field(default_factory=VoiceCloneConfig)
    server: ServerConfig = field(default_factory=ServerConfig)

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            llm=LLMConfig.from_env(),
            tts=TTSConfig.from_env(),
            voice_clone=VoiceCloneConfig.from_env(),
            server=ServerConfig.from_env(),
        )
