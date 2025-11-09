"""YouTube API路由"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict

from ..core.config import Config
from ..services.youtube import YouTubeService

router = APIRouter(prefix="/api/youtube", tags=["youtube"])


class ChannelAddRequest(BaseModel):
    name: str
    url: str


def get_config() -> Config:
    """获取配置"""
    return Config()


@router.get("/channels")
async def get_channels(config: Config = Depends(get_config)):
    """获取所有频道"""
    channels = YouTubeService.get_all_channels(config._config)
    default_channel = config.get('youtube.default_channel', 'NASA TV')
    
    return {
        "channels": channels,
        "default_channel": default_channel
    }


@router.post("/channels")
async def add_channel(
    channel_data: ChannelAddRequest,
    config: Config = Depends(get_config)
):
    """添加自定义频道"""
    success = YouTubeService.add_custom_channel(
        channel_data.name,
        channel_data.url,
        config._config
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="无效的YouTube URL")
    
    config.save()
    return {"status": "success", "message": "频道添加成功"}


@router.delete("/channels/{channel_name}")
async def delete_channel(
    channel_name: str,
    config: Config = Depends(get_config)
):
    """删除自定义频道"""
    success = YouTubeService.remove_custom_channel(channel_name, config._config)
    
    if not success:
        raise HTTPException(status_code=404, detail="频道不存在")
    
    config.save()
    return {"status": "success", "message": "频道删除成功"}


@router.get("/embed/{channel_name}")
async def get_embed_url(
    channel_name: str,
    config: Config = Depends(get_config)
):
    """获取频道的embed URL"""
    embed_url = YouTubeService.get_embed_url(channel_name, config._config)
    
    if not embed_url:
        raise HTTPException(status_code=404, detail="频道不存在")
    
    return {"embed_url": embed_url}


@router.post("/default")
async def set_default_channel(
    channel_name: str,
    config: Config = Depends(get_config)
):
    """设置默认频道"""
    # 验证频道是否存在
    embed_url = YouTubeService.get_embed_url(channel_name, config._config)
    if not embed_url:
        raise HTTPException(status_code=404, detail="频道不存在")
    
    config.set('youtube.default_channel', channel_name)
    config.save()
    
    return {"status": "success", "message": "默认频道设置成功"}
