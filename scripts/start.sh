#!/bin/bash
# Emotions-System 快速启动脚本
# 用法：bash scripts/start.sh
#
# 前提条件：
#   1. 已创建 .env 文件（cp .env.example .env 并填入 API Key）
#   2. Python 3.11+

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "=========================================="
echo "  Emotions-System 启动脚本"
echo "=========================================="

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo "[ERROR] 未找到 .env 文件！"
    echo "请先执行：cp .env.example .env"
    echo "然后编辑 .env 填入实际的 API Key"
    exit 1
fi

# 检查 Python 版本
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "[INFO] Python 版本: $PYTHON_VERSION"

# 安装依赖
echo "[INFO] 安装 Python 依赖..."
pip3 install -e ".[dev]" --quiet 2>&1 | tail -3

# 创建数据目录
mkdir -p data/uploads data/output

# 启动服务
echo "[INFO] 启动 Emotions-System 服务..."
echo "[INFO] 访问地址: http://localhost:8000"
echo "[INFO] 健康检查: http://localhost:8000/health"
echo "[INFO] WebSocket: ws://localhost:8000/ws"
echo "=========================================="

python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --log-level info
