"""
Emotions-System — 兜底推理服务实现

当 LLM 未能生成情感标签时，根据文本语义自动推断情感。

实现层次：
- V1: RuleBasedFallbackService — 基于关键词匹配的规则引擎（当前）
- V2: BERTFallbackService — 基于 BERT 的轻量级分类模型（预留）
- V3: SegmentAwareFallbackService — 句内情感分割（预留）
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Tuple

from core.interfaces import IFallbackInferenceService
from core.models import ActionTag

logger = logging.getLogger(__name__)


class RuleBasedFallbackService(IFallbackInferenceService):
    """V1: 基于规则的兜底推理服务。

    使用关键词匹配来推断情感，并生成对应的自然语言指令。
    """

    # 情感关键词映射：每个情感对应一组关键词及其权重
    EMOTION_KEYWORDS: Dict[str, List[Tuple[str, float]]] = {
        "happy": [
            ("开心", 1.0), ("高兴", 1.0), ("太棒了", 1.0), ("喜欢", 0.8),
            ("哈哈", 1.2), ("太好了", 1.0), ("真好", 0.8), ("快乐", 1.0),
            ("幸福", 0.9), ("棒", 0.7), ("赞", 0.7),
        ],
        "sad": [
            ("难过", 1.0), ("伤心", 1.0), ("抱歉", 0.8), ("对不起", 0.8),
            ("遗憾", 0.9), ("可惜", 0.7), ("唉", 0.6), ("不幸", 0.9),
            ("失望", 0.8), ("痛苦", 1.0), ("心疼", 0.9),
        ],
        "angry": [
            ("生气", 1.0), ("讨厌", 0.9), ("烦", 0.7), ("愤怒", 1.2),
            ("过分", 0.8), ("岂有此理", 1.0), ("可恶", 1.0),
        ],
        "surprised": [
            ("真的吗", 1.0), ("哇", 1.0), ("天哪", 1.0), ("不会吧", 0.9),
            ("居然", 0.8), ("竟然", 0.8), ("没想到", 0.9), ("惊讶", 1.0),
            ("厉害", 0.7),
        ],
        "fearful": [
            ("害怕", 1.0), ("恐怖", 1.0), ("可怕", 0.9), ("担心", 0.7),
            ("紧张", 0.7), ("不安", 0.6), ("慌", 0.8),
        ],
        "disgusted": [
            ("恶心", 1.0), ("受不了", 0.7), ("太差了", 0.8), ("呕", 0.9),
        ],
    }

    # 情感 → 默认自然语言指令
    DEFAULT_INSTRUCTIONS: Dict[str, str] = {
        "happy": "用开心愉悦的语气说话，带着笑意。",
        "sad": "用低沉哀伤的语气说话，带有轻微叹息。",
        "angry": "用严厉不满的语气说话，带有压抑的怒意。",
        "surprised": "用充满惊讶的语气说话，语调上扬。",
        "fearful": "用紧张颤抖的语气说话，充满恐惧。",
        "disgusted": "用厌恶不屑的语气说话。",
        "neutral": "用平静温和的语气说话。",
    }

    async def infer_emotion(self, text: str) -> ActionTag:
        """根据文本中的关键词推断情感。

        对每个情感类型计算关键词匹配的加权得分，返回得分最高的情感。
        如果没有匹配到任何关键词，返回 neutral。

        Args:
            text: 纯文本内容。

        Returns:
            推断出的 ActionTag（包含情感枚举和自然语言指令）。
        """
        if not text or not text.strip():
            return ActionTag(
                tag_type="emotion",
                value="neutral",
                instruction=self.DEFAULT_INSTRUCTIONS["neutral"],
            )

        text_lower = text.lower()
        scores: Dict[str, float] = {}

        for emotion, keywords in self.EMOTION_KEYWORDS.items():
            score = 0.0
            for keyword, weight in keywords:
                if keyword.lower() in text_lower:
                    score += weight
            if score > 0:
                scores[emotion] = score

        if not scores:
            logger.debug(
                f"兜底推理：未匹配到情感关键词，返回 neutral。"
                f"文本: {text[:50]}"
            )
            return ActionTag(
                tag_type="emotion",
                value="neutral",
                instruction=self.DEFAULT_INSTRUCTIONS["neutral"],
            )

        best_emotion = max(scores, key=scores.get)
        instruction = self.DEFAULT_INSTRUCTIONS.get(
            best_emotion, self.DEFAULT_INSTRUCTIONS["neutral"]
        )

        logger.info(
            f"兜底推理：推断情感为 {best_emotion}，"
            f"得分: {scores[best_emotion]:.1f}。文本: {text[:50]}"
        )

        return ActionTag(
            tag_type="emotion",
            value=best_emotion,
            instruction=instruction,
        )


class BERTFallbackService(IFallbackInferenceService):
    """V2: 基于 BERT 的兜底推理服务（预留接口）。

    参考 De et al. (2024) 的方法，使用预训练的 BERT 模型
    进行文本情感分类。

    TODO: 实现以下功能：
    1. 加载预训练的中文 BERT 情感分类模型
    2. 对输入文本进行 tokenize 和推理
    3. 将分类结果映射为 ActionTag
    4. 支持 GPU 加速推理
    """

    def __init__(self, model_path: str = "") -> None:
        self.model_path = model_path
        logger.info(
            "BERTFallbackService 初始化（预留接口，尚未实现）"
        )

    async def infer_emotion(self, text: str) -> ActionTag:
        """基于 BERT 模型推断情感（预留）。"""
        raise NotImplementedError(
            "BERTFallbackService 尚未实现。"
            "请参考 De et al. (2024) 的方法进行实现。"
        )


class SegmentAwareFallbackService(IFallbackInferenceService):
    """V3: 句内情感分割兜底推理服务（预留接口）。

    参考 Segment-Aware Conditioning (2025) 的方法，
    将一句话中的多种情感分割成不同段分别合成。

    例如："虽然很难过，但我还是很感谢你"
    → [("虽然很难过，", sad), ("但我还是很感谢你", happy)]

    TODO: 实现以下功能：
    1. 使用 NLP 模型进行子句分割
    2. 对每个子句进行独立的情感分类
    3. 返回带有分段信息的 ActionTag 列表
    4. 与 CommandPackager 配合，对每段使用不同的 instruction
    """

    def __init__(self, model_path: str = "") -> None:
        self.model_path = model_path
        logger.info(
            "SegmentAwareFallbackService 初始化（预留接口，尚未实现）"
        )

    async def infer_emotion(self, text: str) -> ActionTag:
        """基于句内情感分割推断情感（预留）。"""
        raise NotImplementedError(
            "SegmentAwareFallbackService 尚未实现。"
            "请参考 Segment-Aware Conditioning (2025) 的方法进行实现。"
        )

    async def segment_emotions(
        self, text: str
    ) -> List[Tuple[str, ActionTag]]:
        """将文本分割为多个情感段（预留）。

        Args:
            text: 可能包含多种情感的文本。

        Returns:
            (子句文本, 对应情感标签) 的列表。
        """
        raise NotImplementedError(
            "segment_emotions 尚未实现。"
        )
