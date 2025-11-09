#!/bin/bash
# 安装脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "开始安装 Lookoukwindow..."

# 检查Python版本
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 python3"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Python 版本: $PYTHON_VERSION"

# 创建虚拟环境
if [ ! -d "$PROJECT_DIR/venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv "$PROJECT_DIR/venv"
fi

# 激活虚拟环境
source "$PROJECT_DIR/venv/bin/activate"

# 升级pip
echo "升级 pip..."
pip install --upgrade pip

# 安装依赖
echo "安装依赖..."
pip install -r "$PROJECT_DIR/requirements.txt"

echo "安装完成！"
echo ""
echo "下一步："
echo "1. 激活虚拟环境: source $PROJECT_DIR/venv/bin/activate"
echo "2. 运行应用: python $PROJECT_DIR/run.py"
