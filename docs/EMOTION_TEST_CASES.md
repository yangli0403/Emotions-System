# Emotions-System 情感功能测试用例文档

**文档版本**：v1.0  
**更新日期**：2026-03-22  
**测试目标**：验证 Emotions-System 在情感解析、音效内生化、兜底推理及多版本模型切换等核心情感功能上的正确性与稳定性。

---

## 1. 情感标签解析测试 (ActionParser)

本模块测试系统能否正确从 LLM 输出的文本流中提取不同格式的情感和动作标签。

| 用例编号 | 测试场景 | 输入文本示例 | 预期解析结果 | 验证点 |
|---------|---------|-------------|-------------|-------|
| AP-01 | 简单情感标签解析 | `[emotion:happy]今天天气真好！` | `emotion_base="happy"`, `instruction=""`, `text="今天天气真好！"` | 基础枚举值提取正确，文本分离干净 |
| AP-02 | 复合情感标签解析 | `[emotion:sad|instruction:带着哭腔，声音颤抖]我真的尽力了。` | `emotion_base="sad"`, `instruction="带着哭腔，声音颤抖"`, `text="我真的尽力了。"` | 复合标签的枚举值和自然语言指令均提取正确 |
| AP-03 | 多标签混合解析 | `[emotion:surprised][action:wave]你居然来了！` | `tags=[emotion:surprised, action:wave]`, `text="你居然来了！"` | 同一句子中的多个标签能被全部提取 |
| AP-04 | 标签类型归一化 | `[expr:smile]你好呀。` | `tags=[expression:smile]` | `expr` 被正确归一化为 `expression` |
| AP-05 | 跨句标签解析 | `[emotion:happy]第一句。[emotion:sad]第二句。` | 产生两个 `ParsedSentence`，分别携带对应的情感标签 | 句子边界切分正确，标签不发生越界污染 |
| AP-06 | 无效/未知标签容错 | `[unknown:test]这是一段话。` | `tags=[]`, `text="这是一段话。"` | 未知标签被忽略，不影响正常文本输出 |

---

## 2. 音效内生化测试 (SoundTagConverter)

本模块测试系统能否将特定的音效标签转换为 CosyVoice 支持的文本内标记（如 `[laughter]`、`[breath]`）。

| 用例编号 | 测试场景 | 输入文本与标签 | 预期转换结果 | 验证点 |
|---------|---------|--------------|-------------|-------|
| ST-01 | 笑声标签内生化 | `text="太好笑了", tags=[sound:laugh]` | `text="太好笑了[laughter]"`, `tags=[]` | `laugh` 标签被移除，文本末尾追加 `[laughter]` |
| ST-02 | 呼吸声标签内生化 | `text="让我喘口气", tags=[sound:sigh]` | `text="让我喘口气[breath]"`, `tags=[]` | `sigh` 标签被移除，文本末尾追加 `[breath]` |
| ST-03 | 不支持音效透传 | `text="演出结束", tags=[sound:applause]` | `text="演出结束"`, `tags=[sound:applause]` | `applause` 不支持内生化，标签被保留供前端处理 |
| ST-04 | 混合音效处理 | `text="哈哈", tags=[sound:laugh, sound:bell]` | `text="哈哈[laughter]"`, `tags=[sound:bell]` | 支持的被内生化，不支持的被保留 |
| ST-05 | 同义音效映射 | `text="嘿嘿", tags=[sound:giggle]` | `text="嘿嘿[laughter]"`, `tags=[]` | `giggle` 被正确映射为 `[laughter]` |

---

## 3. 兜底推理测试 (FallbackInferenceService)

本模块测试当 LLM 未显式输出情感标签时，系统能否基于文本内容自动推断情感。

| 用例编号 | 测试场景 | 输入文本示例 | 预期推断结果 | 验证点 |
|---------|---------|-------------|-------------|-------|
| FB-01 | 明显开心语义 | `太棒了，我真的好开心！` | `emotion="happy"`, `instruction="用开心愉悦的语气说话..."` | 命中 happy 关键词，返回正确枚举和默认指令 |
| FB-02 | 明显愤怒语义 | `你太过分了，简直岂有此理！` | `emotion="angry"`, `instruction="用严厉不满的语气说话..."` | 命中 angry 关键词 |
| FB-03 | 明显悲伤语义 | `真的很遗憾，对不起。` | `emotion="sad"`, `instruction="用低沉哀伤的语气说话..."` | 命中 sad 关键词 |
| FB-04 | 无明显情感语义 | `今天下午两点开会。` | `emotion="neutral"`, `instruction="用平静温和的语气说话。"` | 未命中任何关键词，回退到 neutral |
| FB-05 | 显式标签覆盖 | `[emotion:sad]太棒了！` (文本与标签冲突) | `emotion="sad"` (由 CommandPackager 保证) | 兜底推理不被触发，显式标签优先级最高 |
| FB-06 | 空文本处理 | `   ` (仅空格) | `emotion="neutral"` | 空文本安全处理，不抛出异常 |

---

## 4. TTS 情感合成与模型切换测试 (CosyVoiceTTSService)

本模块测试 TTS 引擎对情感指令的响应，以及多版本模型切换的稳定性。

| 用例编号 | 测试场景 | 测试参数 | 预期合成结果 | 验证点 |
|---------|---------|---------|-------------|-------|
| TTS-01 | v1 基础情感合成 | `model="cosyvoice-v1"`, `voice="longxiaochun"`, `instruction="用开心愉悦的语气说话"` | 成功返回音频，听感上有明显笑意 | v1 模型正确接收并应用 instruction |
| TTS-02 | v3-flash 情感合成 | `model="cosyvoice-v3-flash"`, `voice="longanyang"`, `instruction="用愤怒的语气说话"` | 成功返回音频，听感上表现出愤怒 | v3-flash 模型正确接收并应用 instruction |
| TTS-03 | v3.5 无系统音色拦截 | `model="cosyvoice-v3.5-flash"`, `voice="longxiaochun"` | 合成失败或回退到默认复刻音色 | 验证 v3.5 对系统音色的限制处理逻辑 |
| TTS-04 | v3.5 复刻音色合成 | `model="cosyvoice-v3.5-flash"`, `voice="<复刻音色ID>"`, `instruction="用极度恐惧的声音说话"` | 成功返回音频，听感符合指令描述 | v3.5 成功使用复刻音色并应用任意指令 |
| TTS-05 | 默认指令回退 | `emotion_base="sad"`, `instruction=""` | 自动使用 `DEFAULT_EMOTION_INSTRUCTIONS["sad"]` 进行合成 | 当 instruction 为空时，正确映射默认指令 |
| TTS-06 | 指令长度截断 | `instruction="<超过100字符的超长指令...>"` | 成功返回音频，不抛出 API 错误 | 验证 `_get_instruction` 的 100 字符截断逻辑 |

---

## 5. 端到端集成测试 (CommandPackager & Orchestrator)

本模块测试整个流水线串联后的最终输出格式是否符合协议规范。

| 用例编号 | 测试场景 | 模拟 LLM 输出 | 预期最终 Segment 输出 | 验证点 |
|---------|---------|-------------|---------------------|-------|
| E2E-01 | 完整多模态片段 | `[emotion:happy|instruction:大笑][sound:laugh][action:wave]你好！` | `text="你好！[laughter]"`, `emotion="happy"`, `actions=["action:wave"]`, `audio_content` 非空 | 标签解析、音效内生化、动作提取、音频合成全链路正常 |
| E2E-02 | 纯文本无标签 | `你好。` | `text="你好。"`, `emotion="neutral"` (或兜底推断值), `actions=[]` | 无标签时系统能正常运行兜底逻辑并输出 |
| E2E-03 | 异常恢复 | TTS 服务抛出异常 | `audio_content=b""`, `text` 和 `emotion` 正常输出 | TTS 失败不阻塞文本和动作的下发，保证前端能显示文字 |

---

**测试执行建议**：
1. 单元测试可通过运行 `pytest tests/ -v` 自动执行。
2. TTS 合成听感测试（TTS-01 至 TTS-04）需通过 Web 测试面板（`http://localhost:8000`）进行人工 A/B 对比听测。
3. 端到端测试可通过 Web 面板的 WebSocket 聊天框输入特定格式的文本进行验证。
