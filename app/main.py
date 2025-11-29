"""FastAPI 主应用"""
import logging
import sys
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import os
from pathlib import Path

from .core.config import Config
from .core.auth import AuthManager
from .api import auth, youtube, settings, albums, finance, library

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# 设置应用相关模块的日志级别
logging.getLogger("app").setLevel(logging.DEBUG)

app = FastAPI(title="Lookoukwindow", description="NASA 太空直播和本地相册展示")

# 配置CORS（允许局域网访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 局域网环境，允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加 Referrer-Policy 响应头（修复 YouTube 错误 153）
@app.middleware("http")
async def add_referrer_policy(request: Request, call_next):
    """添加 Referrer-Policy 响应头"""
    response = await call_next(request)
    # 只在 HTML 响应中添加，使用 origin 策略以支持 YouTube 嵌入
    if "text/html" in response.headers.get("content-type", ""):
        response.headers["Referrer-Policy"] = "origin"
        # 添加 Permissions-Policy 以减少警告（允许 YouTube iframe 需要的权限）
        # 注意：unload 功能正在被弃用，很多现代浏览器（如 Chrome）会发出警告，
        # 但 YouTube 嵌入播放器目前仍然可能尝试使用它。
        # 我们将其设置为 self 或者是 * 来尝试兼容，但浏览器可能依然会警告。
        # 关键是确保 autoplay 等核心功能可用。
        response.headers["Permissions-Policy"] = (
            "accelerometer=*, autoplay=*, clipboard-write=*, "
            "encrypted-media=*, fullscreen=*, gyroscope=*, "
            "picture-in-picture=*, web-share=*"
        )
    return response

# 注册API路由
app.include_router(auth.router)
app.include_router(youtube.router)
app.include_router(settings.router)
app.include_router(albums.router)
app.include_router(finance.router)
app.include_router(library.router)

# 配置模板和静态文件
templates_dir = Path(__file__).parent / "templates"
static_dir = Path(__file__).parent / "static"

templates = Jinja2Templates(directory=str(templates_dir))
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# 全局配置实例
_config = None


def get_config() -> Config:
    """获取全局配置实例"""
    global _config
    if _config is None:
        _config = Config()
    return _config


# 认证中间件
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """认证中间件"""
    # 排除登录页面、API端点、静态文件
    if (request.url.path.startswith("/api/") or 
        request.url.path.startswith("/static/")):
        response = await call_next(request)
        return response
    
    # 允许无密码访问首页(Kiosk模式)和登录/设置页
    if request.url.path in ["/", "/login", "/setup", "/favicon.ico"]:
        response = await call_next(request)
        return response
    
    # 其他页面（如 /settings）需要认证
    config = get_config()
    auth_manager = AuthManager(config)
    is_authenticated = await auth_manager.get_current_user(request)
    
    if not is_authenticated:
        # 检查是否设置了密码
        if not config.is_password_set():
            if request.url.path != "/setup":
                return RedirectResponse(url="/setup")
        else:
            if request.url.path != "/login":
                return RedirectResponse(url="/login")
    
    response = await call_next(request)
    return response


@app.get("/favicon.ico")
async def favicon():
    """返回 favicon"""
    from fastapi.responses import Response
    # 返回 SVG favicon
    svg_icon = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <text y=".9em" font-size="90">🚀</text>
    </svg>'''
    return Response(content=svg_icon, media_type="image/svg+xml")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """主页"""
    config = get_config()
    default_channel = config.get('youtube.default_channel', 'NASA TV') or 'NASA TV'
    layout = config.get('ui.layout', 'side-by-side') or 'side-by-side'
    slideshow_interval = config.get('ui.slideshow_interval_seconds', 10) or 10
    slideshow_transition = config.get('ui.slideshow_transition', 'fade') or 'fade'
    show_metadata = config.get('ui.show_metadata', True)
    time_format = config.get('ui.time_format', '24h')
    weather_config = config.get('weather', {})
    finance_config = config.get('finance', {})
    energy_config = config.get('energy', {})
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "default_channel": default_channel,
        "layout": layout,
        "slideshow_interval_seconds": slideshow_interval,
        "slideshow_transition": slideshow_transition,
        "show_metadata": show_metadata,
        "time_format": time_format,
        "weather_config": weather_config,
        "finance_config": finance_config,
        "energy_config": energy_config
    })


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """登录页面"""
    config = get_config()
    if not config.is_password_set():
        return RedirectResponse(url="/setup")
    
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request):
    """设置页面（首次设置密码）"""
    config = get_config()
    if config.is_password_set():
        return RedirectResponse(url="/")
    
    return templates.TemplateResponse("setup.html", {"request": request})


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """设置页面"""
    config = get_config()
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "config": config._config
    })

# New Admin Pages
@app.get("/admin/library", response_class=HTMLResponse)
async def library_page(request: Request):
    """照片库管理"""
    return templates.TemplateResponse("library.html", {"request": request})

@app.get("/admin/albums", response_class=HTMLResponse)
async def albums_page(request: Request):
    """相册管理"""
    return templates.TemplateResponse("albums.html", {"request": request})


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok"}
