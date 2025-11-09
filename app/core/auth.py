"""认证模块"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .config import Config


class AuthManager:
    """认证管理器"""
    
    def __init__(self, config: Config):
        self.config = config
        self.security = HTTPBearer(auto_error=False)
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 60 * 24 * 7  # 7天
    
    def create_access_token(self, data: dict) -> str:
        """创建访问令牌"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.config.session_secret, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[dict]:
        """验证令牌"""
        try:
            payload = jwt.decode(token, self.config.session_secret, algorithms=[self.algorithm])
            return payload
        except JWTError:
            return None
    
    async def get_current_user(self, request: Request) -> bool:
        """获取当前用户（检查是否已登录）"""
        # 从cookie获取token
        token = request.cookies.get("access_token")
        if not token:
            # 尝试从Authorization header获取
            authorization: Optional[HTTPAuthorizationCredentials] = await self.security(request)
            if authorization:
                token = authorization.credentials
        
        if not token:
            return False
        
        payload = self.verify_token(token)
        if payload is None:
            return False
        
        return True
    
    def require_auth(self, request: Request):
        """要求认证的装饰器辅助函数"""
        # 这个函数会被中间件或依赖项调用
        pass


async def get_current_user(request: Request, config: Config) -> bool:
    """依赖项：获取当前用户"""
    auth_manager = AuthManager(config)
    return await auth_manager.get_current_user(request)
