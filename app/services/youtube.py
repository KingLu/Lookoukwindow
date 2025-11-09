"""YouTube 直播服务"""
import re
from typing import Dict, List, Optional
import httpx


class YouTubeService:
    """YouTube 服务类"""
    
    @staticmethod
    def extract_video_id(url: str) -> Optional[str]:
        """从URL提取视频ID"""
        patterns = [
            r'(?:youtube\.com\/embed\/|youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com\/channel\/([a-zA-Z0-9_-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    @staticmethod
    def normalize_url(url: str) -> str:
        """标准化YouTube URL为embed格式"""
        video_id = YouTubeService.extract_video_id(url)
        if video_id:
            return f"https://www.youtube.com/embed/{video_id}?autoplay=1&mute=0"
        return url
    
    @staticmethod
    def get_embed_url(channel_name: str, config: Dict) -> Optional[str]:
        """获取频道的embed URL"""
        # 从预设中查找
        presets = config.get('youtube', {}).get('presets', [])
        for preset in presets:
            if preset.get('name') == channel_name:
                return preset.get('url')
        
        # 从自定义频道中查找
        custom_channels = config.get('youtube', {}).get('custom_channels', [])
        for channel in custom_channels:
            if channel.get('name') == channel_name:
                return YouTubeService.normalize_url(channel.get('url', ''))
        
        return None
    
    @staticmethod
    def get_all_channels(config: Dict) -> List[Dict]:
        """获取所有频道列表"""
        channels = []
        
        # 添加预设频道
        presets = config.get('youtube', {}).get('presets', [])
        channels.extend(presets)
        
        # 添加自定义频道
        custom_channels = config.get('youtube', {}).get('custom_channels', [])
        channels.extend(custom_channels)
        
        return channels
    
    @staticmethod
    def add_custom_channel(name: str, url: str, config: Dict) -> bool:
        """添加自定义频道"""
        # 验证URL
        video_id = YouTubeService.extract_video_id(url)
        if not video_id:
            return False
        
        # 检查是否已存在
        custom_channels = config.get('youtube', {}).get('custom_channels', [])
        for channel in custom_channels:
            if channel.get('name') == name:
                channel['url'] = YouTubeService.normalize_url(url)
                return True
        
        # 添加新频道
        custom_channels.append({
            'name': name,
            'url': YouTubeService.normalize_url(url),
            'channel_id': video_id
        })
        
        if 'youtube' not in config:
            config['youtube'] = {}
        config['youtube']['custom_channels'] = custom_channels
        
        return True
    
    @staticmethod
    def remove_custom_channel(name: str, config: Dict) -> bool:
        """删除自定义频道"""
        custom_channels = config.get('youtube', {}).get('custom_channels', [])
        original_len = len(custom_channels)
        custom_channels[:] = [ch for ch in custom_channels if ch.get('name') != name]
        return len(custom_channels) < original_len
