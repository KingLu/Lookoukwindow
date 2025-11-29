from typing import List, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, Body
from fastapi.responses import FileResponse

from ..core.config import Config
from ..core.auth import AuthManager
from ..services.library_service import LibraryService

router = APIRouter(prefix="/api/library", tags=["library"])

def get_config():
    return Config()

def get_library_service(config: Config = Depends(get_config)):
    return LibraryService(config)

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
    degree: int = Body(..., embed=True),
    service: LibraryService = Depends(get_library_service),
    user = Depends(get_current_user)
):
    """旋转照片"""
    result = service.rotate_photo(photo_id, degree)
    if not result:
        raise HTTPException(status_code=404, detail="照片不存在或无法旋转")
    return {"status": "success"}

@router.delete("/photos/{photo_id}")
async def delete_photo(
    photo_id: str,
    service: LibraryService = Depends(get_library_service),
    user = Depends(get_current_user)
):
    """删除照片"""
    service.delete_photo(photo_id)
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
    return FileResponse(path)

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
    return FileResponse(path)
