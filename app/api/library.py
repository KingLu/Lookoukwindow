from typing import List, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, Body
from fastapi.responses import FileResponse

from ..core.config import Config
from ..core.auth import AuthManager
from ..services.album_service import AlbumService
from ..services.library_service import LibraryService

router = APIRouter(prefix="/api/library", tags=["library"])

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

@router.get("/photos")
async def list_photos(
    service: LibraryService = Depends(get_library_service),
    user = Depends(get_current_user)
):
    """获取所有照片库照片"""
    return service.get_photos()

@router.post("/photos")
async def upload_photos(
    files: List[UploadFile] = File(...),
    service: LibraryService = Depends(get_library_service),
    user = Depends(get_current_user)
):
    """上传照片到库"""
    results = []
    for file in files:
        try:
            result = await service.upload_photo(file)
            results.append(result)
        except Exception as e:
            results.append({"status": "error", "filename": file.filename, "error": str(e)})
    return results

@router.put("/photos/{photo_id}")
async def update_photo(
    photo_id: str,
    # 允许更新的字段: 描述, 自定义时间, 自定义位置名
    description: Optional[str] = Form(None),
    date_taken: Optional[str] = Form(None),
    location_name: Optional[str] = Form(None),
    service: LibraryService = Depends(get_library_service),
    user = Depends(get_current_user)
):
    """更新照片信息"""
    updates = {}
    if description is not None: updates["description"] = description
    if date_taken is not None: updates["date_taken"] = date_taken
    if location_name is not None: updates["location_name"] = location_name
    
    result = service.update_photo(photo_id, updates)
    if not result:
        raise HTTPException(status_code=404, detail="照片不存在")
    return result

@router.post("/photos/{photo_id}/rotate")
async def rotate_photo(
    photo_id: str,
    degree: int = 90,
    service: LibraryService = Depends(get_library_service),
    user = Depends(get_current_user)
):
    """旋转照片"""
    result = service.rotate_photo(photo_id, degree)
    if not result:
        raise HTTPException(status_code=404, detail="照片不存在或无法旋转")
    return {"status": "success"}

@router.post("/photos/{photo_id}/crop")
async def crop_photo(
    photo_id: str,
    x: int = Body(...),
    y: int = Body(...),
    width: int = Body(...),
    height: int = Body(...),
    service: LibraryService = Depends(get_library_service),
    user = Depends(get_current_user)
):
    """剪裁照片
    
    Args:
        x: 剪裁区域左上角 X 坐标
        y: 剪裁区域左上角 Y 坐标
        width: 剪裁区域宽度
        height: 剪裁区域高度
    """
    result = service.crop_photo(photo_id, x, y, width, height)
    if not result:
        raise HTTPException(status_code=404, detail="照片不存在或无法剪裁")
    return {"status": "success"}

@router.post("/photos/{photo_id}/reset")
async def reset_photo(
    photo_id: str,
    service: LibraryService = Depends(get_library_service),
    user = Depends(get_current_user)
):
    """重置照片编辑，恢复原图"""
    result = service.reset_photo_edits(photo_id)
    if not result:
        raise HTTPException(status_code=404, detail="照片不存在或无法重置")
    return {"status": "success"}

@router.delete("/photos/{photo_id}")
async def delete_photo(
    photo_id: str,
    service: LibraryService = Depends(get_library_service),
    album_service: AlbumService = Depends(get_album_service),
    user = Depends(get_current_user)
):
    """删除照片"""
    # 1. 从库中删除
    service.delete_photo(photo_id)
    
    # 2. 从所有相册中清理引用
    album_service.purge_photo_from_all_albums(photo_id)
    
    return {"status": "success"}

@router.get("/photos/{filename}")
async def serve_photo(
    filename: str,
    service: LibraryService = Depends(get_library_service)
):
    path = service.library_dir / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(path)

@router.get("/photos/{filename}/thumbnail")
async def serve_thumbnail(
    filename: str,
    service: LibraryService = Depends(get_library_service)
):
    path = service.thumbnails_dir / filename
    if not path.exists():
        path = service.library_dir / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Not found")
    # 禁用缓存，确保编辑后立即显示新图片
    return FileResponse(
        path,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

@router.get("/photos/{filename}/web")
async def serve_web(
    filename: str,
    service: LibraryService = Depends(get_library_service)
):
    path = service.web_images_dir / filename
    if not path.exists():
        path = service.library_dir / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Not found")
    # 禁用缓存，确保编辑后立即显示新图片
    return FileResponse(
        path,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )
