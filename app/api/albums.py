from typing import List, Optional
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, Body
from fastapi.responses import FileResponse

from ..core.config import Config
from ..core.auth import AuthManager
from ..services.album_service import AlbumService
from ..services.library_service import LibraryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/albums", tags=["albums"])

def get_config():
    return Config()

def get_library_service(config: Config = Depends(get_config)):
    return LibraryService(config)

def get_album_service(
    config: Config = Depends(get_config), 
    library_service: LibraryService = Depends(get_library_service)
):
    return AlbumService(config, library_service)

async def get_current_user(request: Request, config: Config = Depends(get_config)):
    auth_manager = AuthManager(config)
    if not await auth_manager.get_current_user(request):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return True

@router.get("")
async def list_albums(
    service: AlbumService = Depends(get_album_service),
    user = Depends(get_current_user)
):
    return service.list_albums()

@router.post("")
async def create_album(
    name: str = Form(...),
    description: str = Form(""),
    service: AlbumService = Depends(get_album_service),
    user = Depends(get_current_user)
):
    logger.info(f"Creating album: {name}")
    return service.create_album(name, description)

@router.get("/slideshow")
async def get_slideshow_photos(
    service: AlbumService = Depends(get_album_service)
):
    return service.get_all_active_photos()

@router.get("/{album_id}")
async def get_album(
    album_id: str,
    service: AlbumService = Depends(get_album_service),
    user = Depends(get_current_user)
):
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
    logger.info(f"Deleting album: {album_id}")
    service.delete_album(album_id)
    return {"status": "success"}

@router.get("/{album_id}/photos")
async def get_album_photos(
    album_id: str,
    service: AlbumService = Depends(get_album_service),
    user = Depends(get_current_user)
):
    return service.get_photos(album_id)

@router.post("/{album_id}/photos/add")
async def add_photos_to_album(
    album_id: str,
    photo_ids: List[str] = Body(..., embed=True),
    service: AlbumService = Depends(get_album_service),
    user = Depends(get_current_user)
):
    """将现有照片添加到相册"""
    service.add_photos(album_id, photo_ids)
    return {"status": "success"}

@router.post("/{album_id}/photos/remove")
async def remove_photos_from_album(
    album_id: str,
    photo_ids: List[str] = Body(..., embed=True),
    service: AlbumService = Depends(get_album_service),
    user = Depends(get_current_user)
):
    """从相册移除照片"""
    service.remove_photos(album_id, photo_ids)
    return {"status": "success"}

@router.post("/{album_id}/photos")
async def upload_photos(
    album_id: str,
    files: List[UploadFile] = File(...),
    service: AlbumService = Depends(get_album_service),
    library_service: LibraryService = Depends(get_library_service),
    user = Depends(get_current_user)
):
    """上传并添加到相册 (快捷方式)"""
    logger.info(f"Uploading {len(files)} photos to album {album_id}")
    results = []
    success_ids = []
    
    for file in files:
        try:
            # 1. 上传到库
            res = await library_service.upload_photo(file)
            if res["status"] in ["success", "duplicate"]:
                photo_data = res["photo"]
                success_ids.append(photo_data["id"])
                results.append(res)
            else:
                results.append(res)
        except Exception as e:
            results.append({"status": "error", "filename": file.filename, "error": str(e)})
            
    # 2. 添加到相册
    if success_ids:
        service.add_photos(album_id, success_ids)
        
    return results

# 兼容旧接口，但这些文件访问接口实际上可以重定向到 library
# 前端如果还在用 /api/albums/{id}/photos/{file}，需要 AlbumService 知道去哪里找
# AlbumService.get_photos 返回的 url 字段现在指向 /api/albums/... 还是 /api/library/... ?
# 在 LibraryService migration 中，我把 url 改成了 /api/library/...
# 所以前端如果用新的 url，就不会调到这里。
# 但为了安全起见（如果旧缓存），保留这些接口并代理到 LibraryService

@router.get("/{album_id}/photos/{filename}")
async def serve_photo(
    album_id: str,
    filename: str,
    service: AlbumService = Depends(get_album_service)
):
    # 实际上现在路径都在 library
    path = service.config.library_dir / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Photo not found")
    return FileResponse(path)

@router.get("/{album_id}/photos/{filename}/thumbnail")
async def serve_thumbnail(
    album_id: str,
    filename: str,
    service: AlbumService = Depends(get_album_service)
):
    path = service.config.thumbnails_dir / filename
    if not path.exists():
        path = service.config.library_dir / filename
    if not path.exists():
         raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(path)
