"""设置API路由"""
import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict

from ..core.config import Config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsUpdateRequest(BaseModel):
    layout: Optional[str] = None
    slideshow_interval_seconds: Optional[int] = None
    slideshow_order: Optional[str] = None  # 'shuffle' or 'sequential'
    slideshow_transition: Optional[str] = None  # 'fade', 'slide-left', etc.
    show_metadata: Optional[bool] = None
    screen_rotation: Optional[str] = None
    scale: Optional[float] = None
    time_format: Optional[str] = None
    weather_location_name: Optional[str] = None
    weather_latitude: Optional[float] = None
    weather_longitude: Optional[float] = None
    finance_indices: Optional[List[Dict[str, str]]] = None
    finance_stocks: Optional[List[Dict[str, str]]] = None
    finance_ticker_speed_seconds: Optional[int] = None
    finance_stock_switch_interval_seconds: Optional[int] = None
    energy_enabled: Optional[bool] = None
    energy_start_time: Optional[str] = None
    energy_end_time: Optional[str] = None


def get_config() -> Config:
    """获取配置"""
    return Config()


@router.get("/")
async def get_settings(config: Config = Depends(get_config)):
    """获取设置"""
    return {
        "layout": config.get('ui.layout', 'side-by-side'),
        "slideshow_interval_seconds": config.get('ui.slideshow_interval_seconds', 10),
        "slideshow_order": config.get('ui.slideshow_order', 'shuffle'),
        "slideshow_transition": config.get('ui.slideshow_transition', 'fade'),
        "show_metadata": config.get('ui.show_metadata', True),
        "screen_rotation": config.get('display.screen_rotation', 'normal'),
        "scale": config.get('display.scale', 1.0),
        "time_format": config.get('ui.time_format', '24h'),
        "weather_location_name": config.get('weather.location_name', '北京市大兴区'),
        "weather_latitude": config.get('weather.latitude', 39.73),
        "weather_longitude": config.get('weather.longitude', 116.33),
        "finance_indices": config.get('finance.indices', []),
        "finance_stocks": config.get('finance.stocks', []),
        "finance_ticker_speed_seconds": config.get('finance.ticker_speed_seconds', 30),
        "finance_stock_switch_interval_seconds": config.get('finance.stock_switch_interval_seconds', 10),
        "energy_enabled": config.get('energy.enabled', True),
        "energy_start_time": config.get('energy.start_time', '22:30'),
        "energy_end_time": config.get('energy.end_time', '05:30')
    }


@router.post("/")
async def update_settings(
    settings: SettingsUpdateRequest,
    config: Config = Depends(get_config)
):
    """更新设置"""
    logger.info("Updating settings")
    if settings.layout is not None:
        logger.info(f"Setting layout to: {settings.layout}")
        config.set('ui.layout', settings.layout)
    if settings.slideshow_interval_seconds is not None:
        config.set('ui.slideshow_interval_seconds', settings.slideshow_interval_seconds)
    if settings.slideshow_order is not None:
        config.set('ui.slideshow_order', settings.slideshow_order)
    if settings.slideshow_transition is not None:
        config.set('ui.slideshow_transition', settings.slideshow_transition)
    if settings.show_metadata is not None:
        config.set('ui.show_metadata', settings.show_metadata)
    if settings.screen_rotation is not None:
        config.set('display.screen_rotation', settings.screen_rotation)
    if settings.scale is not None:
        config.set('display.scale', settings.scale)
    if settings.time_format is not None:
        config.set('ui.time_format', settings.time_format)
    if settings.weather_location_name is not None:
        config.set('weather.location_name', settings.weather_location_name)
    if settings.weather_latitude is not None:
        config.set('weather.latitude', settings.weather_latitude)
    if settings.weather_longitude is not None:
        config.set('weather.longitude', settings.weather_longitude)
    
    if settings.finance_indices is not None:
        config.set('finance.indices', settings.finance_indices)
    if settings.finance_stocks is not None:
        config.set('finance.stocks', settings.finance_stocks)
    if settings.finance_ticker_speed_seconds is not None:
        config.set('finance.ticker_speed_seconds', settings.finance_ticker_speed_seconds)
    if settings.finance_stock_switch_interval_seconds is not None:
        config.set('finance.stock_switch_interval_seconds', settings.finance_stock_switch_interval_seconds)
    
    if settings.energy_enabled is not None:
        config.set('energy.enabled', settings.energy_enabled)
    if settings.energy_start_time is not None:
        config.set('energy.start_time', settings.energy_start_time)
    if settings.energy_end_time is not None:
        config.set('energy.end_time', settings.energy_end_time)

    config.save()
    return {"status": "success", "message": "设置更新成功"}
