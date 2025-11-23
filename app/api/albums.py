from typing import List, Optional
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import FileResponse

from ..core.config import Config
from ..core.auth import AuthManager
from ..services.album_service import AlbumService

router = APIRouter(prefix="/api/albums", tags=["albums"])

def get_config():
    return Config()

def get_album_service(config: Config = Depends(get_config)):
    return AlbumService(config)

async def get_current_user(request: Request, config: Config = Depends(get_config)):
    """获取当前用户"""
    auth_manager = AuthManager(config)
    is_authenticated = await auth_manager.get_current_user(request)
    if not is_authenticated:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return True

@router.get("")
async def list_albums(
    service: AlbumService = Depends(get_album_service),
    user = Depends(get_current_user)
):
    """获取所有相册"""
    return service.list_albums()

@router.post("")
async def create_album(
    name: str = Form(...),
    description: str = Form(""),
    service: AlbumService = Depends(get_album_service),
    user = Depends(get_current_user)
):
    """创建相册"""
    return service.create_album(name, description)

@router.get("/slideshow")
async def get_slideshow_photos(
    service: AlbumService = Depends(get_album_service)
):
    """获取用于轮播的所有照片"""
    # 此接口不需要认证，因为前端播放器可能在无会话状态运行
    return service.get_all_active_photos()

@router.get("/{album_id}")
async def get_album(
    album_id: str,
    service: AlbumService = Depends(get_album_service),
    user = Depends(get_current_user)
):
    """获取相册详情"""
    album = service.get_album(album_id)
    if not album:
        raise HTTPException(status_code=404, detail="相册不存在")
    return album

@router.put("/{album_id}")
async def update_album(
    album_id: str,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    active: Optional[bool] = Form(None),
    service: AlbumService = Depends(get_album_service),
    user = Depends(get_current_user)
):
    """更新相册信息（包括激活状态）"""
    result = service.update_album(album_id, name, description, active)
    if not result:
        raise HTTPException(status_code=404, detail="相册不存在")
    return result

@router.delete("/{album_id}")
async def delete_album(
    album_id: str,
    service: AlbumService = Depends(get_album_service),
    user = Depends(get_current_user)
):
    """删除相册"""
    service.delete_album(album_id)
    return {"status": "success"}

@router.get("/{album_id}/photos")
async def get_album_photos(
    album_id: str,
    service: AlbumService = Depends(get_album_service),
    user = Depends(get_current_user)
):
    """获取相册内的照片"""
    return service.get_photos(album_id)

@router.post("/{album_id}/photos")
async def upload_photos(
    album_id: str,
    files: List[UploadFile] = File(...),
    service: AlbumService = Depends(get_album_service),
    user = Depends(get_current_user)
):
    """上传照片（支持多文件）"""
    results = []
    for file in files:
        try:
            result = await service.upload_photo(album_id, file)
            results.append(result)
        except Exception as e:
            results.append({"error": str(e), "filename": file.filename})
    return results

@router.delete("/{album_id}/photos/{filename}")
async def delete_photo(
    album_id: str,
    filename: str,
    service: AlbumService = Depends(get_album_service),
    user = Depends(get_current_user)
):
    """删除照片"""
    service.delete_photo(album_id, filename)
    return {"status": "success"}

@router.get("/{album_id}/photos/{filename}")
async def serve_photo(
    album_id: str,
    filename: str,
    service: AlbumService = Depends(get_album_service)
):
    """获取照片文件"""
    path = service.albums_dir / album_id / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Photo not found")
    return FileResponse(path)

@router.get("/{album_id}/photos/{filename}/thumbnail")
async def serve_thumbnail(
    album_id: str,
    filename: str,
    service: AlbumService = Depends(get_album_service)
):
    """获取缩略图"""
    path = service.thumbnails_dir / album_id / filename
    if not path.exists():
        # 如果缩略图不存在，尝试返回原图
        path = service.albums_dir / album_id / filename
        if not path.exists():
            raise HTTPException(status_code=404, detail="Thumbnail not found")
    return FileResponse(path)
