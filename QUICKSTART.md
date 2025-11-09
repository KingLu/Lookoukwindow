# 快速启动指南

## 1. 安装依赖

```bash
cd /bigdata/codeCangku/算畿/Lookoukwindow
./scripts/install.sh
```

或手动安装：

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 2. 配置 Google Photos API

1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建新项目或选择现有项目
3. 启用 "Photos Library API"
4. 创建 OAuth 2.0 客户端 ID（应用类型：桌面应用）
5. 下载客户端密钥 JSON 文件
6. 将文件重命名为 `client_secrets.json` 并放到：
   ```
   ~/.local/share/lookoukwindow/tokens/client_secrets.json
   ```

## 3. 启动应用

```bash
source venv/bin/activate
python run.py
```

应用将在 `http://localhost:8000` 启动。

## 4. 首次设置

1. 访问 `http://localhost:8000` 或 `http://<树莓派IP>:8000`
2. 设置登录密码
3. 登录后访问设置页面
4. 授权 Google Photos
5. 选择要展示的相册
6. 点击"同步照片"开始下载

## 5. Kiosk 模式（可选）

### 使用 systemd 服务

```bash
# 修改服务文件中的路径（如果需要）
sudo nano lookoukwindow.service

# 复制服务文件
sudo cp lookoukwindow.service /etc/systemd/system/

# 启用并启动
sudo systemctl enable lookoukwindow.service
sudo systemctl start lookoukwindow.service
```

### 使用 Kiosk 脚本

编辑 `~/.config/autostart/kiosk.desktop`:

```ini
[Desktop Entry]
Type=Application
Name=Lookoukwindow Kiosk
Exec=/bigdata/codeCangku/算畿/Lookoukwindow/scripts/kiosk.sh
```

## 6. 访问应用

- 本地: `http://localhost:8000`
- 局域网: `http://<树莓派IP>:8000`

## 故障排除

### 应用无法启动

- 检查 Python 版本: `python3 --version` (需要 3.8+)
- 检查依赖是否安装: `pip list`
- 查看错误日志

### Google Photos 授权失败

- 确认 `client_secrets.json` 文件在正确位置
- 检查 Google Cloud Console 中的 API 是否已启用
- 确认 OAuth 客户端类型为"桌面应用"

### 照片无法同步

- 检查网络连接
- 确认已选择相册
- 查看控制台日志

### YouTube 视频无法播放

- 检查网络连接
- 确认 YouTube 可访问
- 尝试切换其他频道
