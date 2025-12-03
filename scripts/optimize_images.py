#!/usr/bin/env python3
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.core.config import Config
from app.services.library_service import LibraryService
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    logger.info("开始优化图片库...")
    
    config = Config()
    service = LibraryService(config)
    
    photos = service.get_photos()
    total = len(photos)
    logger.info(f"共发现 {total} 张图片")
    
    count = 0
    for photo in photos:
        if photo["type"] != "image":
            continue
            
        filename = photo["filename"]
        original_path = service.library_dir / filename
        
        if not original_path.exists():
            logger.warning(f"原图不存在: {filename}")
            continue
            
        # 强制重新生成衍生图
        try:
            # 删除旧的 web image (如果存在)
            web_path = service.web_images_dir / filename
            if web_path.exists():
                web_path.unlink()
                
            # 调用生成方法 (会自动生成 web 和 thumbnail)
            # 注意：LibraryService._generate_derivatives 是内部方法，但我们可以调用
            service._generate_derivatives(original_path, photo["id"])
            
            count += 1
            if count % 10 == 0:
                logger.info(f"已处理 {count}/{total}...")
                
        except Exception as e:
            logger.error(f"处理图片 {filename} 失败: {e}")
            
    logger.info(f"优化完成! 共处理 {count} 张图片。")
    logger.info("请重启应用以确保更改生效。")

if __name__ == "__main__":
    main()

