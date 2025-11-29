import os
import json
import shutil
import uuid
import logging
import random
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from fastapi import UploadFile

from ..core.config import Config
from .library_service import LibraryService

logger = logging.getLogger(__name__)

class AlbumService:
    def __init__(self, config: Config, library_service: LibraryService):
        self.config = config
        self.albums_dir = config.albums_dir
        self.library_service = library_service
        
        self.albums_dir.mkdir(parents=True, exist_ok=True)
        
        # 启动时尝试迁移旧数据
        self.library_service.migrate_legacy_data(self)

    def create_album(self, name: str, description: str = "") -> Dict:
        """创建新相册"""
        album_id = str(uuid.uuid4())
        album_path = self.albums_dir / album_id
        album_path.mkdir(exist_ok=True)
        
        metadata = {
            "id": album_id,
            "name": name,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "photo_count": 0,
            "cover_photo": None,
            "photo_ids": [] # 引用 Library 中的 photo_id
        }
        
        self._save_metadata(album_id, metadata)
        return metadata

    def list_albums(self) -> List[Dict]:
        """列出所有相册"""
        albums = []
        active_albums = self.config.get("albums.active_albums", []) or []
        
        for album_dir in self.albums_dir.iterdir():
            if album_dir.is_dir():
                metadata = self._load_metadata(album_dir.name)
                if metadata:
                    # 兼容性处理：如果没有 photo_ids 字段，初始化为空
                    if "photo_ids" not in metadata:
                        metadata["photo_ids"] = []
                        self._save_metadata(album_dir.name, metadata)
                    
                    metadata["photo_count"] = len(metadata["photo_ids"])
                    metadata["active"] = metadata["id"] in active_albums
                    
                    # 确保 cover_photo 有效性 (如果引用不存在了，清空或换一个)
                    # 这里暂不做复杂校验，只在 get_photos 时处理
                    
                    albums.append(metadata)
        
        albums.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return albums

    def get_album(self, album_id: str) -> Optional[Dict]:
        """获取相册详情"""
        return self._load_metadata(album_id)

    def delete_album(self, album_id: str):
        """删除相册 (仅删除逻辑容器，不删除照片)"""
        album_path = self.albums_dir / album_id
        if album_path.exists():
            shutil.rmtree(album_path)
            
        # 从激活列表中移除
        active_albums = self.config.get("albums.active_albums", []) or []
        if album_id in active_albums:
            active_albums.remove(album_id)
            self.config.set("albums.active_albums", active_albums)
            self.config.save()

    def update_album(self, album_id: str, name: str = None, description: str = None, active: bool = None):
        """更新相册信息"""
        metadata = self._load_metadata(album_id)
        if not metadata: return None
            
        if name is not None: metadata["name"] = name
        if description is not None: metadata["description"] = description
            
        metadata["updated_at"] = datetime.now().isoformat()
        self._save_metadata(album_id, metadata)
        
        if active is not None:
            active_albums = self.config.get("albums.active_albums", []) or []
            if active and album_id not in active_albums:
                active_albums.append(album_id)
            elif not active and album_id in active_albums:
                active_albums.remove(album_id)
            self.config.set("albums.active_albums", active_albums)
            self.config.save()
            
        return metadata

    def add_photos(self, album_id: str, photo_ids: List[str]):
        """添加照片到相册"""
        metadata = self._load_metadata(album_id)
        if not metadata: return
        
        current_ids = set(metadata.get("photo_ids", []))
        for pid in photo_ids:
            current_ids.add(pid)
            
        metadata["photo_ids"] = list(current_ids)
        metadata["photo_count"] = len(metadata["photo_ids"])
        
        # 自动设置封面
        if not metadata.get("cover_photo") and metadata["photo_ids"]:
             # 获取第一张照片的文件名作为封面
             first_pid = metadata["photo_ids"][0]
             photo = self.library_service.get_photo(first_pid)
             if photo:
                 metadata["cover_photo"] = photo["filename"]
                 
        self._save_metadata(album_id, metadata)

    def remove_photos(self, album_id: str, photo_ids: List[str]):
        """从相册移除照片"""
        metadata = self._load_metadata(album_id)
        if not metadata: return
        
        current_ids = metadata.get("photo_ids", [])
        metadata["photo_ids"] = [pid for pid in current_ids if pid not in photo_ids]
        metadata["photo_count"] = len(metadata["photo_ids"])
        
        # 如果封面被移除，重置
        # 注意：cover_photo 存的是 filename，不是 id，这有点不方便
        # 我们先检查 photo_ids 里还有没有对应的 filename
        # 或者我们以后把 cover_photo 改为存 ID，但前端可能要改
        # 暂时：如果封面文件名对应的 ID 被移除了？
        # 简化处理：如果列表空了，清除封面；否则如果不匹配任何现有照片，换一个
        if not metadata["photo_ids"]:
            metadata["cover_photo"] = None
        else:
            # 检查现有封面是否还在
            current_cover = metadata.get("cover_photo")
            cover_still_exists = False
            if current_cover:
                for pid in metadata["photo_ids"]:
                    p = self.library_service.get_photo(pid)
                    if p and p["filename"] == current_cover:
                        cover_still_exists = True
                        break
            
            if not cover_still_exists:
                # 找个新的
                first_pid = metadata["photo_ids"][0]
                photo = self.library_service.get_photo(first_pid)
                if photo: metadata["cover_photo"] = photo["filename"]

        self._save_metadata(album_id, metadata)

    def get_photos(self, album_id: str) -> List[Dict]:
        """获取相册照片详情"""
        metadata = self._load_metadata(album_id)
        if not metadata: return []
        
        photo_ids = metadata.get("photo_ids", [])
        photos = []
        for pid in photo_ids:
            p = self.library_service.get_photo(pid)
            if p:
                photos.append(p)
            else:
                # 数据不一致，ID存在但库里没了（可能是库里删了）
                # 暂时忽略，下次 save 时清理？
                pass
                
        photos.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return photos

    def get_all_active_photos(self) -> List[Dict]:
        """获取所有激活相册的照片（用于轮播）"""
        active_albums = self.config.get("albums.active_albums", []) or []
        all_photos = []
        seen_ids = set()
        
        for album_id in active_albums:
            metadata = self._load_metadata(album_id)
            if not metadata: continue
            
            photo_ids = metadata.get("photo_ids", [])
            for pid in photo_ids:
                if pid in seen_ids: continue
                seen_ids.add(pid)
                
                p = self.library_service.get_photo(pid)
                if p:
                    # 注入相册名 (如果有多个相册，这里只会显示第一个遇到的)
                    # 为了轮播显示，复制一份避免污染缓存
                    p_copy = p.copy()
                    p_copy["album_name"] = metadata["name"]
                    all_photos.append(p_copy)
        
        order = self.config.get("ui.slideshow_order", "shuffle")
        if order == "shuffle":
            random.shuffle(all_photos)
        else:
            all_photos.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            
        return all_photos

    def _load_metadata(self, album_id: str) -> Optional[Dict]:
        meta_path = self.albums_dir / album_id / "metadata.json"
        if meta_path.exists():
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except: return None
        return None

    def _save_metadata(self, album_id: str, metadata: Dict):
        meta_path = self.albums_dir / album_id / "metadata.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
