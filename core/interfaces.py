from abc import ABC, abstractmethod
from typing import AsyncGenerator, List
from .models import ActionTag, ParsedSentence, MultimodalSegment, VoiceCloneConfig

class ILLMService(ABC):
    @abstractmethod
    async def generate_response_stream(self, prompt: str, history: List[dict]) -> AsyncGenerator[str, None]:
        """流式生成带有情感/动作标签的回复文本。"""
        pass

class ITTSService(ABC):
    @abstractmethod
    async def synthesize_stream(self, text: str, emotion_instruction: str, voice_id: str) -> AsyncGenerator[bytes, None]:
        """双向流式合成语音。"""
        pass

class IVoiceCloningService(ABC):
    @abstractmethod
    async def clone_voice(self, audio_file_path: str, voice_name: str) -> VoiceCloneConfig:
        """上传音频并创建零样本复刻音色。"""
        pass
        
    @abstractmethod
    async def list_voices(self) -> List[VoiceCloneConfig]:
        """获取当前可用的复刻音色列表。"""
        pass

class IFallbackInferenceService(ABC):
    @abstractmethod
    async def infer_emotion(self, text: str) -> ActionTag:
        """根据文本内容推断最合适的情感枚举和指令。"""
        pass

class IProtocolAdapter(ABC):
    @abstractmethod
    def adapt(self, segment: MultimodalSegment) -> dict:
        """将系统内部的片段对象转换为前端期望的 JSON 字典。"""
        pass
