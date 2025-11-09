"""Google Photos API路由"""
import logging
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import List, Dict, Optional
import asyncio

from ..core.config import Config
from ..services.google_photos import GooglePhotosService
from ..services.photo_cache import PhotoCacheService
from ..core.auth import AuthManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/google-photos", tags=["google-photos"])


class AlbumSelectRequest(BaseModel):
    album_id: str


class PickerMediaItem(BaseModel):
    """来自 Google Photos Picker 的媒体项精简信息"""
    id: str
    baseUrl: Optional[str] = None  # Picker/Library 常见字段；若存在可直接拼参下载
    url: Optional[str] = None      # 某些返回可能为 url 字段（短时效）
    filename: Optional[str] = None
    mimeType: Optional[str] = None
    description: Optional[str] = None
    creationTime: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None


class PickerSelectionRequest(BaseModel):
    """前端提交的 Picker 选择结果"""
    media_items: List[PickerMediaItem]
    auth_token: Optional[str] = None  # 某些下载 URL 需要短期 Bearer，用于服务端直连下载


def get_config() -> Config:
    """获取配置"""
    return Config()


def get_google_photos_service(config: Config = Depends(get_config)) -> GooglePhotosService:
    """获取Google Photos服务"""
    return GooglePhotosService(config)


def get_photo_cache_service(config: Config = Depends(get_config)) -> PhotoCacheService:
    """获取照片缓存服务"""
    return PhotoCacheService(config)


@router.get("/auth/status")
async def get_auth_status(service: GooglePhotosService = Depends(get_google_photos_service)):
    """获取认证状态"""
    client_secrets_path = service._get_client_secrets_path()
    has_client_secrets = client_secrets_path.exists()
    
    return {
        "authenticated": service.is_authenticated(),
        "has_client_secrets": has_client_secrets,
        "client_secrets_path": str(client_secrets_path) if has_client_secrets else None,
        "tokens_dir": str(service.config.tokens_dir)
    }


@router.get("/auth/url")
async def get_auth_url(
    request: Request,
    service: GooglePhotosService = Depends(get_google_photos_service)
):
    """获取授权URL"""
    # 构建重定向URI
    base_url = str(request.base_url).rstrip('/')
    redirect_uri = f"{base_url}/api/google-photos/auth/callback"
    
    try:
        auth_url, state = service.get_authorization_url(redirect_uri)
        return {
            "auth_url": auth_url,
            "state": state
        }
    except FileNotFoundError as e:
        tokens_dir = service.config.tokens_dir
        logger.error(f"未找到 client_secrets.json 文件: {tokens_dir}")
        raise HTTPException(
            status_code=400,
            detail=f"未找到 client_secrets.json 文件。请将文件放到: {tokens_dir}/client_secrets.json"
        )
    except Exception as e:
        logger.error(f"获取授权URL失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取授权URL失败: {str(e)}"
        )


@router.get("/auth/callback")
async def auth_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    service: GooglePhotosService = Depends(get_google_photos_service)
):
    """OAuth回调处理"""
    from fastapi.responses import HTMLResponse
    if error:
        html = f"""
        <html><body style="background:#1a1a1a;color:#fff;font-family:system-ui;padding:20px;">
        <h3>授权失败</h3>
        <div style="margin-top:10px;color:#e74c3c;">错误：{error}</div>
        <div style="margin-top:10px;font-size:13px;color:#ccc;">
            请关闭本页，回到设置页并点击“网页授权（备用）”重试。
        </div>
        <script>setTimeout(() => window.close(), 2000);</script>
        </body></html>
        """
        return HTMLResponse(content=html)
    
    if not code or not state:
        html = """
        <html><body style="background:#1a1a1a;color:#fff;font-family:system-ui;padding:20px;">
        <h3>授权失败</h3>
        <div style="margin-top:10px;color:#e74c3c;">缺少必要参数（code/state）。</div>
        <div style="margin-top:10px;font-size:13px;color:#ccc;">
            请关闭本页，回到设置页并点击“网页授权（备用）”重新发起授权。
        </div>
        <script>setTimeout(() => window.close(), 2000);</script>
        </body></html>
        """
        return HTMLResponse(content=html)
    
    base_url = str(request.base_url).rstrip('/')
    redirect_uri = f"{base_url}/api/google-photos/auth/callback"
    
    success = service.handle_oauth_callback(code, redirect_uri, state)
    
    if success:
        html = """
        <html><body style="background:#1a1a1a;color:#fff;font-family:system-ui;padding:20px;">
        <h3>授权成功</h3>
        <div style="margin-top:10px;color:#27ae60;">现在可以关闭此窗口。</div>
        <script>
        try { if (window.opener) window.opener.postMessage({ type: 'google-photos-auth', status: 'success' }, '*'); } catch(e) {}
        setTimeout(() => window.close(), 1500);
        </script>
        </body></html>
        """
        return HTMLResponse(content=html)
    else:
        # 友好提示：如果使用的是“桌面应用”凭据，网页授权可能失败，应改用“本机授权”或改用“Web 应用”凭据并配置回调URI
        html = """
        <html><body style="background:#1a1a1a;color:#fff;font-family:system-ui;padding:20px;">
        <h3>授权失败</h3>
        <div style="margin-top:10px;color:#e74c3c;">无法交换授权码为访问令牌。</div>
        <div style="margin-top:10px;font-size:13px;color:#ccc;line-height:1.6;">
            可能原因：<br>
            1) 当前使用的是“桌面应用”类型的 client_secrets.json，网页授权不适配。请在设置页使用“本机授权（推荐）”；或<br>
            2) 改为在 Google Cloud Console 创建“Web 应用”类型的 OAuth 客户端，并将回调URI加入允许列表：<br>
               - http://127.0.0.1:8000/api/google-photos/auth/callback<br>
               - http://<你的局域网IP>:8000/api/google-photos/auth/callback
        </div>
        <script>setTimeout(() => window.close(), 3500);</script>
        </body></html>
        """
        return HTMLResponse(content=html)


@router.get("/albums")
async def list_albums(service: GooglePhotosService = Depends(get_google_photos_service)):
    """列出所有相册"""
    if not service.is_authenticated():
        raise HTTPException(status_code=401, detail="未授权，请先完成Google授权")
    
    try:
        albums = service.list_albums()
        return {"albums": albums}
    except Exception as e:
        error_msg = str(e)
        if "insufficient authentication scopes" in error_msg.lower():
            logger.error(f"授权作用域不足: {e}")
            raise HTTPException(
                status_code=403,
                detail="授权作用域不足，请重新授权。确保在 OAuth 同意屏幕中添加了 photoslibrary.readonly 作用域"
            )
        logger.error(f"获取相册列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取相册列表失败: {error_msg}")


@router.post("/albums/select")
async def select_album(
    album_data: AlbumSelectRequest,
    config: Config = Depends(get_config)
):
    """选择相册"""
    config.set('google.album_id', album_data.album_id)
    config.save()
    return {"status": "success", "message": "相册选择成功"}


@router.get("/photos")
async def get_photos(
    config: Config = Depends(get_config),
    cache_service: PhotoCacheService = Depends(get_photo_cache_service)
):
    """获取照片列表（从缓存）"""
    album_id = config.get('google.album_id')
    if not album_id:
        return {"photos": []}
    
    # 从缓存获取照片列表
    cached_photo_ids = cache_service.list_cached_photos()
    photos = []
    
    for photo_id in cached_photo_ids:
        metadata = cache_service.get_metadata(photo_id)
        if metadata:
            photos.append({
                "id": photo_id,
                **metadata
            })
    
    # 按时间排序
    photos.sort(key=lambda x: x.get('photoTime', ''), reverse=True)
    
    return {"photos": photos}


@router.get("/photos/{photo_id}/image")
async def get_photo_image(
    photo_id: str,
    size: str = "medium",
    cache_service: PhotoCacheService = Depends(get_photo_cache_service)
):
    """获取照片图片"""
    photo_data = cache_service.get_photo(photo_id, size)
    if not photo_data:
        raise HTTPException(status_code=404, detail="照片不存在")
    
    from fastapi.responses import Response
    return Response(content=photo_data, media_type="image/jpeg")


@router.post("/sync")
async def sync_photos(
    request: Request,
    config: Config = Depends(get_config),
    service: GooglePhotosService = Depends(get_google_photos_service),
    cache_service: PhotoCacheService = Depends(get_photo_cache_service)
):
    """同步照片"""
    if not service.is_authenticated():
        raise HTTPException(status_code=401, detail="未授权，请先完成Google授权")
    
    album_id = config.get('google.album_id')
    if not album_id:
        raise HTTPException(status_code=400, detail="请先选择相册")
    
    # 在后台任务中同步
    asyncio.create_task(_sync_photos_task(service, cache_service, album_id))
    
    return {"status": "started", "message": "同步任务已启动"}


@router.post("/auth/desktop")
async def start_desktop_auth(
    service: GooglePhotosService = Depends(get_google_photos_service)
):
    """启动桌面应用本地回调授权（在本机打开浏览器进行授权）"""
    try:
        # 在后台线程启动，避免阻塞请求
        loop = asyncio.get_running_loop()
        loop.run_in_executor(None, service.start_desktop_authorization)
        return {
            "status": "started",
            "message": "已启动本机授权流程，将自动打开浏览器。授权完成后，此页面会自动显示已授权状态。"
        }
    except Exception as e:
        logger.error(f"启动桌面授权失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动桌面授权失败: {str(e)}")


@router.post("/auth/clear")
async def clear_auth(
    service: GooglePhotosService = Depends(get_google_photos_service)
):
    """清除已保存的授权凭据"""
    if service.clear_credentials():
        return {"status": "success", "message": "已清除授权，请重新进行授权"}
    raise HTTPException(status_code=500, detail="清除授权失败")


@router.post("/picker/selection")
async def import_picker_selection(
    payload: PickerSelectionRequest,
    cache_service: PhotoCacheService = Depends(get_photo_cache_service)
):
    """
    导入来自 Google Photos Picker 的选择结果，并立即下载/缓存所选媒体。
    注意：此接口假定前端已通过 Picker 获取到媒体项的 baseUrl/url 以及（可选）短期 auth_token。
    """
    if not payload.media_items:
        raise HTTPException(status_code=400, detail="media_items 不能为空")
    
    import httpx
    headers = {}
    if payload.auth_token:
        headers["Authorization"] = f"Bearer {payload.auth_token}"
    
    success = 0
    failed: List[Dict] = []
    for item in payload.media_items:
        media_id = item.id
        # 选择可用的下载基地址
        base = item.baseUrl or item.url
        if not base:
            failed.append({"id": media_id, "reason": "缺少可下载的URL（baseUrl/url）"})
            continue
        
        # 统一构造不同尺寸下载地址（若 URL 已自带参数则直接使用）
        def build_url(target_base: str, width: int) -> str:
            return target_base if ("=w" in target_base or "=h" in target_base) else f"{target_base}=w{width}"
        
        try:
            # 下载缩略图与中等尺寸
            thumb_url = build_url(base, 200)
            medium_url = build_url(base, 1920)
            
            thumb_resp = httpx.get(thumb_url, headers=headers, timeout=20.0)
            if thumb_resp.status_code == 200:
                cache_service.save_photo(
                    media_id,
                    thumb_resp.content,
                    size="thumbnail",
                    metadata={
                        "id": media_id,
                        "filename": item.filename or "",
                        "mimeType": item.mimeType or "",
                        "creationTime": item.creationTime or "",
                        "width": item.width,
                        "height": item.height,
                        "description": item.description or "",
                        "source": "picker"
                    }
                )
            # 中等尺寸
            medium_resp = httpx.get(medium_url, headers=headers, timeout=30.0)
            if medium_resp.status_code == 200:
                cache_service.save_photo(
                    media_id,
                    medium_resp.content,
                    size="medium",
                    metadata={
                        "id": media_id,
                        "filename": item.filename or "",
                        "mimeType": item.mimeType or "",
                        "creationTime": item.creationTime or "",
                        "width": item.width,
                        "height": item.height,
                        "description": item.description or "",
                        "source": "picker"
                    }
                )
                success += 1
            else:
                failed.append({"id": media_id, "reason": f"下载中等尺寸失败：{medium_resp.status_code}"})
        except Exception as e:
            failed.append({"id": media_id, "reason": f"下载异常：{e}"})
    
    # 下载后清理缓存以满足容量约束
    cache_service.cleanup_cache()
    
    return {
        "status": "ok",
        "imported": success,
        "failed": failed
    }


@router.post("/picker/clear")
async def clear_picker_cache(
    cache_service: PhotoCacheService = Depends(get_photo_cache_service)
):
    """清空通过 Picker 导入的缓存照片（将清空所有缓存）"""
    cache_service.clear_cache()
    return {"status": "ok", "message": "已清空缓存"}


@router.get("/picker/client-id")
async def get_picker_client_id(config: Config = Depends(get_config)):
    """
    尝试从 tokens_dir/client_secrets.json 提取 Web 应用的 client_id。
    结构示例：
    {
      "web": { "client_id": "...", "javascript_origins": [...], "redirect_uris": [...] }
    }
    或
    {
      "installed": { "client_id": "...", ... }  # 桌面应用；不适用于前端GIS
    }
    """
    secrets_path = (config.tokens_dir / "client_secrets.json")
    if not secrets_path.exists():
        return {"client_id": None, "type": None}
    try:
        import json
        data = json.loads(secrets_path.read_text(encoding="utf-8"))
        if "web" in data and "client_id" in data["web"]:
            return {"client_id": data["web"]["client_id"], "type": "web"}
        if "installed" in data and "client_id" in data["installed"]:
            # 返回桌面应用的 client_id（提示仅供参考，GIS需 web 客户端）
            return {"client_id": data["installed"]["client_id"], "type": "installed"}
    except Exception:
        pass
    return {"client_id": None, "type": None}


class PickerSessionCreateRequest(BaseModel):
    access_token: str
    autoclose: Optional[bool] = True


@router.post("/picker/session/create")
async def create_picker_session(payload: PickerSessionCreateRequest):
    """
    使用前端获取到的 OAuth 访问令牌创建 Picker 会话，返回 pickerUri 与 session_id。
    注意：该端点依赖 Google Photos Picker API 的会话创建 REST 接口。
    """
    import httpx
    headers = {
        "Authorization": f"Bearer {payload.access_token}",
        "Content-Type": "application/json"
    }
    # 按照公开资料尝试的会话创建端点；如有变更请根据官方文档调整
    create_url = "https://photoslibrary.googleapis.com/v1/sessions"
    try:
        resp = httpx.post(create_url, headers=headers, json={}, timeout=20.0)
        if resp.status_code >= 400:
            detail = resp.text
            raise HTTPException(status_code=resp.status_code, detail=f"创建会话失败：{detail}")
        data = resp.json()
        picker_uri = data.get("pickerUri") or data.get("picker_uri") or ""
        session_id = data.get("id") or data.get("name") or ""
        if not picker_uri:
            raise HTTPException(status_code=500, detail="创建会话成功但未返回 pickerUri")
        if payload.autoclose and not picker_uri.endswith("/autoclose"):
            picker_uri = picker_uri.rstrip("/") + "/autoclose"
        return {"pickerUri": picker_uri, "sessionId": session_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建会话异常：{e}")


@router.get("/picker/session/{session_id}/status")
async def get_picker_session_status(session_id: str, access_token: str):
    """
    查询会话状态，检查 mediaItemsSet 是否为 true。
    返回完整响应以便前端读取建议轮询间隔等字段。
    """
    import httpx
    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"https://photoslibrary.googleapis.com/v1/sessions/{session_id}"
    try:
        resp = httpx.get(url, headers=headers, timeout=15.0)
        if resp.status_code >= 400:
            return {"ok": False, "status": resp.status_code, "detail": resp.text}
        return {"ok": True, "data": resp.json()}
    except Exception as e:
        return {"ok": False, "detail": str(e)}


@router.get("/picker/session/{session_id}/media")
async def list_picker_selected_media(session_id: str, access_token: str):
    """
    列出会话中已选择的媒体项，用于后续导入。
    """
    import httpx
    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"https://photoslibrary.googleapis.com/v1/sessions/{session_id}/mediaItems"
    try:
        resp = httpx.get(url, headers=headers, timeout=20.0)
        if resp.status_code >= 400:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return resp.json()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def _sync_photos_task(
    service: GooglePhotosService,
    cache_service: PhotoCacheService,
    album_id: str
):
    """同步照片的后台任务"""
    try:
        # 确保服务已初始化
        if not service.service:
            logger.error("Google Photos 服务未初始化")
            return
        
        # 获取所有媒体项
        media_items = service.get_all_album_media_items(album_id)
        
        # 下载并缓存照片
        for item in media_items:
            media_id = item.get('id')
            if not media_id:
                continue
            
            # 检查是否已缓存
            if cache_service.photo_exists(media_id, 'medium'):
                continue
            
            # 下载缩略图
            thumbnail_data = service.download_media_item(item, 'thumbnail')
            if thumbnail_data:
                cache_service.save_photo(media_id, thumbnail_data, 'thumbnail')
            
            # 下载中等尺寸
            medium_data = service.download_media_item(item, 'medium')
            if medium_data:
                metadata = service.get_media_item_metadata(item)
                cache_service.save_photo(media_id, medium_data, 'medium', metadata)
        
        # 清理缓存
        cache_service.cleanup_cache()
    except Exception as e:
        print(f"同步照片失败: {e}")


@router.get("/sync/status")
async def get_sync_status(
    cache_service: PhotoCacheService = Depends(get_photo_cache_service)
):
    """获取同步状态"""
    cache_size = cache_service.get_cache_size()
    cache_size_mb = cache_size / (1024 * 1024)
    photo_count = len(cache_service.list_cached_photos())
    
    return {
        "photo_count": photo_count,
        "cache_size_mb": round(cache_size_mb, 2),
        "cache_size_gb": round(cache_size_mb / 1024, 2)
    }
