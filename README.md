# Lookoukwindow

NASA 太空直播和 Google 相册展示应用，专为树莓派设计。

## 功能特性

- 🚀 **NASA 太空直播**: 观看 NASA TV、ISS Live、NASA Live 等 YouTube 直播
- 📸 **Google 相册集成**: 关联并展示你的 Google 相册
- 🎨 **轮播展示**: 自动轮播照片，支持手动翻页
- 🔒 **安全访问**: 简单的密码保护，支持局域网访问
- 💾 **离线支持**: 照片缓存到本地，离线也可查看
- 🖥️ **Kiosk 模式**: 开机全屏自动展示

## 系统要求

- 树莓派（推荐 Raspberry Pi 4）
- Ubuntu 20.04+ 或 Raspberry Pi OS
- Python 3.8+
- 至少 2GB 可用存储空间（用于照片缓存）

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

### 3. 配置 Google Photos API

**详细配置步骤请参考：[Google Photos API 配置指南](docs/GOOGLE_PHOTOS_SETUP.md)**

简要步骤：
1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建新项目或选择现有项目
3. 启用 "Photos Library API"
4. **配置 OAuth 同意屏幕**（重要！）：
   - 添加作用域：`https://www.googleapis.com/auth/photoslibrary.readonly`
   - **在"测试用户"中添加你的 Google 账号邮箱**（必须！否则会报 403 错误）
5. 创建 OAuth 2.0 客户端 ID（应用类型：**桌面应用**）
6. 下载客户端密钥 JSON 文件
7. 将文件重命名为 `client_secrets.json` 并放到 `~/.local/share/lookoukwindow/tokens/` 目录

**重要提示：**
- 文件路径：`~/.local/share/lookoukwindow/tokens/client_secrets.json`
- 必须使用 "桌面应用" 类型的 OAuth 客户端
- **必须将你的 Google 账号添加到 OAuth 同意屏幕的"测试用户"列表**，否则会报 403 错误
- 首次使用需要配置 OAuth 同意屏幕

### 4. 首次运行

```bash
source venv/bin/activate
python run.py
```

访问 `http://localhost:8000` 或 `http://<树莓派IP>:8000`

首次访问会要求设置登录密码。

## 配置说明

配置文件位置: `~/.local/share/lookoukwindow/config.yaml`

主要配置项：

- `youtube`: YouTube 直播配置
  - `presets`: 预设频道列表
  - `custom_channels`: 自定义频道
  - `default_channel`: 默认频道
- `google`: Google Photos 配置
  - `album_id`: 选择的相册ID
  - `sync_interval_minutes`: 同步间隔（分钟）
  - `max_cache_gb`: 最大缓存大小（GB）
- `ui`: UI 配置
  - `layout`: 布局（side-by-side/stacked/picture-in-picture）
  - `slideshow_interval_seconds`: 轮播间隔（秒）
  - `show_metadata`: 显示照片元数据
- `display`: 显示配置
  - `kiosk`: 是否启用 Kiosk 模式
  - `screen_rotation`: 屏幕旋转（normal/left/right/inverted）
  - `scale`: 缩放比例

## 使用说明

### 设置密码

首次访问会自动跳转到设置页面，设置登录密码。

### 重置密码

如果忘记密码或需要重置密码，可以使用重置密码脚本：

```bash
source venv/bin/activate
python scripts/reset_password.py
```

脚本会引导你：
1. 确认是否要重置密码
2. 输入新密码（至少6位，不超过72字节）
3. 确认新密码

**注意：** 重置密码会清除旧的密码hash，即使你忘记了旧密码也可以重置。

### 选择相册

1. 访问设置页面 (`/settings`)
2. 点击 "授权 Google Photos"
3. 在浏览器中完成授权
4. 选择要展示的相册
5. 点击 "同步照片" 开始下载

### 添加 YouTube 频道

1. 访问设置页面
2. 在 "YouTube 频道" 部分点击 "添加频道"
3. 输入频道名称和 YouTube URL

### Kiosk 模式

#### 方式1: 使用 systemd 服务（推荐）

```bash
# 复制服务文件
sudo cp lookoukwindow.service /etc/systemd/system/

# 修改服务文件中的路径（如果需要）
sudo nano /etc/systemd/system/lookoukwindow.service

# 启用并启动服务
sudo systemctl enable lookoukwindow.service
sudo systemctl start lookoukwindow.service

# 查看状态
sudo systemctl status lookoukwindow.service
```

#### 方式2: 使用 Kiosk 脚本

编辑 `~/.config/autostart/kiosk.desktop`:

```ini
[Desktop Entry]
Type=Application
Name=Lookoukwindow Kiosk
Exec=/bigdata/codeCangku/算畿/Lookoukwindow/scripts/kiosk.sh
```

### 局域网访问

应用默认监听 `0.0.0.0:8000`，局域网内其他设备可通过 `http://<树莓派IP>:8000` 访问。

**安全提示**: 应用仅设计用于局域网环境，请勿暴露到公网。

## API 文档

应用启动后，访问 `/docs` 查看自动生成的 API 文档。

## 故障排除

### Google Photos 授权失败

- 确保 `client_secrets.json` 文件在正确位置
- 检查 Google Cloud Console 中的 API 是否已启用
- 确认 OAuth 客户端类型为 "桌面应用"

### 照片同步失败

- 检查网络连接
- 确认已选择相册
- 查看控制台日志

### YouTube 视频无法播放

- 检查网络连接
- 确认 YouTube 可访问
- 尝试切换其他频道

## 开发

### 项目结构

```
Lookoukwindow/
├── app/
│   ├── api/          # API 路由
│   ├── core/         # 核心模块（配置、认证）
│   ├── services/     # 业务服务
│   ├── templates/    # HTML 模板
│   └── main.py       # FastAPI 应用入口
├── scripts/          # 脚本文件
├── requirements.txt  # Python 依赖
└── run.py           # 启动脚本
```

### 运行开发服务器

```bash
source venv/bin/activate
python run.py
```

## 许可证

GPL-3.0

## 贡献

欢迎提交 Issue 和 Pull Request！

## 更新日志

### v1.0.0

- 初始版本
- 支持 NASA YouTube 直播
- 支持 Google Photos 相册展示
- 支持轮播和手动翻页
- 支持 Kiosk 模式
