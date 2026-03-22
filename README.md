# Emotions-System

**情感驱动的多模态语音合成系统** — 融合 Emotions-Express 与 CosyVoice 的下一代交互引擎。

Emotions-System 在原有 [Emotions-Express](https://github.com/Open-LLM-VTuber/Emotions-Express) 的模块化流水线基础上，深度整合了阿里通义实验室开源的 [CosyVoice](https://github.com/FunAudioLLM/CosyVoice) 语音生成模型，突破传统 TTS 引擎在情感粒度和音效表现上的瓶颈。系统支持 100+ 种细粒度情感指令控制、将笑声/呼吸声等音效内生融入语音流，并预留了基于 BERT 的句内情感分割与上下文情感推断能力，为虚拟人、数字人和智能语音助手提供接近真人水平的细腻、自然的多模态交互体验。

## Features

- **细粒度情感语音合成**：通过 CosyVoice 的自然语言指令（instruction），支持超越 7 种基础枚举的复杂情感表达（如"强压怒火的平静"、"带着自嘲的无奈"）。
- **音效标签内生融合**：`SoundTagConverter` 将 `[sound:laugh]`、`[sound:sigh]` 等音效标签转换为 CosyVoice 的 `[laughter]`、`[breath]` 文本内标记，让音效与语音无缝融合，音色一致。
- **双向流式合成**：采用 DashScope SDK 的流式调用模式，实现"边生成文本、边合成语音、边播放"的低延迟交互。
- **复合情感标签**：`[emotion:happy|instruction:语气活泼俏皮，带着明显的笑意]` 格式同时满足前端动画的离散状态需求和 TTS 的连续情感控制。
- **多 LLM 后端支持**：支持 OpenAI 兼容 API 和字节火山引擎 Ark SDK（DeepSeek/豆包等模型），通过配置切换。
- **可插拔兜底推理**：预留 V1（规则引擎）、V2（BERT 分类）、V3（句内情感分割）三级兜底推理架构。
- **零样本声音复刻**：通过 DashScope Voice Cloning API，上传 3-10 秒参考音频即可创建个性化音色。
- **Web 测试面板**：内置可视化测试界面，支持 WebSocket 对话、TTS 独立测试、音色管理，**新增多版本模型（v1/v3/v3.5）一键切换与 A/B 对比功能**。
- **Open-LLM-VTuber 协议兼容**：输出格式完全兼容主流虚拟人前端项目。

## Prerequisites

- Python >= 3.11
- 阿里百炼 DashScope API Key（用于 CosyVoice TTS 和声音复刻）
- LLM API Key（支持以下两种之一）：
  - **字节火山引擎 Ark SDK**（推荐，支持 DeepSeek/豆包模型）
  - **OpenAI 兼容 API**（OpenAI、Azure OpenAI 等）

## Quick Start

### 方式一：Manus 环境一键启动

```bash
# 克隆仓库
git clone https://github.com/yangli0403/Emotions-System.git
cd Emotions-System

# 运行 Manus 一键配置脚本
bash scripts/setup_manus.sh
# 首次运行会创建 .env 文件，编辑后再次运行即可启动
```

### 方式二：手动安装

```bash
# 1. 克隆仓库
git clone https://github.com/yangli0403/Emotions-System.git
cd Emotions-System

# 2. 安装依赖
pip install -e ".[dev]"

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的 API Key（参见下方配置说明）

# 4. 启动服务
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### 方式三：Windows 本地部署

```cmd
:: 1. 克隆仓库
git clone https://github.com/yangli0403/Emotions-System.git
cd Emotions-System

:: 2. 切换到 Windows 适配分支（可选）
git checkout windows-deploy

:: 3. 运行一键启动脚本
scripts\start_windows.bat
:: 首次运行会自动创建 .env 文件，填入 API Key 后重新运行即可
```

详细的 Windows 部署步骤请参见 [Windows 部署指南](docs/WINDOWS_DEPLOYMENT_GUIDE.md)。

### 方式四：Docker 部署

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 文件

# 2. 启动容器
docker-compose up -d
```

启动后访问 `http://localhost:8000` 即可打开 Web 测试面板。

## Configuration

### LLM 后端配置

系统支持两种 LLM 后端，通过 `LLM_BACKEND` 环境变量切换：

| Variable | 字节 Ark 后端 | OpenAI 后端 |
|----------|--------------|-------------|
| `LLM_BACKEND` | `ark` | `openai` |
| `LLM_API_KEY` | 火山引擎 API Key | OpenAI API Key |
| `LLM_MODEL` | Endpoint ID（如 `ep-xxxxxxx`） | 模型名（如 `gpt-4`） |
| `LLM_BASE_URL` | 无需设置 | `https://api.openai.com/v1` |

### TTS 配置

| Variable | Description | Default |
|----------|-------------|---------|
| `DASHSCOPE_API_KEY` | 阿里百炼 DashScope API 密钥 | `""` |
| `TTS_MODEL` | CosyVoice 模型版本（推荐 `cosyvoice-v1`） | `cosyvoice-v1` |
| `TTS_DEFAULT_VOICE` | 默认音色 ID | `longxiaochun` |

> **关于模型版本的选择：**
> - **cosyvoice-v1**：性价比最高（1元/万字符），支持 instruction 情感指令，内置 `longxiaochun` 等系统音色。
> - **cosyvoice-v3-flash**：支持 instruction、SSML 和多语种，内置 `longanyang` 等系统音色。
> - **cosyvoice-v3.5-flash / plus**：最新版本，支持任意自然语言指令控制，效果最好。**注意：v3.5 系列没有系统音色，必须先通过声音复刻创建音色后才能使用。**
> 
> *您可以在 Web 测试面板中直接切换这几个版本进行 A/B 对比测试。*

### 全部环境变量

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_BACKEND` | LLM 后端类型 | `ark` |
| `LLM_API_KEY` | LLM API 密钥 | `""` |
| `LLM_BASE_URL` | LLM API 基础 URL（OpenAI 后端） | `https://api.openai.com/v1` |
| `LLM_MODEL` | LLM 模型名称或 Endpoint ID | `gpt-4` |
| `LLM_TEMPERATURE` | LLM 生成温度 | `0.7` |
| `LLM_MAX_TOKENS` | LLM 最大 Token 数 | `1024` |
| `DASHSCOPE_API_KEY` | 阿里百炼 DashScope API 密钥 | `""` |
| `TTS_MODEL` | CosyVoice 模型版本 | `cosyvoice-v1` |
| `TTS_DEFAULT_VOICE` | 默认音色 ID | `longxiaochun` |
| `VOICE_CONFIG_PATH` | 复刻音色配置文件路径 | `data/voice_configs.json` |
| `SERVER_HOST` | 服务器监听地址 | `0.0.0.0` |
| `SERVER_PORT` | 服务器监听端口 | `8000` |
| `SERVER_WS_PATH` | WebSocket 路径 | `/ws` |

## Project Structure

```
Emotions-System/
├── core/                       # 核心数据模型和抽象接口
│   ├── models.py               # ActionTag, ParsedSentence, MultimodalSegment, VoiceCloneConfig
│   └── interfaces.py           # ILLMService, ITTSService, IVoiceCloningService, IFallbackInferenceService, IProtocolAdapter
├── services/                   # 业务逻辑实现
│   ├── llm_service.py          # OpenAI 兼容 LLM + 字节 Ark SDK 双后端
│   ├── tts_service.py          # CosyVoice TTS 服务（流式合成）
│   ├── voice_cloning_service.py # 声音复刻服务
│   ├── action_parser.py        # 动作/情感标签解析器
│   ├── sound_tag_converter.py  # 音效标签内生化转换器
│   ├── command_packager.py     # 指令包装器（组装多模态片段）
│   ├── fallback_inference_service.py # 兜底推理服务（V1规则/V2 BERT/V3分割）
│   └── orchestrator.py         # 编排器（协调完整数据流）
├── adapters/                   # 协议适配层
│   └── protocol_adapter.py     # Open-LLM-VTuber 协议适配器
├── static/                     # Web 测试前端
│   └── index.html              # 可视化测试面板
├── scripts/                    # 工具脚本
│   ├── start.sh                # Linux/macOS 快速启动脚本
│   ├── start_windows.bat       # Windows CMD 一键启动脚本
│   ├── start_windows.ps1       # Windows PowerShell 启动脚本
│   └── setup_manus.sh          # Manus 环境一键配置脚本
├── data/                       # 运行时数据目录
│   ├── uploads/                # 音频上传目录
│   └── output/                 # 合成音频输出目录
├── config.py                   # 配置管理（环境变量加载）
├── main.py                     # FastAPI 应用入口
├── tests/                      # 自动化测试套件（111 个测试，覆盖率 97%）
├── docs/                       # 项目文档
│   ├── EMOTION_TEST_CASES.md   # 情感功能测试用例文档
│   ├── WINDOWS_DEPLOYMENT_GUIDE.md # Windows 部署指南
│   ├── FEASIBILITY_RESEARCH_REPORT.docx
│   ├── PRODUCT_SPEC.docx
│   ├── ARCHITECTURE_DESIGN.docx
│   ├── INTERFACE_DATA_STRUCTURE_DESIGN.docx
│   └── REQUIREMENTS_REFLECTION_REPORT.docx
├── diagrams/                   # 架构图
│   ├── architecture.mmd
│   └── architecture.png
├── pyproject.toml              # 项目配置和依赖
├── Dockerfile                  # Docker 容器化配置
├── docker-compose.yml          # Docker Compose 编排
├── .github/workflows/ci.yml    # GitHub Actions CI 配置
├── .env.example                # 环境变量模板
└── .gitignore
```

## Running Tests

```bash
# 运行全部测试并生成覆盖率报告
pytest --cov=core --cov=services --cov=adapters --cov=config --cov-report=term-missing -v

# 运行特定模块的测试
pytest tests/test_action_parser.py -v

# 生成 HTML 覆盖率报告
pytest --cov=. --cov-report=html
```

当前测试状态：**111 个测试全部通过，代码覆盖率 97%**。

## API Endpoints

### WebSocket

| Endpoint | Description |
|----------|-------------|
| `ws://host:port/ws` | 实时对话 WebSocket 端点 |

### REST API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/voice/clone` | 上传音频创建复刻音色 |
| `GET` | `/api/voice/list` | 获取所有可用复刻音色 |
| `DELETE` | `/api/voice/{voice_id}` | 删除一个复刻音色 |
| `POST` | `/api/tts/synthesize` | 合成音频并返回 WAV 文件 |
| `POST` | `/api/tts/synthesize-to-file` | 合成音频并保存到服务器 |
| `GET` | `/health` | 健康检查 |

## Architecture

系统采用基于 Python 的异步流式处理架构，核心数据流为：

```
用户输入 → LLM 流式生成 → ActionParser 标签解析 → SoundTagConverter 音效内生化
→ CommandPackager (TTS合成 + 兜底推理) → ProtocolAdapter → WebSocket 输出
```

详见 [ARCHITECTURE.md](ARCHITECTURE.md) 获取完整的架构设计文档。

## Documentation

| Document | Description |
|----------|-------------|
| [PRODUCT_SPEC.md](PRODUCT_SPEC.md) | 产品规格说明 |
| [ARCHITECTURE.md](ARCHITECTURE.md) | 架构设计文档 |
| [INTERFACE_DESIGN.md](INTERFACE_DESIGN.md) | 接口与数据结构设计 |
| [REQUIREMENTS_REFLECTION.md](REQUIREMENTS_REFLECTION.md) | 需求反思报告 |
| [docs/EMOTION_TEST_CASES.md](docs/EMOTION_TEST_CASES.md) | 情感功能测试用例文档 |
| [docs/WINDOWS_DEPLOYMENT_GUIDE.md](docs/WINDOWS_DEPLOYMENT_GUIDE.md) | Windows 本地部署指南 |
| [docs/](docs/) | 完整的 Word 格式文档（含可行性调研报告） |

## License

MIT
