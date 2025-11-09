#!/bin/bash
# Kiosk 模式启动脚本

# 禁用屏保和电源管理
xset s off
xset -dpms
xset s noblank

# 启动 Chromium 全屏模式
chromium-browser \
    --kiosk \
    --noerrdialogs \
    --disable-infobars \
    --disable-session-crashed-bubble \
    --disable-restore-session-state \
    --autoplay-policy=no-user-gesture-required \
    --check-for-update-interval=31536000 \
    http://localhost:8000
