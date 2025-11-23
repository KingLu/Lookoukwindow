#!/bin/bash
# Kiosk 模式启动脚本

# 禁用屏保和电源管理
xset s off
xset -dpms
xset s noblank

# 启动 Firefox 全屏模式
# 提示：在树莓派上如果没有安装，请运行: sudo apt install firefox-esr

# 优先检测 firefox-esr (树莓派常用)，否则使用 firefox
BROWSER="firefox"
if command -v firefox-esr &> /dev/null; then
    BROWSER="firefox-esr"
fi

$BROWSER \
    --kiosk \
    --private-window \
    http://localhost:8000
