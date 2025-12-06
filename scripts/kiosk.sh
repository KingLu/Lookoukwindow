#!/bin/bash
# Kiosk 模式启动脚本

# 日志文件路径
LOG_FILE="$HOME/.local/share/lookoukwindow/kiosk.log"
mkdir -p "$(dirname "$LOG_FILE")"

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=== Kiosk 脚本启动 ==="

# 设置 DISPLAY 环境变量（如果未设置）
if [ -z "$DISPLAY" ]; then
    # 尝试检测可用的显示
    if [ -e /tmp/.X11-unix/X0 ]; then
        export DISPLAY=:0
        log "设置 DISPLAY=:0"
    else
        # 尝试其他常见的显示
        export DISPLAY=:0.0
        log "设置 DISPLAY=:0.0"
    fi
else
    log "DISPLAY 已设置为: $DISPLAY"
fi

# 等待桌面环境完全启动（树莓派2 可能需要更长时间）
log "等待桌面环境启动..."
sleep 5

# 等待 X 服务器就绪
log "检查 X 服务器..."
for i in {1..30}; do
    if xset q &>/dev/null; then
        log "X 服务器已就绪"
        break
    fi
    if [ $i -eq 30 ]; then
        log "错误: X 服务器未就绪，但继续尝试..."
    else
        sleep 1
    fi
done

# 禁用屏保和电源管理
log "配置屏幕设置..."
xset s off 2>&1 | tee -a "$LOG_FILE"
xset -dpms 2>&1 | tee -a "$LOG_FILE"
xset s noblank 2>&1 | tee -a "$LOG_FILE"

# 启动 Firefox 全屏模式
# 提示：在树莓派上如果没有安装，请运行: sudo apt install firefox-esr

# 优先检测 chromium-browser (树莓派默认)
if command -v chromium-browser &> /dev/null; then
    BROWSER="chromium-browser"
    log "使用浏览器: chromium-browser"
elif command -v chromium &> /dev/null; then
    BROWSER="chromium"
    log "使用浏览器: chromium"
elif command -v firefox &> /dev/null; then
    BROWSER="firefox"
    log "使用浏览器: firefox"
elif command -v firefox-esr &> /dev/null; then
    BROWSER="firefox-esr"
    log "使用浏览器: firefox-esr"
else
    log "错误: 未找到支持的浏览器 (chromium, firefox)"
    log "请安装: sudo apt install chromium-browser 或 sudo apt install firefox"
    exit 1
fi

# 检查浏览器是否存在 (再次确认)
if ! command -v "$BROWSER" &> /dev/null; then
    log "错误: 未找到浏览器 $BROWSER"
    exit 1
fi

# 等待服务启动
log "等待 Lookoukwindow 服务启动..."

check_service() {
    # 尝试使用 curl 或 python 检查服务状态
    if command -v curl &> /dev/null; then
        curl -s -o /dev/null -w "%{http_code}" http://localhost:8000 | grep -q "200"
    else
        python3 -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000').getcode() == 200 else 1)" 2>/dev/null
    fi
}

RETRY_COUNT=0
MAX_RETRIES=60  # 最多等待 2 分钟

until check_service; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        log "错误: 服务启动超时，但继续尝试打开浏览器..."
        break
    fi
    log "服务未就绪，等待 2 秒... (尝试 $RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done

if check_service; then
    log "服务已启动，准备打开浏览器..."
else
    log "警告: 服务可能未完全启动，但继续尝试..."
fi

# 额外等待，确保桌面环境完全稳定（树莓派2 需要）
log "等待桌面环境稳定..."
sleep 3

# 关闭可能已存在的浏览器进程（避免冲突）
log "检查并关闭已存在的浏览器进程..."
pkill -f "firefox" 2>/dev/null || true
pkill -f "chromium" 2>/dev/null || true
sleep 2

# 启动浏览器
log "启动 $BROWSER..."

if [[ "$BROWSER" == *"chromium"* ]]; then
    # Chromium 启动参数
    # 创建用户数据目录（用于持久化禁用翻译设置）
    CHROMIUM_USER_DIR="$HOME/.local/share/lookoukwindow/chromium-kiosk"
    mkdir -p "$CHROMIUM_USER_DIR"
    
    # 创建 Preferences 文件禁用翻译
    PREFS_DIR="$CHROMIUM_USER_DIR/Default"
    mkdir -p "$PREFS_DIR"
    if [ ! -f "$PREFS_DIR/Preferences" ]; then
        cat > "$PREFS_DIR/Preferences" << 'EOF'
{
    "translate": {
        "enabled": false
    },
    "translate_blocked_languages": ["zh-CN", "zh", "en"],
    "browser": {
        "enable_spellchecking": false
    }
}
EOF
        log "已创建 Chromium 首选项文件禁用翻译"
    fi
    
    nohup "$BROWSER" \
        --noerrdialogs \
        --disable-infobars \
        --kiosk \
        --incognito \
        --password-store=basic \
        --autoplay-policy=no-user-gesture-required \
        --check-for-update-interval=31536000 \
        --disable-restore-session-state \
        --disable-translate \
        --disable-extensions \
        --disable-component-extensions-with-background-pages \
        --disable-default-apps \
        --disable-features=Translate,TranslateUI,TranslateScript \
        --lang=zh-CN \
        --accept-lang=zh-CN,zh \
        --user-data-dir="$CHROMIUM_USER_DIR" \
        http://localhost:8000 >> "$LOG_FILE" 2>&1 &
else
    # Firefox 启动参数
    # 创建 Firefox profile 目录（用于持久化设置）
    FIREFOX_PROFILE_DIR="$HOME/.local/share/lookoukwindow/firefox-kiosk"
    mkdir -p "$FIREFOX_PROFILE_DIR"
    
    # 创建 user.js 文件禁用翻译和其他干扰项
    if [ ! -f "$FIREFOX_PROFILE_DIR/user.js" ]; then
        cat > "$FIREFOX_PROFILE_DIR/user.js" << 'EOF'
// 禁用翻译功能
user_pref("browser.translations.enable", false);
user_pref("browser.translations.automaticallyPopup", false);
user_pref("browser.translations.panelShown", false);
// 禁用首次运行向导
user_pref("browser.startup.homepage_override.mstone", "ignore");
user_pref("datareporting.policy.dataSubmissionEnabled", false);
user_pref("toolkit.telemetry.reportingpolicy.firstRun", false);
// 设置语言
user_pref("intl.accept_languages", "zh-CN, zh");
user_pref("intl.locale.requested", "zh-CN");
EOF
        log "已创建 Firefox 首选项文件禁用翻译"
    fi
    
    nohup "$BROWSER" \
        --kiosk \
        --private-window \
        --no-remote \
        --profile "$FIREFOX_PROFILE_DIR" \
        http://localhost:8000 >> "$LOG_FILE" 2>&1 &
fi

BROWSER_PID=$!
log "$BROWSER 已启动，PID: $BROWSER_PID"

# 等待浏览器完全启动
sleep 5

# 检查浏览器是否还在运行
if ps -p $BROWSER_PID > /dev/null 2>&1; then
    log "$BROWSER 进程运行正常"
else
    log "警告: $BROWSER 进程可能已退出，检查日志: $LOG_FILE"
fi

log "=== Kiosk 脚本完成 ==="
