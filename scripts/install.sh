#!/bin/bash
# 安装脚本

set -e

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 获取项目根目录的绝对路径
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "脚本目录: $SCRIPT_DIR"
echo "项目目录: $PROJECT_DIR"
echo "开始安装 Lookoukwindow..."

# 检查Python版本
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 python3"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Python 版本: $PYTHON_VERSION"

# 检查虚拟环境是否有效
VENV_DIR="$PROJECT_DIR/venv"
ACTIVATE_SCRIPT="$VENV_DIR/bin/activate"

if [ -d "$VENV_DIR" ] && [ ! -f "$ACTIVATE_SCRIPT" ]; then
    echo "警告: 发现损坏的虚拟环境，正在清理..."
    rm -rf "$VENV_DIR"
fi

# 创建虚拟环境
if [ ! -d "$VENV_DIR" ]; then
    echo "创建虚拟环境..."
    python3 -m venv "$VENV_DIR"
    
    if [ ! -f "$ACTIVATE_SCRIPT" ]; then
        echo "错误: 虚拟环境创建失败，找不到 $ACTIVATE_SCRIPT"
        # 尝试安装 venv 模块（某些系统可能需要）
        echo "尝试安装 python3-venv..."
        sudo apt-get update && sudo apt-get install -y python3-venv
        python3 -m venv "$VENV_DIR"
        
        if [ ! -f "$ACTIVATE_SCRIPT" ]; then
             echo "致命错误: 无法创建虚拟环境。"
             exit 1
        fi
    fi
fi

# 激活虚拟环境
echo "正在激活虚拟环境: $ACTIVATE_SCRIPT"
source "$ACTIVATE_SCRIPT"

# 检查 pip
if ! command -v pip &> /dev/null; then
    echo "错误: 虚拟环境中未找到 pip"
    exit 1
fi

# 升级pip (增加超时设置，防止网络慢卡死)
echo "升级 pip..."
pip install --upgrade pip --timeout 100 --retries 3

# 安装依赖
echo "安装依赖..."
if [ -f "$PROJECT_DIR/requirements.txt" ]; then
    pip install -r "$PROJECT_DIR/requirements.txt" --timeout 100 --retries 3
else
    echo "警告: 未找到 requirements.txt"
fi

echo "安装完成！"
echo ""
echo "下一步："
echo "1. 激活虚拟环境: source $VENV_DIR/bin/activate"
echo "2. 运行应用: python $PROJECT_DIR/run.py"
