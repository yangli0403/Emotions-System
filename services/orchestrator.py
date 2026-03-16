"""
Emotions-System — 编排器实现

系统的核心协调者，管理对话状态，协调各服务之间的数据流。
完整流程:
  用户输入 → LLM → ActionParser → SoundTagConverter → CommandPackager(+TTS+Fallback)
  → ProtocolAdapter → WebSocket 输出
"""

from __future__ import annotations

import logging
from typing import AsyncIterator, Dict, List, Optional

from core.interfaces import ILLMService, IProtocolAdapter
from core.models import MultimodalSegment
from services.action_parser import ActionParser
from services.command_packager import CommandPackager

logger = logging.getLogger(__name__)


class Orchestrator:
    """默认编排器实现。

    协调 LLM → ActionParser → CommandPackager → ProtocolAdapter
    的完整数据流。管理多会话的对话历史。
    """

    def __init__(
        self,
        llm_service: ILLMService,
        action_parser: ActionParser,
        command_packager: CommandPackager,
        protocol_adapter: IProtocolAdapter,
    ) -> None:
        """初始化编排器。

        Args:
            llm_service: 大语言模型服务。
            action_parser: 动作解析器。
            command_packager: 指令包装器。
            protocol_adapter: 协议适配器。
        """
        self.llm_service = llm_service
        self.action_parser = action_parser
        self.command_packager = command_packager
        self.protocol_adapter = protocol_adapter
        self._histories: Dict[str, List[dict]] = {}

        logger.info("编排器初始化完成")

    def get_history(self, session_id: str) -> List[dict]:
        """获取指定会话的对话历史。"""
        if session_id not in self._histories:
            self._histories[session_id] = []
        return self._histories[session_id]

    async def handle_text_input(
        self, session_id: str, text: str
    ) -> AsyncIterator[dict]:
        """处理用户的文本输入，返回多模态响应流。

        完整流程：
        1. 更新对话历史
        2. LLM 流式生成带标签的文本
        3. 动作解析器分离文本和标签
        4. 指令包装器组装多模态片段（含音效转换、TTS、兜底推理）
        5. 协议适配器转换为前端兼容格式

        Args:
            session_id: 会话 ID。
            text: 用户输入的文本。

        Yields:
            前端兼容的 JSON 字典。
        """
        logger.info(
            f"处理文本输入: session={session_id}, text='{text[:50]}'"
        )

        if not text.strip():
            yield {"type": "info", "message": "输入为空"}
            return

        # Step 1: 更新对话历史
        history = self.get_history(session_id)
        history.append({"role": "user", "content": text})

        # Step 2: LLM 流式生成
        try:
            llm_stream = self.llm_service.generate_response_stream(
                prompt=text, history=history[:-1]  # 不含当前消息
            )
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            yield {"type": "error", "message": f"AI 生成失败: {e}"}
            return

        # Step 3: 动作解析
        sentence_stream = self.action_parser.parse_stream(llm_stream)

        # Step 4: 指令包装（含音效转换、TTS、兜底推理）
        segment_stream = self.command_packager.package_stream(sentence_stream)

        # Step 5: 协议适配并输出
        full_response_text = ""
        async for segment in segment_stream:
            full_response_text += segment.text
            adapted_message = self.protocol_adapter.adapt(segment)
            yield adapted_message

        # 将完整的助手回复添加到对话历史
        if full_response_text:
            history.append({
                "role": "assistant",
                "content": full_response_text,
            })

        # 发送结束标记
        yield {"type": "end"}

    def clear_history(self, session_id: str) -> None:
        """清除指定会话的对话历史。"""
        if session_id in self._histories:
            del self._histories[session_id]
            logger.info(f"已清除会话历史: {session_id}")
