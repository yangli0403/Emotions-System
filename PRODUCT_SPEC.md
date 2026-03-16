# Emotions-System — Product Specification

## Product Vision

Emotions-System 是下一代多模态情感交互系统，它在原有 Emotions-Express 的模块化流水线基础上，深度整合了阿里通义实验室开源的 CosyVoice 语音生成模型。本系统旨在突破传统 TTS 引擎在情感粒度和音效表现上的瓶颈，通过支持 100+ 种细粒度情感指令控制、将笑声/呼吸声等音效内生融入语音流，并引入强大的零样本声音复刻能力。系统预留了基于大语言模型的句内情感分割与上下文情感推断架构，为虚拟人、数字人和智能语音助手提供接近真人水平的细腻、自然的多模态交互体验。

## Target Users

- **虚拟主播 (VTuber) 开发者**：需要将文本对话转化为带有丰富情感、表情和动作的实时语音流，以驱动前端虚拟形象。
- **数字人交互平台构建者**：希望在客户服务、教育辅导或娱乐陪伴场景中，提供具备高情商和自然语音表现力的数字人。
- **AI 语音应用研究者**：需要一个模块化、可扩展的测试平台，用于验证新型情感推断算法在端到端交互系统中的效果。

## Core Features (MVP)

### Feature 1: 基于 CosyVoice 的细粒度情感语音合成
- **Description**: 使用阿里百炼平台提供的 `cosyvoice-v3.5-flash` API，支持通过自然语言指令（如“语气活泼俏皮，带着明显的笑意”）来控制生成的语音风格，打破原有 7 种粗粒度情感枚举的限制。
- **User Story**: 作为一名虚拟主播开发者，我希望大语言模型生成的文本能够带有详细的情感指令，这样生成的语音就能展现出复杂的、混合的情绪（如“强压怒火的平静”），让虚拟主播听起来更像真人。
- **Priority**: High

### Feature 2: 音效标签的内生融合 (SoundTagConverter)
- **Description**: 新增 `SoundTagConverter` 模块，拦截 `[sound:laugh]`、`[sound:sigh]` 等音效标签，并将其转换为 CosyVoice 支持的文本内标记（如 `[laughter]`、`[breath]`），使音效直接由 TTS 模型合成，融入语音流中。
- **User Story**: 作为一名听众，我希望在虚拟主播讲笑话时，笑声能和她说话的语音自然连贯地结合在一起，而不是像播放两个独立的音频文件那样产生断层感。
- **Priority**: High

### Feature 3: 声音复刻与管理模块 (Voice Cloning)
- **Description**: 提供一套基于阿里百炼 API 的声音复刻工具，允许用户通过上传 3-10 秒的参考音频，零样本（Zero-shot）快速克隆目标音色。该模块支持音色特征的提取、保存和在 TTS 合成中的动态加载。
- **User Story**: 作为一名数字人运营者，我希望能够上传一段我自己的录音，让系统在后续的对话中完全使用我的声音进行回复，并且还能带有各种情感变化。
- **Priority**: High

### Feature 4: 双向流式合成与低延迟交互
- **Description**: 采用 DashScope SDK 的双向流式调用模式（`streaming_call`），在 LLM 逐句输出文本的同时实时发送给 CosyVoice API，并通过回调函数增量接收音频流，大幅降低端到端延迟。
- **User Story**: 作为一名数字人交互平台构建者，我希望用户在说完话后能尽快听到数字人的回复，并且语音是边生成边播放的，从而保证对话的流畅性。
- **Priority**: High

### Feature 5: 可插拔的兜底推理服务架构
- **Description**: 重构 `FallbackInferenceService`，在保留原有基于规则匹配的兜底方案（`RuleBasedFallback`）的同时，定义清晰的接口，为未来接入基于 BERT 的轻量级情感推断预留架构空间。
- **User Story**: 作为一名 AI 研究者，我希望能够轻松地将自己训练的 BERT 情感分类模型接入系统，用于在 LLM 未输出情感标签时自动推断文本情感。
- **Priority**: Medium

## 基础功能测试样例 (Test Cases)

为了验证上述核心功能，系统在测试阶段应能正确处理以下特定格式的输入，并产生预期的合成效果：

### 样例 1：细粒度情感指令测试
- **输入文本**: `[emotion:angry|instruction:语气冰冷，带着强烈的压迫感和嘲讽] 你觉得这样就能骗过我吗？简直可笑。`
- **预期输出**: 系统提取基础枚举 `angry` 供前端驱动愤怒表情，同时将文本与指令发送给 CosyVoice。合成的语音应具有低沉、冰冷且带有嘲讽意味的语调，而非普通的大声咆哮。

### 样例 2：音效内生融合测试
- **输入文本**: `[emotion:happy] 哎呀，你这个人怎么这么有趣 [sound:laugh] 真是笑死我了。`
- **预期输出**: `SoundTagConverter` 将文本转换为 `哎呀，你这个人怎么这么有趣 [laughter] 真是笑死我了。` 语音合成时，笑声应与前后文本使用相同的音色，且过渡平滑无断层。

### 样例 3：呼吸声节奏控制测试
- **输入文本**: `[emotion:fearful|instruction:语速极快，声音颤抖] 我...我刚刚看到 [sound:gasp] 窗外好像有个人影！`
- **预期输出**: `SoundTagConverter` 将 `[sound:gasp]` 转换为 `[breath]`。合成的语音应体现出明显的惊恐颤抖，并在“看到”之后产生急促的倒吸凉气（呼吸声）效果。

### 样例 4：声音复刻一致性测试
- **操作流程**: 
  1. 通过声音复刻模块上传一段 5 秒的女性温柔声音样本（如 `reference_female.wav`）。
  2. 使用该复刻音色 ID 合成测试文本：`[emotion:sad|instruction:带着哭腔的委屈] 为什么每次都是我被留下来...`
- **预期输出**: 合成的语音必须高度还原 `reference_female.wav` 的音色特征，同时成功叠加“哭腔”的情感风格，证明声音复刻与情感指令可以完美兼容。

## Anti-Features

本系统明确**不包含**以下功能：
- **前端动画渲染**：系统仅负责后端流水线处理，输出包含音频、动作、表情指令的 WebSocket JSON 数据流，不负责具体的 3D/2D 模型渲染。
- **本地大模型部署**：系统默认依赖云端 LLM API（如 OpenAI 兼容接口）和云端 TTS API（阿里百炼），不包含本地部署这些庞大模型的复杂配置。
- **视频流生成**：系统输出的是音频流和控制指令，而不是直接合成带有画面的视频流。

## Technical Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Language | Python 3.11+ | AI 和数据处理生态最丰富的语言，开发效率高 |
| Web Framework | FastAPI | 支持异步 I/O 和 WebSocket，非常适合构建流式交互系统 |
| TTS Engine | 阿里百炼 CosyVoice API | 提供 100+ 种细粒度情感指令控制、音效标记和双向流式合成能力 |
| Voice Cloning | DashScope Voice API | 官方提供的声音复刻接口，支持零样本音色克隆 |
| LLM Integration | OpenAI Python Client | 兼容主流大模型 API，用于生成对话文本和复合情感指令 |

## Key Assumptions

1. 阿里百炼平台的 `cosyvoice-v3.5-flash` 模型 API 能够保持稳定的响应速度和并发处理能力。
2. 现有的虚拟人前端能够兼容并忽略它们无法识别的新型自然语言情感指令，仅依赖基础的情感枚举进行动画状态切换。
3. 大语言模型在经过系统提示词引导后，能够稳定地输出符合 `[emotion:基础枚举|instruction:自然语言指令]` 格式的复合标签。

## Known Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| 阿里百炼 API 网络延迟过高导致交互卡顿 | High | Medium | 强制使用双向流式调用；实现句子级别的缓冲和预处理；保留 EdgeTTS 作为网络不佳时的降级方案。 |
| LLM 无法稳定输出复合情感标签格式 | High | Low | 提供详细的 Few-shot 示例在系统提示词中；在 `ActionParser` 中实现健壮的正则表达式和容错解析逻辑。 |
| 声音复刻 API 的审核与限制 | Medium | Medium | 在复刻模块中增加异常处理，提示用户音频需清晰无噪音，并处理 API 返回的频率限制错误。 |

## Success Criteria

1. **功能实现**：成功将 EE 格式的音效标签转换为 CosyVoice 标记并合成出自然连贯的语音。
2. **声音复刻**：用户可通过系统提供的接口或脚本成功上传音频并创建复刻音色，且该音色可被 TTS 服务调用。
3. **情感表现**：系统能够解析复合情感标签，并通过 CosyVoice API 展现出超越 7 种基础枚举的细腻语音风格。
4. **延迟指标**：在网络状况良好的情况下，端到端延迟控制在 1000ms 以内。
