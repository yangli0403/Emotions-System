from pydantic import BaseModel, Field
from typing import List, Optional

class ActionTag(BaseModel):
    """表示从文本中解析出的控制指令（如情感、音效、动作）"""
    tag_type: str        # e.g., "emotion", "sound", "action"
    value: str           # 基础枚举值，e.g., "happy", "laugh"
    instruction: str = "" # 附加的自然语言指令，e.g., "语气活泼俏皮" (可选)

class ParsedSentence(BaseModel):
    """表示 LLM 输出的单个完整句子"""
    text: str
    tags: List[ActionTag] = Field(default_factory=list)
    is_final: bool = False # 是否是 LLM 响应的最后一句

class MultimodalSegment(BaseModel):
    """系统最终输出给协议适配器的对象"""
    audio_content: bytes       # 原始 WAV 音频数据
    text: str                  # 对应的文本
    emotion: str = "neutral"   # 基础情感枚举，用于前端表情驱动
    actions: List[str] = Field(default_factory=list) # 动作指令列表
    is_final: bool = False     # 是否是当前对话的最后一段

class VoiceCloneConfig(BaseModel):
    """声音复刻配置"""
    voice_id: str              # 阿里百炼返回的复刻音色 ID
    name: str                  # 用户自定义的音色名称
    description: str = ""      # 音色描述
