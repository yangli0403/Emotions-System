@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

echo ==========================================
echo   Emotions-System Windows 启动脚本
echo ==========================================
echo.

:: 检查 Python 版本
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] 未找到 Python！请先安装 Python 3.11+ 并确保已添加到 PATH。
    echo 下载地址: https://www.python.org/downloads/windows/
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYTHON_VERSION=%%v
echo [INFO] Python 版本: %PYTHON_VERSION%

:: 切换到项目根目录
cd /d "%~dp0\.."
echo [INFO] 项目目录: %cd%

:: 检查 .env 文件
if not exist ".env" (
    echo [WARN] 未找到 .env 文件！
    if exist ".env.example" (
        echo [INFO] 正在从 .env.example 创建 .env ...
        copy .env.example .env >nul
        echo [INFO] 已创建 .env 文件，请编辑该文件填入您的 API Key，然后重新运行此脚本。
        echo.
        echo 需要填写的关键配置:
        echo   - LLM_API_KEY: 火山引擎或 OpenAI 的 API Key
        echo   - LLM_MODEL: 模型名称或 Endpoint ID
        echo   - DASHSCOPE_API_KEY: 阿里百炼 DashScope API Key
        echo.
        notepad .env
        pause
        exit /b 0
    ) else (
        echo [ERROR] 未找到 .env.example 模板文件！
        pause
        exit /b 1
    )
)

:: 创建虚拟环境（如果不存在）
if not exist "venv" (
    echo [INFO] 创建 Python 虚拟环境...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] 虚拟环境创建失败！
        pause
        exit /b 1
    )
    echo [INFO] 虚拟环境创建成功。
)

:: 激活虚拟环境
echo [INFO] 激活虚拟环境...
call venv\Scripts\activate.bat

:: 安装依赖
echo [INFO] 安装 Python 依赖（首次运行可能需要几分钟）...
pip install -e ".[dev]" --quiet 2>&1
if %errorlevel% neq 0 (
    echo [WARN] 依赖安装可能存在问题，尝试继续启动...
)

:: 创建数据目录
if not exist "data\uploads" mkdir data\uploads
if not exist "data\output" mkdir data\output

:: 启动服务
echo.
echo ==========================================
echo [INFO] 启动 Emotions-System 服务...
echo [INFO] 访问地址: http://localhost:8000
echo [INFO] 健康检查: http://localhost:8000/health
echo [INFO] WebSocket: ws://localhost:8000/ws
echo [INFO] 按 Ctrl+C 停止服务
echo ==========================================
echo.

python -m uvicorn main:app --host 0.0.0.0 --port 8000 --log-level info

:: 服务停止后
echo.
echo [INFO] 服务已停止。
pause
