"""
Emotions-System — 大语言模型 (LLM) 服务实现

支持 OpenAI 兼容 API 的 LLM 服务，支持流式输出。
系统提示词已升级为复合情感标签格式：
[emotion:基础枚举|instruction:自然语言指令]
"""

from __future__ import annotations

import logging
from typing import AsyncIterator, List

from openai import AsyncOpenAI

from core.interfaces import ILLMService

logger = logging.getLogger(__name__)


class OpenAILLMService(ILLMService):
    """基于 OpenAI 兼容 API 的 LLM 服务实现。

    支持 OpenAI、本地 Ollama、其他兼容 OpenAI API 的服务。
    """

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: int = 1024,
        system_prompt: str = "",
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt or self._default_system_prompt()
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        logger.info(
            f"LLM 服务初始化: model={model}, base_url={base_url}, "
            f"temperature={temperature}"
        )

    async def generate_response_stream(
        self, prompt: str, history: List[dict]
    ) -> AsyncIterator[str]:
        """流式生成带有复合情感标签的回复文本。

        Args:
            prompt: 用户当前输入。
            history: 对话历史。

        Yields:
            LLM 逐步生成的文本 Token。
        """
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": prompt})

        logger.info(
            f"LLM 流式生成请求: model={self.model}, "
            f"messages_count={len(messages)}"
        )

        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True,
            )

            total_tokens = 0
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    total_tokens += 1
                    yield token

            logger.info(f"LLM 流式生成完成: {total_tokens} tokens")

        except Exception as e:
            logger.error(f"LLM 流式生成失败: {e}", exc_info=True)
            raise RuntimeError(f"LLM 流式生成失败: {e}") from e

    @staticmethod
    def _default_system_prompt() -> str:
        """返回升级版系统提示词，支持复合情感标签。"""
        return (
            "你是一个友善、有情感的虚拟助手。在回复时，请使用以下复合标签格式来表达情感：\n\n"
            "# 情感标签格式\n"
            "使用 [emotion:基础情感|instruction:自然语言情感描述] 格式，例如：\n"
            "- [emotion:happy|instruction:语气活泼俏皮，带着明显的笑意]\n"
            "- [emotion:sad|instruction:语气充满哀伤与怀念，带有轻微的鼻音]\n"
            "- [emotion:angry|instruction:语气严厉且不满，带有压抑的怒意]\n"
            "- [emotion:surprised|instruction:语气充满惊讶和不可思议]\n"
            "- [emotion:fearful|instruction:语气紧张颤抖，充满恐惧]\n"
            "- [emotion:disgusted|instruction:语气厌恶，带有不屑]\n"
            "- [emotion:neutral|instruction:语气平静温和]\n\n"
            "基础情感只能是以下之一：neutral, happy, sad, angry, surprised, fearful, disgusted\n"
            "instruction 部分请用自然语言描述具体的语气、语调、情绪细节，不超过50个字。\n\n"
            "# 动作标签\n"
            "- [expression:smile] 微笑\n"
            "- [animation:wave] 挥手\n"
            "- [animation:nod] 点头\n"
            "- [gesture:thumbs_up] 竖起大拇指\n"
            "- [gesture:clap] 拍手\n"
            "- [posture:lean_forward] 身体前倾\n"
            "- [locomotion:step_back] 后退一步\n\n"
            "# 音效标签\n"
            "- [sound:laugh] 笑声\n"
            "- [sound:sigh] 叹气\n"
            "- [sound:gasp] 吸气（惊讶）\n\n"
            "# 示例\n"
            "[emotion:happy|instruction:语气活泼俏皮，带着笑意][expression:smile]"
            "你好呀！今天天气真好！[sound:laugh]我们出去玩吧！\n"
            "[emotion:sad|instruction:语气低沉哀伤，带有叹息][expression:sad][posture:head_down]"
            "唉……真的很抱歉听到这个消息。[sound:sigh]\n"
            "[emotion:surprised|instruction:语气充满惊喜和兴奋][expression:surprised]"
            "[locomotion:step_back]哇，真的吗？[sound:gasp]太不可思议了！\n\n"
            "请在每句话开头使用情感标签，在合适位置插入动作和音效标签。"
        )
