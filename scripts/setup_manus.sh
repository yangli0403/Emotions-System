#!/bin/bash
# Emotions-System — Manus 环境一键配置脚本
# 用法：bash scripts/setup_manus.sh
#
# 本脚本专为 Manus 沙箱环境设计，执行以下操作：
#   1. 安装 Python 依赖（含 Ark SDK、DashScope SDK）
#   2. 检查 .env 配置文件
#   3. 创建必要的数据目录
#   4. 运行测试验证环境
#   5. 启动服务

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "=========================================="
echo "  Emotions-System — Manus 环境配置"
echo "=========================================="

# Step 1: 安装依赖
echo ""
echo "[Step 1/5] 安装 Python 依赖..."
sudo pip3 install -e ".[dev]" --quiet 2>&1 | tail -5
echo "[OK] 依赖安装完成"

# Step 2: 检查 .env 文件
echo ""
echo "[Step 2/5] 检查环境配置..."
if [ ! -f ".env" ]; then
    echo "[WARN] 未找到 .env 文件，从模板创建..."
    cp .env.example .env
    echo "[INFO] 已创建 .env 文件，请编辑填入实际 API Key："
    echo "       - LLM_API_KEY: 字节火山引擎 Ark API Key"
    echo "       - LLM_MODEL: Ark Endpoint ID (如 ep-xxxxxxx)"
    echo "       - DASHSCOPE_API_KEY: 阿里百炼 DashScope API Key"
    echo ""
    echo "[INFO] 编辑命令：nano .env"
    exit 0
else
    echo "[OK] .env 文件已存在"
    # 验证关键配置
    source .env 2>/dev/null || true
    if [ -z "$LLM_API_KEY" ] || [ "$LLM_API_KEY" = "your_api_key_here" ]; then
        echo "[WARN] LLM_API_KEY 未配置，请编辑 .env 文件"
    fi
    if [ -z "$DASHSCOPE_API_KEY" ] || [ "$DASHSCOPE_API_KEY" = "your_dashscope_api_key_here" ]; then
        echo "[WARN] DASHSCOPE_API_KEY 未配置，请编辑 .env 文件"
    fi
fi

# Step 3: 创建数据目录
echo ""
echo "[Step 3/5] 创建数据目录..."
mkdir -p data/uploads data/output
echo "[OK] 数据目录就绪"

# Step 4: 运行测试
echo ""
echo "[Step 4/5] 运行单元测试..."
python3 -m pytest tests/ --cov=core --cov=services --cov=adapters --cov=config -q 2>&1 | tail -5
echo "[OK] 测试完成"

# Step 5: 启动服务
echo ""
echo "[Step 5/5] 启动服务..."
echo "=========================================="
echo "  访问地址: http://localhost:8000"
echo "  健康检查: http://localhost:8000/health"
echo "  WebSocket: ws://localhost:8000/ws"
echo "=========================================="
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --log-level info
