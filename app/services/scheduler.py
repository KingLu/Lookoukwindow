"""定时任务调度服务"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import asyncio

from ..core.config import Config
from ..services.google_photos import GooglePhotosService
from ..services.photo_cache import PhotoCacheService


class SchedulerService:
    """定时任务服务"""
    
    def __init__(self, config: Config):
        self.config = config
        self.scheduler = AsyncIOScheduler()
        self.google_photos_service = None
        self.photo_cache_service = None
    
    def start(self):
        """启动调度器"""
        # 初始化服务
        self.google_photos_service = GooglePhotosService(self.config)
        self.photo_cache_service = PhotoCacheService(self.config)
        
        # 添加同步任务
        sync_interval = self.config.get('google.sync_interval_minutes', 60)
        self.scheduler.add_job(
            self.sync_photos_task,
            trigger=IntervalTrigger(minutes=sync_interval),
            id='sync_photos',
            replace_existing=True
        )
        
        self.scheduler.start()
        print(f"定时任务调度器已启动，照片同步间隔: {sync_interval} 分钟")
    
    def stop(self):
        """停止调度器"""
        self.scheduler.shutdown()
    
    async def sync_photos_task(self):
        """同步照片任务"""
        try:
            if not self.google_photos_service.is_authenticated():
                print("Google Photos 未授权，跳过同步")
                return
            
            album_id = self.config.get('google.album_id')
            if not album_id:
                print("未选择相册，跳过同步")
                return
            
            print("开始同步照片...")
            
            # 获取所有媒体项
            media_items = self.google_photos_service.get_all_album_media_items(album_id)
            print(f"找到 {len(media_items)} 个媒体项")
            
            # 下载并缓存照片
            downloaded = 0
            for item in media_items:
                media_id = item.get('id')
                if not media_id:
                    continue
                
                # 检查是否已缓存
                if self.photo_cache_service.photo_exists(media_id, 'medium'):
                    continue
                
                # 下载缩略图
                thumbnail_data = self.google_photos_service.download_media_item(item, 'thumbnail')
                if thumbnail_data:
                    self.photo_cache_service.save_photo(media_id, thumbnail_data, 'thumbnail')
                
                # 下载中等尺寸
                medium_data = self.google_photos_service.download_media_item(item, 'medium')
                if medium_data:
                    metadata = self.google_photos_service.get_media_item_metadata(item)
                    self.photo_cache_service.save_photo(media_id, medium_data, 'medium', metadata)
                    downloaded += 1
                
                # 每10张打印一次进度
                if downloaded % 10 == 0:
                    print(f"已下载 {downloaded} 张照片...")
            
            print(f"同步完成，新下载 {downloaded} 张照片")
            
            # 清理缓存
            self.photo_cache_service.cleanup_cache()
            
        except Exception as e:
            print(f"同步照片任务失败: {e}")
