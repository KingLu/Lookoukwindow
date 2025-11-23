#!/bin/bash
# 打包脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
RELEASE_DIR="$PROJECT_DIR/release"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
ARCHIVE_NAME="lookoukwindow_${TIMESTAMP}.tar.gz"

echo "开始打包 Lookoukwindow..."

# 创建 release 目录
if [ ! -d "$RELEASE_DIR" ]; then
    mkdir -p "$RELEASE_DIR"
fi

# 清理旧的构建产物
echo "清理旧文件..."
rm -f "$RELEASE_DIR"/*.tar.gz

# 切换到项目根目录
cd "$PROJECT_DIR"

# 执行打包
echo "正在打包到 $RELEASE_DIR/$ARCHIVE_NAME ..."

# 使用 tar 打包，--exclude 排除不需要的文件
# 注意：--exclude 必须放在 tar 命令的前面或中间，具体取决于 tar 版本，但在 Linux 上通常通用
tar -czf "$RELEASE_DIR/$ARCHIVE_NAME" \
    --exclude='.git' \
    --exclude='.gitignore' \
    --exclude='.vscode' \
    --exclude='.idea' \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.DS_Store' \
    --exclude='release' \
    --exclude='*.log' \
    --exclude='data/albums/*' \
    --exclude='data/thumbnails/*' \
    --exclude='tests' \
    .

echo "----------------------------------------"
echo "✅ 打包完成！"
echo "文件位置: $RELEASE_DIR/$ARCHIVE_NAME"
echo "大小: $(du -h "$RELEASE_DIR/$ARCHIVE_NAME" | cut -f1)"
echo "----------------------------------------"
echo "部署提示："
echo "1. 将此压缩包上传到树莓派"
echo "2. 解压: tar -xzf $ARCHIVE_NAME -C lookoukwindow"
echo "3. 进入目录并运行安装脚本: ./scripts/install.sh"

