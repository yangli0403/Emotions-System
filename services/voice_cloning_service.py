"""
Emotions-System — 声音复刻服务实现

基于阿里百炼 DashScope API 的声音复刻服务。
支持：
- 零样本音色复刻（上传 3-10 秒参考音频）
- 复刻音色管理（列表、删除）
- 音色配置持久化（本地 JSON 文件）
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import List, Optional

from core.interfaces import IVoiceCloningService
from core.models import VoiceCloneConfig

logger = logging.getLogger(__name__)

# 本地音色配置文件路径
DEFAULT_VOICE_CONFIG_PATH = "data/voice_configs.json"


class DashScopeVoiceCloningService(IVoiceCloningService):
    """基于阿里百炼 DashScope API 的声音复刻服务。

    使用 CosyVoice 的声音复刻能力，上传参考音频创建复刻音色。
    复刻的音色 ID 会持久化到本地配置文件中。
    """

    # 音频格式要求
    SUPPORTED_AUDIO_FORMATS = {".wav", ".mp3", ".flac", ".pcm"}
    MIN_AUDIO_DURATION_SEC = 3
    MAX_AUDIO_DURATION_SEC = 10
    MAX_AUDIO_SIZE_MB = 10

    def __init__(
        self,
        api_key: str = "",
        config_path: str = DEFAULT_VOICE_CONFIG_PATH,
    ) -> None:
        """初始化声音复刻服务。

        Args:
            api_key: DashScope API 密钥。
            config_path: 本地音色配置文件路径。
        """
        self.api_key = api_key
        self.config_path = Path(config_path)
        self._voices: List[VoiceCloneConfig] = []
        self._load_configs()
        logger.info(
            f"声音复刻服务初始化: config_path={config_path}, "
            f"已加载 {len(self._voices)} 个音色"
        )

    def _load_configs(self) -> None:
        """从本地文件加载音色配置。"""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._voices = [
                    VoiceCloneConfig(**item) for item in data
                ]
                logger.info(f"加载了 {len(self._voices)} 个音色配置")
            except Exception as e:
                logger.warning(f"加载音色配置失败: {e}")
                self._voices = []
        else:
            self._voices = []

    def _save_configs(self) -> None:
        """将音色配置保存到本地文件。"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(
                    [v.model_dump() for v in self._voices],
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
            logger.info(f"保存了 {len(self._voices)} 个音色配置")
        except Exception as e:
            logger.error(f"保存音色配置失败: {e}")

    def _validate_audio_file(self, audio_file_path: str) -> None:
        """验证音频文件是否符合要求。

        Args:
            audio_file_path: 音频文件路径。

        Raises:
            ValueError: 文件不符合要求时抛出。
        """
        path = Path(audio_file_path)

        if not path.exists():
            raise ValueError(f"音频文件不存在: {audio_file_path}")

        if path.suffix.lower() not in self.SUPPORTED_AUDIO_FORMATS:
            raise ValueError(
                f"不支持的音频格式: {path.suffix}，"
                f"支持: {self.SUPPORTED_AUDIO_FORMATS}"
            )

        file_size_mb = path.stat().st_size / (1024 * 1024)
        if file_size_mb > self.MAX_AUDIO_SIZE_MB:
            raise ValueError(
                f"音频文件过大: {file_size_mb:.1f}MB，"
                f"最大: {self.MAX_AUDIO_SIZE_MB}MB"
            )

    async def clone_voice(
        self, audio_file_path: str, voice_name: str
    ) -> VoiceCloneConfig:
        """上传音频并创建零样本复刻音色。

        Args:
            audio_file_path: 参考音频文件路径（3-10秒清晰人声）。
            voice_name: 用户自定义的音色名称。

        Returns:
            创建的音色配置。

        Raises:
            ValueError: 音频文件不符合要求。
            RuntimeError: API 调用失败。
        """
        self._validate_audio_file(audio_file_path)

        logger.info(
            f"开始声音复刻: name={voice_name}, "
            f"file={audio_file_path}"
        )

        try:
            import dashscope
            from dashscope.audio.tts_v2 import VoiceCloneManager

            if self.api_key:
                dashscope.api_key = self.api_key

            # 上传参考音频并创建复刻音色
            # 使用 DashScope Voice Enrollment API
            voice_id = VoiceCloneManager.upload(
                audio_file_path=audio_file_path,
                voice_name=voice_name,
            )

            if not voice_id:
                raise RuntimeError("声音复刻 API 未返回有效的 voice_id")

            config = VoiceCloneConfig(
                voice_id=voice_id,
                name=voice_name,
                description=f"从 {Path(audio_file_path).name} 复刻的音色",
            )

            # 添加到列表并持久化
            self._voices.append(config)
            self._save_configs()

            logger.info(
                f"声音复刻成功: voice_id={voice_id}, name={voice_name}"
            )

            # 清理本地音频文件（保护隐私）
            try:
                os.remove(audio_file_path)
                logger.info(f"已清理参考音频文件: {audio_file_path}")
            except OSError:
                logger.warning(f"清理参考音频文件失败: {audio_file_path}")

            return config

        except ImportError:
            logger.error(
                "dashscope 未安装，请执行: pip install dashscope"
            )
            raise RuntimeError("dashscope SDK 未安装")
        except Exception as e:
            logger.error(f"声音复刻失败: {e}", exc_info=True)
            raise RuntimeError(f"声音复刻失败: {e}") from e

    async def list_voices(self) -> List[VoiceCloneConfig]:
        """获取当前可用的复刻音色列表。

        Returns:
            复刻音色配置列表。
        """
        return list(self._voices)

    async def get_voice(self, voice_id: str) -> Optional[VoiceCloneConfig]:
        """根据 voice_id 获取音色配置。

        Args:
            voice_id: 音色 ID。

        Returns:
            匹配的音色配置，未找到返回 None。
        """
        for voice in self._voices:
            if voice.voice_id == voice_id:
                return voice
        return None

    async def delete_voice(self, voice_id: str) -> bool:
        """删除一个复刻音色。

        Args:
            voice_id: 要删除的音色 ID。

        Returns:
            是否成功删除。
        """
        original_count = len(self._voices)
        self._voices = [v for v in self._voices if v.voice_id != voice_id]

        if len(self._voices) < original_count:
            self._save_configs()
            logger.info(f"已删除音色: {voice_id}")
            return True
        else:
            logger.warning(f"未找到音色: {voice_id}")
            return False
