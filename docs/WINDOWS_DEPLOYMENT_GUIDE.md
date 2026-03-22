# Emotions-System Windows 部署指南

**文档版本**：v1.0  
**更新日期**：2026-03-22  

本文档专门针对在 Windows 操作系统（如 Windows 10/11 笔记本电脑）上部署和运行 Emotions-System 提供详细指导。

---

## 1. 环境准备

在开始部署之前，请确保您的 Windows 电脑已安装以下基础环境：

### 1.1 安装 Python
1. 访问 [Python 官方网站](https://www.python.org/downloads/windows/) 下载 Python 3.11.x 或 3.12.x 的 Windows 安装程序（推荐 64-bit）。
2. 运行安装程序时，**务必勾选 "Add Python to PATH"**（将 Python 添加到环境变量）。
3. 安装完成后，打开命令提示符（CMD）或 PowerShell，输入以下命令验证：
   ```cmd
   python --version
   ```
   *应输出 `Python 3.11.x` 或更高版本。*

### 1.2 安装 Git
1. 访问 [Git for Windows](https://gitforwindows.org/) 下载并安装 Git。
2. 验证安装：
   ```cmd
   git --version
   ```

---

## 2. 获取代码与配置

### 2.1 克隆代码仓库
打开命令提示符（CMD）或 PowerShell，进入您希望存放项目的目录，执行：
```cmd
git clone https://github.com/yangli0403/Emotions-System.git
cd Emotions-System
```

### 2.2 切换到 Windows 适配分支（可选）
如果您需要使用专门为 Windows 优化的启动脚本，请切换到 `windows-deploy` 分支：
```cmd
git checkout windows-deploy
```

### 2.3 配置环境变量
项目需要 API Key 才能运行。在 Windows 下配置环境变量文件：
1. 在项目根目录下，找到 `.env.example` 文件。
2. 复制该文件并重命名为 `.env`。
   *在命令提示符中可以使用：`copy .env.example .env`*
3. 使用记事本或 VS Code 打开 `.env` 文件，填入您的 API Key：
   - `LLM_API_KEY`：火山引擎或 OpenAI 的 API Key
   - `DASHSCOPE_API_KEY`：阿里百炼的 API Key

---

## 3. 安装依赖与启动

为了避免污染全局 Python 环境，强烈建议使用虚拟环境（Virtual Environment）。

### 3.1 方式一：使用一键启动脚本（推荐）
我们在 `scripts` 目录下提供了 Windows 专用的批处理脚本，它会自动创建虚拟环境、安装依赖并启动服务。

双击运行或在命令行中执行：
```cmd
scripts\start_windows.bat
```

### 3.2 方式二：手动分步执行
如果您希望手动控制每一步，请按以下顺序执行：

**1. 创建并激活虚拟环境**
```cmd
python -m venv venv
venv\Scripts\activate
```
*激活后，命令行提示符前会出现 `(venv)` 字样。*

**2. 安装项目依赖**
```cmd
pip install -e ".[dev]"
```

**3. 创建必要的数据目录**
```cmd
mkdir data\uploads
mkdir data\output
```

**4. 启动服务**
```cmd
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## 4. 验证部署

服务启动后，控制台会输出类似 `Application startup complete` 的信息。

1. 打开浏览器，访问：[http://localhost:8000](http://localhost:8000)
2. 您将看到 Emotions-System 的 Web 测试面板。
3. 在右侧的 "TTS 独立测试" 区域，输入一段文本并点击 "合成音频"，如果能听到声音，说明部署完全成功！

---

## 5. 常见问题排查 (FAQ)

### Q1: 运行脚本时提示 "python 不是内部或外部命令"
**原因**：安装 Python 时没有勾选 "Add Python to PATH"。
**解决**：重新运行 Python 安装程序，选择 "Modify"（修改），勾选 "Add Python to environment variables"，然后一路 Next。

### Q2: 提示 "dashscope SDK 未安装" 或其他模块找不到
**原因**：依赖安装失败或未在虚拟环境中运行。
**解决**：确保命令行前有 `(venv)` 标志，然后重新运行 `pip install -e .`。

### Q3: WebSocket 连接失败或断开
**原因**：Windows 上的 `asyncio` 默认使用 `ProactorEventLoop`，在某些 Python 版本下可能与特定库存在兼容性问题。
**解决**：我们在 `main.py` 中已添加了针对 Windows 的事件循环策略兼容代码。如果仍有问题，请检查防火墙是否拦截了 8000 端口。

### Q4: 声音复刻上传音频失败
**原因**：Windows 路径分隔符（`\`）与 Linux（`/`）不同。
**解决**：项目核心代码已使用 `pathlib` 处理路径，天然跨平台。如果报错，请检查 `data/uploads` 目录是否具有写入权限。
