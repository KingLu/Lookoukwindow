# Google Photos API 配置指南

## 步骤 1: 创建 Google Cloud 项目

1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 点击项目选择器，创建新项目或选择现有项目
3. 给项目命名（例如：Lookoukwindow）

## 步骤 2: 启用 Photos Library API

1. 在左侧菜单中，点击 "API 和服务" → "库"
2. 搜索 "Photos Library API"
3. 点击进入，然后点击 "启用"

## 步骤 3: 配置 OAuth 同意屏幕

**重要：这是必须的步骤，否则无法授权！**

1. 在左侧菜单中，点击 "API 和服务" → "OAuth 同意屏幕"
2. 选择用户类型：
   - 选择 "外部"（除非你有 Google Workspace）
   - 点击 "创建"
3. 填写应用信息：
   - **应用名称**：Lookoukwindow（或任意名称）
   - **用户支持电子邮件**：选择你的邮箱
   - **开发者联系信息**：填写你的邮箱
   - 点击 "保存并继续"
4. 配置作用域：
   - 点击 "添加或移除作用域"
   - 在 "手动输入作用域" 中输入：`https://www.googleapis.com/auth/photoslibrary.readonly`
   - 点击 "添加到表格"
   - 点击 "更新"
   - 点击 "保存并继续"
5. **添加测试用户（重要！）**：
   - 在 "测试用户" 部分，点击 "添加用户"
   - 输入你的 Google 账号邮箱（例如：`lushize@gmail.com`）
   - 点击 "添加"
   - **重要**：只有添加到测试用户列表的账号才能使用应用
   - 点击 "保存并继续"
6. 完成配置：
   - 查看摘要信息
   - 点击 "返回到信息中心"

## 步骤 4: 创建 OAuth 2.0 客户端 ID（推荐：桌面应用）

1. 在左侧菜单中，点击 "API 和服务" → "凭据"
2. 点击 "创建凭据" → "OAuth 客户端 ID"
3. 创建 OAuth 客户端：
   - **应用类型**：选择 "桌面应用"（Desktop app）
   - **名称**：Lookoukwindow（或任意名称）
   - 点击 "创建"
4. 下载凭据：
   - 点击下载按钮（⬇️），下载 JSON 文件
   - 文件通常命名为类似 `client_secret_xxxxx.json`
5. 如果之前曾使用“Web 应用”类型，请删除旧 token 并改用桌面应用凭据（见下方“清理旧授权”）

## 步骤 5: 上传 client_secrets.json

1. 将下载的 JSON 文件重命名为 `client_secrets.json`
2. 上传到服务器的以下目录：
   ```
   ~/.local/share/lookoukwindow/tokens/client_secrets.json
   ```
   
   或者使用 scp 命令：
   ```bash
   scp client_secrets.json user@your-server:~/.local/share/lookoukwindow/tokens/
   ```

3. 确保文件权限正确：
   ```bash
   chmod 600 ~/.local/share/lookoukwindow/tokens/client_secrets.json
   ```

## 步骤 6: 授权应用

1. 在设置页面点击 "本机授权（推荐）"
2. 系统会自动打开浏览器，显示 Google 授权页面
3. 选择你的 Google 账号
4. 点击 "允许" 授予权限
5. 授权成功后会自动返回应用

如果本机授权不可用，可使用“网页授权（备用）”，但某些环境下可能在 consentsummary 页面卡住，建议优先使用本机授权。

## 步骤 7: 选择相册

1. 授权成功后，应用会自动获取你的相册列表
2. 在设置页面选择要展示的相册
3. 点击 "同步照片" 开始下载照片

## 故障排除

### 错误：未找到 client_secrets.json

- 确认文件路径正确：`~/.local/share/lookoukwindow/tokens/client_secrets.json`
- 确认文件名正确（必须是 `client_secrets.json`）
- 检查文件权限

### 错误：OAuth 客户端类型不正确

- 确保创建的是 "桌面应用" 类型的 OAuth 客户端
- 不要使用 "Web 应用" 类型

### 错误：API 未启用

- 确认已在 Google Cloud Console 中启用 "Photos Library API"
- 等待几分钟让更改生效

### 错误 403: access_denied - 应用尚未完成验证流程

**原因**：OAuth 应用处于测试状态，你的 Google 账号未添加到测试用户列表

**解决方法**：
1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 进入 "API 和服务" → "OAuth 同意屏幕"
3. 滚动到 "测试用户" 部分
4. 点击 "添加用户"
5. 输入你的 Google 账号邮箱（例如：`lushize@gmail.com`）
6. 点击 "添加"
7. 等待几分钟让更改生效
8. 重新尝试授权

**注意**：
- 只有添加到测试用户列表的账号才能使用应用
- 最多可以添加 100 个测试用户
- 如果需要更多人使用，需要发布应用（需要完成 Google 验证流程）

### 清理旧授权

如果切换为“桌面应用”凭据后仍无法授权，请清理旧 token 并重新授权：
```bash
rm ~/.local/share/lookoukwindow/tokens/google_photos_token.json
```
然后回到设置页面，点击“本机授权（推荐）”重新授权。
### 授权后无法获取相册

- 检查网络连接
- 查看应用日志了解详细错误
- 确认 OAuth 同意屏幕已配置测试用户
- 确认已启用 Photos Library API

## 注意事项

- `client_secrets.json` 包含敏感信息，请妥善保管
- 不要将 `client_secrets.json` 提交到代码仓库
- OAuth 客户端有配额限制，大量请求可能需要申请提高配额
