# Lookoukwindow

NASA 太空直播、本地相册展示及金融信息看板应用，专为树莓派设计。

## 功能特性

- 🚀 **NASA 太空直播**: 观看 NASA TV、ISS Live、NASA Live 等 YouTube 直播，支持 16:9 完美适配。
- 📈 **金融信息看板**:
  - **全球指数**: 实时显示上证、纳斯达克、恒生、BTC 等主要市场指数。
  - **个股行情**: 轮播自选股（如 AAPL, TSLA），支持实时报价和分时走势图。
- 📅 **智能生活信息**:
  - **超级日历**: 大屏显示时间、公历日期、农历（含干支/生肖）。
  - **实时天气**: 集成 Open-Meteo，显示温度、天气状况、湿度等信息。
- 🖼️ **本地相册管理**: 
  - 创建/管理多个本地相册
  - 批量上传照片（支持拖拽）
  - 自由切换要轮播的相册
- 🔒 **安全访问**: 简单的密码保护，支持局域网访问。
- 🖥️ **Kiosk 模式**: 开机全屏自动展示，界面针对远距离观看优化。

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

可以在网页端 `/settings` 页面进行可视化配置。

主要配置项：

- `youtube`: YouTube 直播配置
- `albums`: 相册配置
- `finance`: 金融数据配置 **(v0.3 新增)**
  - `indices`: 显示的指数列表（如 `^IXIC` 纳指, `000001.SS` 上证）
  - `stocks`: 自选股列表（如 `AAPL`, `600519.SS`）
- `weather`: 天气配置 **(v0.2 新增)**
  - `location_name`: 显示地名
  - `latitude`: 纬度
  - `longitude`: 经度
- `ui`: UI 配置
  - `time_format`: 时间格式 (12h/24h)
  - `layout`: 布局模式

## 使用说明

### 相册管理

1. 访问设置页面 (`/settings`)
2. 在“本地相册管理”区域，点击“新建相册”
3. 创建后点击相册封面或“管理照片”
4. 拖拽照片到上传区域，或点击上传
5. 开启相册的开关（Toggle）以加入轮播列表

### 金融数据设置

1. 访问设置页面
2. 在 "金融数据设置" 区域配置指数和自选股
3. 格式为 `代码,名称`（每行一个），支持 Yahoo Finance 代码格式

**常用指数参考：**

```text
000001.SS,上证指数
399001.SZ,深证成指
^IXIC,纳斯达克
^DJI,道琼斯
^HSI,香港恒生
^VIX,VIX恐慌
GC=F,黄金
BTC-USD,BTC
ETH-USD,ETH
```

**自选股参考：**

```text
300253.SZ,卫宁健康
600584.SS,长电科技
1810.HK,小米集团
0981.HK,中芯国际
```

## 许可证

GPL-3.0
