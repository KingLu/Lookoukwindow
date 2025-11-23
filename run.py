#!/usr/bin/env python3
"""应用启动脚本"""
import uvicorn
from app.main import app, get_config

if __name__ == "__main__":
    config = get_config()
    
    host = config.get('server.host', '0.0.0.0')
    port = config.get('server.port', 8000)
    reload = config.get('server.reload', False)
    
    # 不再需要定时任务，因为改为本地相册管理
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )
