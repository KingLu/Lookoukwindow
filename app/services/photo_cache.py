"""照片缓存管理服务"""
import hashlib
import shutil
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import json

from ..core.config import Config


class PhotoCacheService:
    """照片缓存服务"""
    
    def __init__(self, config: Config):
        self.config = config
        self.cache_dir = config.cache_dir / "photos"
        self.thumbnails_dir = config.cache_dir / "thumbnails"
        self.metadata_file = config.cache_dir / "metadata.json"
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.thumbnails_dir.mkdir(parents=True, exist_ok=True)
        
        self._metadata = self._load_metadata()
    
    def _load_metadata(self) -> Dict:
        """加载元数据"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_metadata(self):
        """保存元数据"""
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self._metadata, f, ensure_ascii=False, indent=2, default=str)
    
    def _get_file_hash(self, media_id: str) -> str:
        """获取文件哈希"""
        return hashlib.md5(media_id.encode()).hexdigest()
    
    def get_photo_path(self, media_id: str, size: str = 'medium') -> Path:
        """获取照片路径"""
        file_hash = self._get_file_hash(media_id)
        if size == 'thumbnail':
            return self.thumbnails_dir / f"{file_hash}.jpg"
        return self.cache_dir / f"{file_hash}_{size}.jpg"
    
    def save_photo(self, media_id: str, data: bytes, size: str = 'medium', metadata: Optional[Dict] = None):
        """保存照片"""
        photo_path = self.get_photo_path(media_id, size)
        photo_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(photo_path, 'wb') as f:
            f.write(data)
        
        # 保存元数据
        if metadata:
            self._metadata[media_id] = {
                **metadata,
                'cached_at': datetime.now().isoformat(),
                'size': size
            }
            self._save_metadata()
    
    def get_photo(self, media_id: str, size: str = 'medium') -> Optional[bytes]:
        """获取照片"""
        photo_path = self.get_photo_path(media_id, size)
        if photo_path.exists():
            with open(photo_path, 'rb') as f:
                return f.read()
        return None
    
    def photo_exists(self, media_id: str, size: str = 'medium') -> bool:
        """检查照片是否存在"""
        return self.get_photo_path(media_id, size).exists()
    
    def get_metadata(self, media_id: str) -> Optional[Dict]:
        """获取元数据"""
        return self._metadata.get(media_id)
    
    def list_cached_photos(self) -> List[str]:
        """列出所有缓存的照片ID"""
        return list(self._metadata.keys())
    
    def get_cache_size(self) -> int:
        """获取缓存大小（字节）"""
        total_size = 0
        for path in [self.cache_dir, self.thumbnails_dir]:
            if path.exists():
                for file_path in path.rglob('*'):
                    if file_path.is_file():
                        total_size += file_path.stat().st_size
        return total_size
    
    def cleanup_cache(self, max_size_gb: Optional[int] = None):
        """清理缓存"""
        if max_size_gb is None:
            max_size_gb = self.config.get('google.max_cache_gb', 2)
        
        max_size_bytes = max_size_gb * 1024 * 1024 * 1024
        current_size = self.get_cache_size()
        
        if current_size <= max_size_bytes:
            return
        
        # 按访问时间排序，删除最旧的
        # 这里简化处理，删除所有缓存后重新同步
        # 实际应该实现LRU策略
        photos_to_remove = []
        for media_id in self._metadata.keys():
            photo_path = self.get_photo_path(media_id, 'medium')
            if photo_path.exists():
                photos_to_remove.append((media_id, photo_path.stat().st_mtime))
        
        # 按修改时间排序
        photos_to_remove.sort(key=lambda x: x[1])
        
        # 删除最旧的照片直到满足大小要求
        for media_id, _ in photos_to_remove:
            if current_size <= max_size_bytes:
                break
            
            # 删除所有尺寸的照片
            for size in ['thumbnail', 'small', 'medium', 'large']:
                photo_path = self.get_photo_path(media_id, size)
                if photo_path.exists():
                    current_size -= photo_path.stat().st_size
                    photo_path.unlink()
            
            # 删除元数据
            if media_id in self._metadata:
                del self._metadata[media_id]
        
        self._save_metadata()
    
    def clear_cache(self):
        """清空所有缓存"""
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
        if self.thumbnails_dir.exists():
            shutil.rmtree(self.thumbnails_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.thumbnails_dir.mkdir(parents=True, exist_ok=True)
        self._metadata = {}
        self._save_metadata()
