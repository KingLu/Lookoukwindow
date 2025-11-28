import os
import json
import shutil
import uuid
import logging
import random
import math
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from PIL import Image, ExifTags
from fastapi import UploadFile
from geopy.geocoders import Nominatim

from ..core.config import Config

logger = logging.getLogger(__name__)

class AlbumService:
    def __init__(self, config: Config):
        self.config = config
        self.albums_dir = config.albums_dir
        self.thumbnails_dir = config.thumbnails_dir
        
        # 确保目录存在
        self.albums_dir.mkdir(parents=True, exist_ok=True)
        self.thumbnails_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化地理位置解析器
        self.geolocator = Nominatim(user_agent="lookoukwindow")

    def create_album(self, name: str, description: str = "") -> Dict:
        """创建新相册"""
        album_id = str(uuid.uuid4())
        album_path = self.albums_dir / album_id
        album_path.mkdir()
        
        metadata = {
            "id": album_id,
            "name": name,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        self._save_metadata(album_id, metadata)
        return metadata

    def list_albums(self) -> List[Dict]:
        """列出所有相册"""
        albums = []
        # 确保 active_albums 始终是列表
        active_albums = self.config.get("albums.active_albums", []) or []
        
        for album_dir in self.albums_dir.iterdir():
            if album_dir.is_dir():
                metadata = self._load_metadata(album_dir.name)
                if metadata:
                    # 统计照片数量
                    photos = list(album_dir.glob("*"))
                    photo_count = len([p for p in photos if p.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp', '.mp4', '.mov']])
                    
                    metadata["photo_count"] = photo_count
                    metadata["active"] = metadata["id"] in active_albums
                    
                    # 获取封面图（第一张照片）
                    if photo_count > 0:
                        # 优先找图片作为封面
                        first_photo = next((p for p in photos if p.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']), None)
                        # 如果没有图片，尝试找视频（暂无缩略图）
                        if not first_photo:
                            first_photo = next((p for p in photos if p.suffix.lower() in ['.mp4', '.mov']), None)
                            
                        if first_photo:
                            metadata["cover_photo"] = first_photo.name
                    
                    albums.append(metadata)
        
        # 按创建时间倒序
        albums.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return albums

    def get_album(self, album_id: str) -> Optional[Dict]:
        """获取相册详情"""
        return self._load_metadata(album_id)

    def delete_album(self, album_id: str):
        """删除相册"""
        album_path = self.albums_dir / album_id
        if album_path.exists():
            shutil.rmtree(album_path)
            
        # 清理缩略图
        thumb_path = self.thumbnails_dir / album_id
        if thumb_path.exists():
            shutil.rmtree(thumb_path)
            
        # 从激活列表中移除
        active_albums = self.config.get("albums.active_albums", []) or []
        if album_id in active_albums:
            active_albums.remove(album_id)
            self.config.set("albums.active_albums", active_albums)
            self.config.save()

    def update_album(self, album_id: str, name: str = None, description: str = None, active: bool = None):
        """更新相册信息"""
        metadata = self._load_metadata(album_id)
        if not metadata:
            return None
            
        if name is not None:
            metadata["name"] = name
        if description is not None:
            metadata["description"] = description
            
        metadata["updated_at"] = datetime.now().isoformat()
        self._save_metadata(album_id, metadata)
        
        # 更新激活状态
        if active is not None:
            active_albums = self.config.get("albums.active_albums", []) or []
            if active and album_id not in active_albums:
                active_albums.append(album_id)
            elif not active and album_id in active_albums:
                active_albums.remove(album_id)
            self.config.set("albums.active_albums", active_albums)
            self.config.save()
            
        return metadata

    async def upload_photo(self, album_id: str, file: UploadFile) -> Dict:
        """上传照片或视频"""
        album_path = self.albums_dir / album_id
        if not album_path.exists():
            raise ValueError("相册不存在")
            
        # 生成安全的文件名
        ext = Path(file.filename).suffix.lower()
        if not ext:
            ext = ".jpg"
            
        # 简单的后缀检查
        if ext not in ['.jpg', '.jpeg', '.png', '.webp', '.mp4', '.mov']:
             # 默认处理，或者报错
             pass

        photo_id = str(uuid.uuid4())
        filename = f"{photo_id}{ext}"
        file_path = album_path / filename
        
        # 保存文件
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
            
        # 生成缩略图 (仅图片)
        if ext in ['.jpg', '.jpeg', '.png', '.webp']:
            self._generate_thumbnail(album_id, filename)
        
        return {
            "id": photo_id,
            "filename": filename,
            "url": f"/api/albums/{album_id}/photos/{filename}",
            "thumbnail_url": f"/api/albums/{album_id}/photos/{filename}/thumbnail" if ext in ['.jpg', '.jpeg', '.png', '.webp'] else None
        }

    def get_photos(self, album_id: str) -> List[Dict]:
        """获取相册内的照片/视频列表"""
        album_path = self.albums_dir / album_id
        if not album_path.exists():
            return []
            
        photos = []
        valid_exts = ['.jpg', '.jpeg', '.png', '.webp', '.mp4', '.mov']
        
        for file_path in album_path.glob("*"):
            suffix = file_path.suffix.lower()
            if suffix in valid_exts:
                stat = file_path.stat()
                is_video = suffix in ['.mp4', '.mov']
                
                photo_data = {
                    "id": file_path.stem,
                    "filename": file_path.name,
                    "size": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "url": f"/api/albums/{album_id}/photos/{file_path.name}",
                    "type": "video" if is_video else "image",
                    "thumbnail_url": f"/api/albums/{album_id}/photos/{file_path.name}/thumbnail" if not is_video else None
                }
                
                # 提取EXIF信息 (仅图片)
                if not is_video:
                    exif = self._get_exif_data(file_path)
                    photo_data.update(exif)
                
                photos.append(photo_data)
        
        # 按创建时间倒序
        photos.sort(key=lambda x: x["created_at"], reverse=True)
        return photos

    def delete_photo(self, album_id: str, filename: str):
        """删除照片"""
        # 删除原图
        photo_path = self.albums_dir / album_id / filename
        if photo_path.exists():
            photo_path.unlink()
            
        # 删除缩略图
        thumb_path = self.thumbnails_dir / album_id / filename
        if thumb_path.exists():
            thumb_path.unlink()

    def get_all_active_photos(self) -> List[Dict]:
        """获取所有激活相册的照片（用于轮播）"""
        active_albums = self.config.get("albums.active_albums", []) or []
        all_photos = []
        
        for album_id in active_albums:
            album = self.get_album(album_id)
            if not album:
                continue
                
            photos = self.get_photos(album_id)
            for p in photos:
                p["album_name"] = album["name"]
                all_photos.append(p)
                
        # 获取播放顺序配置，默认乱序
        order = self.config.get("ui.slideshow_order", "shuffle")
        
        if order == "shuffle":
            random.shuffle(all_photos)
        else:
            # 按时间倒序
            all_photos.sort(key=lambda x: x["created_at"], reverse=True)
            
        return all_photos

    def _load_metadata(self, album_id: str) -> Optional[Dict]:
        """读取元数据"""
        meta_path = self.albums_dir / album_id / "metadata.json"
        if meta_path.exists():
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return None
        return None

    def _save_metadata(self, album_id: str, metadata: Dict):
        """保存元数据"""
        meta_path = self.albums_dir / album_id / "metadata.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

    def _generate_thumbnail(self, album_id: str, filename: str):
        """生成缩略图"""
        original_path = self.albums_dir / album_id / filename
        thumb_dir = self.thumbnails_dir / album_id
        thumb_dir.mkdir(parents=True, exist_ok=True)
        thumb_path = thumb_dir / filename
        
        try:
            with Image.open(original_path) as img:
                # 转换为RGB（防止PNG透明背景变黑）
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                
                # 保持比例缩放，最大边长 400
                img.thumbnail((400, 400))
                img.save(thumb_path, "JPEG", quality=85)
        except Exception as e:
            logger.error(f"生成缩略图失败 {filename}: {e}")

    def _convert_to_degrees(self, value):
        """将 GPS 坐标 (度, 分, 秒) 转换为十进制格式"""
        d, m, s = value
        return d + (m / 60.0) + (s / 3600.0)

    def _get_location_name(self, lat, lon):
        """通过逆地理编码获取位置名称"""
        try:
            location = self.geolocator.reverse(f"{lat}, {lon}", language='zh-CN')
            if location:
                address = location.raw.get('address', {})
                city = address.get('city', '')
                state = address.get('state', '')
                district = address.get('district', '')
                
                # 优先显示 市/区，或者 省/市
                if city and district:
                    return f"{city}{district}"
                elif state and city:
                    return f"{state}{city}"
                elif state:
                    return state
                elif city:
                    return city
                else:
                    return location.address.split(',')[0] # fallback
        except Exception as e:
            logger.error(f"逆地理编码失败: {e}")
        return None

    def _get_exif_data(self, file_path: Path) -> Dict:
        """提取EXIF信息"""
        exif_info = {}
        try:
            with Image.open(file_path) as img:
                if hasattr(img, '_getexif'):
                    exif = img._getexif()
                    if exif:
                        gps_info = {}
                        for tag, value in exif.items():
                            decoded = ExifTags.TAGS.get(tag, tag)
                            if decoded == "DateTimeOriginal":
                                # 格式化日期
                                try:
                                    dt = datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
                                    exif_info["date_taken"] = dt.isoformat()
                                except:
                                    exif_info["date_taken"] = value
                            elif decoded == "Make":
                                exif_info["make"] = str(value).strip()
                            elif decoded == "Model":
                                exif_info["model"] = str(value).strip()
                            elif decoded == "GPSInfo":
                                gps_info = value
                        
                        # 解析 GPS 信息
                        if gps_info:
                            try:
                                # GPSLatitudeRef: 'N' or 'S'
                                # GPSLatitude: ((deg, 1), (min, 1), (sec, 100))
                                # GPSLongitudeRef: 'E' or 'W'
                                # GPSLongitude: ((deg, 1), (min, 1), (sec, 100))
                                
                                lat_ref = gps_info.get(1)
                                lat = gps_info.get(2)
                                lon_ref = gps_info.get(3)
                                lon = gps_info.get(4)
                                
                                if lat and lon and lat_ref and lon_ref:
                                    lat_val = self._convert_to_degrees(lat)
                                    if lat_ref != 'N':
                                        lat_val = -lat_val
                                        
                                    lon_val = self._convert_to_degrees(lon)
                                    if lon_ref != 'E':
                                        lon_val = -lon_val
                                        
                                    exif_info["location"] = {
                                        "lat": lat_val,
                                        "lon": lon_val
                                    }
                                    exif_info["has_location"] = True
                                    
                                    # 获取位置名称
                                    location_name = self._get_location_name(lat_val, lon_val)
                                    if location_name:
                                        exif_info["location_name"] = location_name

                            except Exception as e:
                                logger.error(f"GPS 解析失败: {e}")
                                pass

        except Exception:
            pass
        return exif_info
