"""设置API路由"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from ..core.config import Config

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsUpdateRequest(BaseModel):
    layout: Optional[str] = None
    slideshow_interval_seconds: Optional[int] = None
    show_metadata: Optional[bool] = None
    screen_rotation: Optional[str] = None
    scale: Optional[float] = None


def get_config() -> Config:
    """获取配置"""
    return Config()


@router.get("/")
async def get_settings(config: Config = Depends(get_config)):
    """获取设置"""
    return {
        "layout": config.get('ui.layout', 'side-by-side'),
        "slideshow_interval_seconds": config.get('ui.slideshow_interval_seconds', 10),
        "show_metadata": config.get('ui.show_metadata', True),
        "screen_rotation": config.get('display.screen_rotation', 'normal'),
        "scale": config.get('display.scale', 1.0)
    }


@router.post("/")
async def update_settings(
    settings: SettingsUpdateRequest,
    config: Config = Depends(get_config)
):
    """更新设置"""
    if settings.layout is not None:
        config.set('ui.layout', settings.layout)
    if settings.slideshow_interval_seconds is not None:
        config.set('ui.slideshow_interval_seconds', settings.slideshow_interval_seconds)
    if settings.show_metadata is not None:
        config.set('ui.show_metadata', settings.show_metadata)
    if settings.screen_rotation is not None:
        config.set('display.screen_rotation', settings.screen_rotation)
    if settings.scale is not None:
        config.set('display.scale', settings.scale)
    
    config.save()
    return {"status": "success", "message": "设置更新成功"}
