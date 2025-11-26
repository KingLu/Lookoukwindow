# Lookoukwindow

NASA 太空直播和本地相册展示应用，专为树莓派设计。

## 功能特性

- 🚀 **NASA 太空直播**: 观看 NASA TV、ISS Live、NASA Live 等 YouTube 直播
- 🖼️ **本地相册管理**: 
  - 创建/管理多个本地相册
  - 批量上传照片（支持拖拽）
  - 自由切换要轮播的相册
  - 完全离线运行，无需 Google API
- 🎨 **轮播展示**: 自动轮播照片，支持手动翻页
- 🔒 **安全访问**: 简单的密码保护，支持局域网访问
- 🖥️ **Kiosk 模式**: 开机全屏自动展示

## 系统要求

- 树莓派（推荐 Raspberry Pi 4）
- Ubuntu 20.04+ 或 Raspberry Pi OS
- Python 3.8+
- 至少 2GB 可用存储空间（用于存储照片）

## 安装步骤

### 1. 克隆项目

```bash
cd /bigdata/codeCangku/算畿/Lookoukwindow
```

### 2. 运行安装脚本

```bash
./scripts/install.sh
```

或者手动安装：

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 首次运行

```bash
source venv/bin/activate
python run.py
```

访问 `http://localhost:8000` 或 `http://<树莓派IP>:8000`

首次访问会要求设置登录密码（默认密码：`Spacewin`）。

## 配置说明

配置文件位置: `~/.local/share/lookoukwindow/config.yaml`

主要配置项：

- `youtube`: YouTube 直播配置
  - `presets`: 预设频道列表
  - `custom_channels`: 自定义频道
  - `default_channel`: 默认频道
- `albums`: 相册配置
  - `active_albums`: 启用的相册ID列表
- `ui`: UI 配置
  - `layout`: 布局（side-by-side/stacked/picture-in-picture）
  - `slideshow_interval_seconds`: 轮播间隔（秒）
  - `show_metadata`: 显示照片元数据
- `display`: 显示配置
  - `kiosk`: 是否启用 Kiosk 模式
  - `screen_rotation`: 屏幕旋转（normal/left/right/inverted）

## 使用说明

### 设置密码

首次访问会自动跳转到设置页面，设置登录密码（默认密码：`Spacewin`）。

### 重置密码

如果忘记密码或需要重置密码，可以使用重置密码脚本：

```bash
source venv/bin/activate
python scripts/reset_password.py
```

### 相册管理

1. 访问设置页面 (`/settings`)
2. 在“本地相册管理”区域，点击“新建相册”
3. 创建后点击相册封面或“管理照片”
4. 拖拽照片到上传区域，或点击上传
5. 开启相册的开关（Toggle）以加入轮播列表

### 添加 YouTube 频道

1. 访问设置页面
2. 在 "YouTube 频道" 部分点击 "添加频道"
3. 输入频道名称和 YouTube URL

### Kiosk 模式

Kiosk 模式可以让树莓派开机后自动全屏显示应用，适合作为展示屏使用。

#### 步骤1: 配置 systemd 服务（后台服务）

```bash
# 复制服务文件
sudo cp lookoukwindow.service /etc/systemd/system/

# 修改服务文件中的路径和用户（根据实际情况）
sudo nano /etc/systemd/system/lookoukwindow.service

# 启用并启动服务
sudo systemctl daemon-reload
sudo systemctl enable lookoukwindow.service
sudo systemctl start lookoukwindow.service

# 查看状态
sudo systemctl status lookoukwindow.service
```

#### 步骤2: 配置桌面自启动（浏览器）

```bash
# 1. 创建自启动目录
mkdir -p ~/.config/autostart

# 2. 创建桌面启动文件（根据实际路径修改）
cat > ~/.config/autostart/lookoukwindow-kiosk.desktop << EOF
[Desktop Entry]
Type=Application
Name=Lookoukwindow Kiosk
Comment=Start Lookoukwindow in Kiosk mode
Exec=/var/www/loooutwindow/scripts/kiosk.sh
X-GNOME-Autostart-enabled=true
EOF

# 3. 赋予脚本执行权限
chmod +x /var/www/loooutwindow/scripts/kiosk.sh
```

#### 步骤3: 重启测试

```bash
sudo reboot
```

重启后，系统会自动：
1. 启动后台服务（systemd）
2. 进入桌面后自动打开浏览器全屏显示

#### 故障排除

**问题1: Firefox 进程存在但屏幕没有显示**

- 检查日志文件：`cat ~/.local/share/lookoukwindow/kiosk.log`
- 检查 DISPLAY 环境变量：`echo $DISPLAY`（应该是 `:0` 或 `:0.0`）
- 检查 X 服务器：`xset q`（应该能正常执行）
- 手动测试：`firefox-esr --kiosk http://localhost:8000`

**问题2: 树莓派2 资源不足，启动慢**

- 脚本已优化，会自动等待服务启动
- 如果还是慢，可以增加等待时间（编辑 `kiosk.sh` 中的 `sleep` 时间）
- 考虑使用更轻量的浏览器（如 Chromium）或优化系统

**问题3: 服务未启动**

```bash
# 检查服务状态
sudo systemctl status lookoukwindow.service

# 查看服务日志
sudo journalctl -u lookoukwindow.service -f

# 手动启动测试
cd /var/www/loooutwindow
source venv/bin/activate
python run.py
```

**问题4: 浏览器未安装**

```bash
# 安装 Firefox ESR（推荐）
sudo apt update
sudo apt install firefox-esr

# 或安装 Chromium（备选）
sudo apt install chromium-browser
```

## 开发

### 项目结构

```
Lookoukwindow/
├── app/
│   ├── api/          # API 路由 (albums, youtube, settings, auth)
│   ├── core/         # 核心模块（配置、认证）
│   ├── services/     # 业务服务 (album_service, youtube_service)
│   ├── templates/    # HTML 模板
│   └── main.py       # FastAPI 应用入口
├── scripts/          # 脚本文件
├── requirements.txt  # Python 依赖
└── run.py           # 启动脚本
```

## 许可证

GPL-3.0
