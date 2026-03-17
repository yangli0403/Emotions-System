# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-03-17

### Added

- **核心架构**：基于 Python 异步流式处理的多模态语音合成系统。
- **LLM 服务**：OpenAI 兼容的流式对话生成服务（`OpenAILLMService`）。
- **TTS 服务**：基于 CosyVoice v3.5 的双向流式语音合成（`CosyVoiceTTSService`），支持自然语言情感指令。
- **声音复刻**：基于 DashScope Voice Cloning API 的零样本声音复刻（`DashScopeVoiceCloningService`）。
- **动作解析器**：支持复合情感标签 `[emotion:value|instruction:text]` 和简单标签 `[tag:value]` 的流式解析（`ActionParser`）。
- **音效内生化**：将 `[sound:laugh]` 等音效标签转换为 CosyVoice 的 `[laughter]`、`[breath]` 文本内标记（`SoundTagConverter`）。
- **指令包装器**：将解析后的句子流结合 TTS 音频组装为 `MultimodalSegment`（`CommandPackager`）。
- **兜底推理**：V1 基于关键词匹配的规则引擎（`RuleBasedFallbackService`），预留 V2 BERT 分类和 V3 句内情感分割接口。
- **协议适配器**：Open-LLM-VTuber 前端协议兼容的 WebSocket JSON 输出（`OpenLLMVTuberAdapter`）。
- **编排器**：协调 LLM → 解析 → 包装 → 适配的完整数据流（`Orchestrator`）。
- **REST API**：声音复刻管理（CRUD）和独立 TTS 合成端点。
- **WebSocket 端点**：实时对话的流式交互接口。
- **配置管理**：基于环境变量的分层配置（`AppConfig`）。
- **自动化测试**：111 个单元测试，代码覆盖率 97%。
- **Docker 支持**：Dockerfile 和 docker-compose.yml。
- **CI/CD**：GitHub Actions 工作流（lint + test + coverage）。
- **完整文档**：产品规格、架构设计、接口设计、需求反思报告、可行性调研报告。
