#!/usr/bin/env python3
"""应用启动脚本"""
import uvicorn
from app.main import app, get_config

if __name__ == "__main__":
    config = get_config()
    
    host = config.get('server.host', '0.0.0.0')
    port = config.get('server.port', 8000)
    reload = config.get('server.reload', False)
    
    # 启动定时任务
    from app.services.scheduler import SchedulerService
    scheduler = SchedulerService(config)
    scheduler.start()
    
    try:
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )
    finally:
        scheduler.stop()
