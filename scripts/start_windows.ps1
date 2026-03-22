# Emotions-System Windows PowerShell 启动脚本
# 用法：在 PowerShell 中运行 .\scripts\start_windows.ps1
# 如果提示执行策略限制，请先运行：Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Emotions-System Windows 启动脚本 (PS)" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[INFO] $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] 未找到 Python！请先安装 Python 3.11+ 并确保已添加到 PATH。" -ForegroundColor Red
    Write-Host "下载地址: https://www.python.org/downloads/windows/" -ForegroundColor Yellow
    Read-Host "按回车键退出"
    exit 1
}

# 切换到项目根目录
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Split-Path -Parent $scriptDir
Set-Location $projectDir
Write-Host "[INFO] 项目目录: $projectDir" -ForegroundColor Green

# 检查 .env 文件
if (-not (Test-Path ".env")) {
    Write-Host "[WARN] 未找到 .env 文件！" -ForegroundColor Yellow
    if (Test-Path ".env.example") {
        Write-Host "[INFO] 正在从 .env.example 创建 .env ..." -ForegroundColor Green
        Copy-Item ".env.example" ".env"
        Write-Host "[INFO] 已创建 .env 文件，请编辑该文件填入您的 API Key，然后重新运行此脚本。" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "需要填写的关键配置:" -ForegroundColor Yellow
        Write-Host "  - LLM_API_KEY: 火山引擎或 OpenAI 的 API Key" -ForegroundColor Yellow
        Write-Host "  - LLM_MODEL: 模型名称或 Endpoint ID" -ForegroundColor Yellow
        Write-Host "  - DASHSCOPE_API_KEY: 阿里百炼 DashScope API Key" -ForegroundColor Yellow
        Write-Host ""
        notepad .env
        Read-Host "编辑完成后按回车键继续"
    } else {
        Write-Host "[ERROR] 未找到 .env.example 模板文件！" -ForegroundColor Red
        Read-Host "按回车键退出"
        exit 1
    }
}

# 创建虚拟环境
if (-not (Test-Path "venv")) {
    Write-Host "[INFO] 创建 Python 虚拟环境..." -ForegroundColor Green
    python -m venv venv
    Write-Host "[INFO] 虚拟环境创建成功。" -ForegroundColor Green
}

# 激活虚拟环境
Write-Host "[INFO] 激活虚拟环境..." -ForegroundColor Green
& .\venv\Scripts\Activate.ps1

# 安装依赖
Write-Host "[INFO] 安装 Python 依赖（首次运行可能需要几分钟）..." -ForegroundColor Green
pip install -e ".[dev]" --quiet 2>&1 | Out-Null

# 创建数据目录
New-Item -ItemType Directory -Force -Path "data\uploads" | Out-Null
New-Item -ItemType Directory -Force -Path "data\output" | Out-Null

# 启动服务
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "[INFO] 启动 Emotions-System 服务..." -ForegroundColor Green
Write-Host "[INFO] 访问地址: http://localhost:8000" -ForegroundColor Green
Write-Host "[INFO] 健康检查: http://localhost:8000/health" -ForegroundColor Green
Write-Host "[INFO] WebSocket: ws://localhost:8000/ws" -ForegroundColor Green
Write-Host "[INFO] 按 Ctrl+C 停止服务" -ForegroundColor Yellow
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

python -m uvicorn main:app --host 0.0.0.0 --port 8000 --log-level info
