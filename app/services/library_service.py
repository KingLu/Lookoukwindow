import json
import shutil
import uuid
import logging
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from PIL import Image, ExifTags
from fastapi import UploadFile
from geopy.geocoders import Nominatim

from ..core.config import Config

logger = logging.getLogger(__name__)

class LibraryService:
    def __init__(self, config: Config):
        self.config = config
        self.library_dir = config.library_dir
        self.index_path = config.library_index_path
        self.thumbnails_dir = config.thumbnails_dir
        self.web_images_dir = config.web_images_dir
        
        # 确保目录存在
        self.library_dir.mkdir(parents=True, exist_ok=True)
        self.thumbnails_dir.mkdir(parents=True, exist_ok=True)
        self.web_images_dir.mkdir(parents=True, exist_ok=True)
        
        self.geolocator = Nominatim(user_agent="lookoukwindow")
        
        # 内存缓存索引
        self._library_index = self._load_index()

    def _load_index(self) -> List[Dict]:
        if self.index_path.exists():
            try:
                with open(self.index_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载库索引失败: {e}")
                return []
        return []

    def _save_index(self):
        try:
            with open(self.index_path, "w", encoding="utf-8") as f:
                json.dump(self._library_index, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存库索引失败: {e}")

    def get_photos(self) -> List[Dict]:
        """获取所有照片"""
        # 按时间倒序
        return sorted(self._library_index, key=lambda x: x.get("created_at", ""), reverse=True)

    def get_photo(self, photo_id: str) -> Optional[Dict]:
        for p in self._library_index:
            if p["id"] == photo_id:
                return p
        return None

    async def upload_photo(self, file: UploadFile) -> Dict:
        """上传照片到库
        
        存储策略：
        - data/library: 存放用户上传的原始照片（不做任何压缩处理）
        - data/web_images: 存放压缩/优化后的展示版
        - data/thumbnails: 存放缩略图
        """
        original_content = await file.read()
        
        ext = Path(file.filename).suffix.lower()
        is_image = ext in ['.jpg', '.jpeg', '.png', '.webp']
        is_video = ext in ['.mp4', '.mov']
        
        # 1. 计算原始内容的 Hash 用于查重
        sha256_hash = hashlib.sha256(original_content).hexdigest()
        
        # 检查是否存在
        for p in self._library_index:
            if p.get("hash") == sha256_hash:
                logger.info(f"照片已存在 (Hash冲突): {file.filename}")
                return {"status": "duplicate", "photo": p}

        # 2. 保存原始文件到 library（不做任何处理）
        if not ext: ext = ".jpg"
        
        photo_id = str(uuid.uuid4())
        filename = f"{photo_id}{ext}"
        original_path = self.library_dir / filename
        
        with open(original_path, "wb") as f:
            f.write(original_content)
        
        logger.info(f"原图已保存: {original_path} ({len(original_content)/1024/1024:.2f}MB)")
            
        # 3. 生成衍生图（web优化版 + 缩略图）
        if not is_video:
            self._generate_derivatives(original_path, photo_id)
            
        # 4. 解析元数据
        stat = original_path.stat()
        photo_data = {
            "id": photo_id,
            "filename": filename,
            "original_filename": file.filename,
            "size": stat.st_size,  # 原始文件大小
            "hash": sha256_hash,
            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "url": f"/api/library/photos/{filename}",
            "type": "video" if is_video else "image",
            "thumbnail_url": f"/api/library/photos/{filename}/thumbnail" if not is_video else None,
            "web_url": f"/api/library/photos/{filename}/web" if not is_video else None
        }
        
        if not is_video:
            exif = self._get_exif_data(original_path)
            photo_data.update(exif)
            
        # 5. 更新索引
        self._library_index.append(photo_data)
        self._save_index()
        
        return {"status": "success", "photo": photo_data}

    def update_photo(self, photo_id: str, updates: Dict) -> Optional[Dict]:
        """更新照片信息"""
        for p in self._library_index:
            if p["id"] == photo_id:
                p.update(updates)
                p["updated_at"] = datetime.now().isoformat()
                self._save_index()
                return p
        return None

    def rotate_photo(self, photo_id: str, degree: int) -> bool:
        """旋转照片（只修改展示版，不修改原图）
        
        原图保持不变，只旋转 web_images 和 thumbnails 中的展示版
        """
        photo = self.get_photo(photo_id)
        if not photo or photo["type"] != "image": return False
        
        filename = photo["filename"]
        original_path = self.library_dir / filename
        web_path = self.web_images_dir / filename
        thumb_path = self.thumbnails_dir / filename
        
        try:
            # 从原图重新生成旋转后的 web 版和缩略图
            with Image.open(original_path) as img:
                # 旋转（负数是顺时针，Pillow rotate 正数是逆时针）
                rotated = img.rotate(-degree, expand=True)
                
                if rotated.mode in ('RGBA', 'P'):
                    rotated = rotated.convert('RGB')
                
                # 生成 Web 优化图 (1280px)
                width, height = rotated.size
                if width > 1280 or height > 1280:
                    web_img = rotated.copy()
                    web_img.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
                    web_img.save(web_path, "JPEG", quality=75)
                else:
                    rotated.save(web_path, "JPEG", quality=75)
                
                # 生成缩略图 (400px)
                rotated.thumbnail((400, 400))
                rotated.save(thumb_path, "JPEG", quality=80)
            
            # 记录旋转角度（累计），方便后续可能的操作
            current_rotation = photo.get("rotation", 0)
            new_rotation = (current_rotation + degree) % 360
            self.update_photo(photo_id, {"rotation": new_rotation})
            
            logger.info(f"照片 {photo_id} 已旋转 {degree}° (总计 {new_rotation}°)")
            return True
        except Exception as e:
            logger.error(f"旋转失败: {e}")
            return False

    def delete_photo(self, photo_id: str):
        """删除照片"""
        logger.info(f"开始删除照片: {photo_id}")
        photo = self.get_photo(photo_id)
        if not photo: 
            logger.warning(f"删除失败: 图片ID {photo_id} 未在索引中找到")
            return
        
        # 删除物理文件
        filename = photo["filename"]
        
        def safe_delete(base_dir: Path, name: str, label: str):
            try:
                path = base_dir / name
                if path.exists():
                    path.unlink()
                    logger.info(f"[{label}] 已删除: {path}")
                else:
                    logger.warning(f"[{label}] 文件不存在: {path}")
            except Exception as e:
                logger.error(f"[{label}] 删除失败 {name}: {e}")

        safe_delete(self.library_dir, filename, "原图")
        safe_delete(self.thumbnails_dir, filename, "缩略图")
        safe_delete(self.web_images_dir, filename, "Web图")
        
        # 更新索引
        self._library_index = [p for p in self._library_index if p["id"] != photo_id]
        self._save_index()
        logger.info(f"照片 {photo_id} 已从索引移除")

    def _generate_derivatives(self, original_path: Path, photo_id: str):
        """生成缩略图和Web优化图
        
        从原图生成：
        - web_images: 1280px 压缩版（用于前端展示）
        - thumbnails: 400px 缩略图（用于列表预览）
        """
        filename = original_path.name
        
        thumb_path = self.thumbnails_dir / filename
        web_path = self.web_images_dir / filename

        try:
            with Image.open(original_path) as img:
                original_size = img.size
                
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                
                # Web 优化图 (1280px - 适配树莓派)
                width, height = img.size
                if width > 1280 or height > 1280:
                    web_img = img.copy()
                    web_img.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
                    web_img.save(web_path, "JPEG", quality=75)
                    web_size = web_path.stat().st_size
                    logger.info(f"Web图已生成: {web_path.name} ({original_size[0]}x{original_size[1]} -> {web_img.size[0]}x{web_img.size[1]}, {web_size/1024:.1f}KB)")
                else:
                    img.save(web_path, "JPEG", quality=75)
                    web_size = web_path.stat().st_size
                    logger.info(f"Web图已生成: {web_path.name} (原尺寸, {web_size/1024:.1f}KB)")

                # 缩略图 (400px)
                img.thumbnail((400, 400))
                img.save(thumb_path, "JPEG", quality=80)
                thumb_size = thumb_path.stat().st_size
                logger.info(f"缩略图已生成: {thumb_path.name} ({img.size[0]}x{img.size[1]}, {thumb_size/1024:.1f}KB)")
                
        except Exception as e:
            logger.error(f"生成衍生图失败 {filename}: {e}")

    def _get_exif_data(self, file_path: Path) -> Dict:
        # 复用之前的 EXIF 逻辑，稍作简化
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
                                try:
                                    dt = datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
                                    exif_info["date_taken"] = dt.isoformat()
                                except:
                                    exif_info["date_taken"] = value
                            elif decoded == "GPSInfo":
                                gps_info = value
                            elif decoded in ["Make", "Model"]:
                                exif_info[decoded.lower()] = str(value).strip()
                        
                        if gps_info:
                            location = self._parse_gps(gps_info)
                            if location:
                                exif_info["location"] = location
                                exif_info["has_location"] = True
                                name = self._get_location_name(location["lat"], location["lon"])
                                if name: exif_info["location_name"] = name
        except: pass
        return exif_info

    def _parse_gps(self, gps_info):
        try:
            def convert(v): return v[0] + (v[1] / 60.0) + (v[2] / 3600.0)
            lat = convert(gps_info[2])
            if gps_info[1] != 'N': lat = -lat
            lon = convert(gps_info[4])
            if gps_info[3] != 'E': lon = -lon
            return {"lat": lat, "lon": lon}
        except: return None

    def _get_location_name(self, lat, lon):
        try:
            location = self.geolocator.reverse(f"{lat}, {lon}", language='zh-CN', timeout=2)
            if location:
                address = location.raw.get('address', {})
                parts = [address.get(k, '') for k in ['city', 'district', 'state']]
                return "".join([p for p in parts if p]) or location.address.split(',')[0]
        except: return None

    def migrate_legacy_data(self):
        """从旧的相册结构迁移到库结构"""
        if self._library_index:
            return # 已经有数据，假设已迁移

        logger.info("开始迁移旧数据到 Library...")
        albums_dir = self.config.albums_dir
        
        for album_dir in albums_dir.iterdir():
            if not album_dir.is_dir(): continue
            
            album_photo_ids = []
            
            # 遍历相册内的图片
            # 注意：因为要修改列表，最好先转 list
            for file_path in list(album_dir.glob("*")):
                if file_path.name in ["metadata.json", "photos.json"]: continue
                if file_path.suffix.lower() not in ['.jpg', '.jpeg', '.png', '.webp', '.mp4', '.mov']: continue
                
                # 移动到 library
                new_path = self.library_dir / file_path.name
                
                # 如果目标不存在，则移动
                if not new_path.exists():
                    shutil.move(str(file_path), str(new_path))
                
                # 构建 photo entry
                photo_id = file_path.stem
                ext = file_path.suffix.lower()
                is_video = ext in ['.mp4', '.mov']
                
                # 计算 Hash (如果是刚移动过来的)
                sha256_hash = ""
                if new_path.exists():
                    with open(new_path, "rb") as f:
                         sha256_hash = hashlib.sha256(f.read()).hexdigest()

                photo_data = {
                    "id": photo_id,
                    "filename": file_path.name,
                    "original_filename": file_path.name,
                    "hash": sha256_hash,
                    "size": new_path.stat().st_size,
                    "created_at": datetime.fromtimestamp(new_path.stat().st_ctime).isoformat(),
                    "url": f"/api/library/photos/{file_path.name}",
                    "type": "video" if is_video else "image",
                    "thumbnail_url": f"/api/library/photos/{file_path.name}/thumbnail" if not is_video else None,
                    "web_url": f"/api/library/photos/{file_path.name}/web" if not is_video else None
                }
                
                if not is_video:
                    exif = self._get_exif_data(new_path)
                    photo_data.update(exif)
                    
                    # 迁移衍生图 (thumbnails/album_id/file -> thumbnails/file)
                    old_thumb = self.thumbnails_dir / album_dir.name / file_path.name
                    new_thumb = self.thumbnails_dir / file_path.name
                    if old_thumb.exists():
                        # 如果目标不存在才移动，防止覆盖（虽然UUID应该唯一）
                        if not new_thumb.exists():
                             shutil.move(str(old_thumb), str(new_thumb))
                    elif not new_thumb.exists():
                        self._generate_derivatives(new_path, photo_id)
                        
                    old_web = self.web_images_dir / album_dir.name / file_path.name
                    new_web = self.web_images_dir / file_path.name
                    if old_web.exists():
                        if not new_web.exists():
                            shutil.move(str(old_web), str(new_web))
                    elif not new_web.exists():
                        self._generate_derivatives(new_path, photo_id)

                # 添加到全局索引
                # 避免重复添加 (不同相册可能有相同UUID的文件名? 理论上不应该，因为UUID是生成的)
                if not any(p['id'] == photo_id for p in self._library_index):
                    self._library_index.append(photo_data)
                
                album_photo_ids.append(photo_id)

            # 更新相册元数据，记录 photo_ids
            meta_path = album_dir / "metadata.json"
            if meta_path.exists():
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    meta["photo_ids"] = album_photo_ids
                    # 移除旧的 cover_photo 路径依赖? 
                    # cover_photo 存的是 filename，现在 filename 依然有效，只是位置变了
                    # 但 AlbumService 需要知道去哪里找封面。
                    # 暂时保持不变，AlbumService logic update to resolve cover from library
                    
                    with open(meta_path, "w", encoding="utf-8") as f:
                        json.dump(meta, f, ensure_ascii=False, indent=2)
                except: pass
            
            # 删除旧的 photos.json
            (album_dir / "photos.json").unlink(missing_ok=True)
            
            # 清理空的衍生图目录
            shutil.rmtree(self.thumbnails_dir / album_dir.name, ignore_errors=True)
            shutil.rmtree(self.web_images_dir / album_dir.name, ignore_errors=True)
        
        self._save_index()
        logger.info(f"迁移完成，共迁移 {len(self._library_index)} 张照片")
