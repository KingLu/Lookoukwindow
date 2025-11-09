"""认证API路由"""
import logging
from fastapi import APIRouter, Request, Response, HTTPException, status, Depends
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from ..core.config import Config
from ..core.auth import AuthManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    password: str


class PasswordSetRequest(BaseModel):
    password: str


class PasswordResetRequest(BaseModel):
    old_password: str
    new_password: str


def get_config() -> Config:
    """获取配置"""
    return Config()


@router.post("/login")
async def login(
    request: Request,
    response: Response,
    login_data: LoginRequest,
    config: Config = Depends(get_config)
):
    """登录"""
    client_ip = request.client.host if request.client else "unknown"
    password_length = len(login_data.password)
    
    logger.info(f"[登录尝试] IP: {client_ip}, 密码长度: {password_length}")
    
    if not config.is_password_set():
        logger.warning(f"[登录失败] IP: {client_ip}, 原因: 密码未设置")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先设置密码"
        )
    
    # 检查密码hash是否存在
    password_hash = config.get('security.login_password_hash')
    has_plain_password = bool(config.get('security.login_password'))
    
    logger.debug(f"[密码验证] IP: {client_ip}, hash存在: {bool(password_hash)}, 明文密码存在: {has_plain_password}")
    
    if not config.verify_password(login_data.password):
        logger.warning(f"[登录失败] IP: {client_ip}, 原因: 密码错误")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="密码错误"
        )
    
    logger.info(f"[登录成功] IP: {client_ip}")
    
    auth_manager = AuthManager(config)
    access_token = auth_manager.create_access_token({"sub": "user"})
    
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,  # 局域网环境，不使用HTTPS
        samesite="lax",
        max_age=60 * 60 * 24 * 7  # 7天
    )
    
    return {"status": "success", "message": "登录成功"}


@router.post("/logout")
async def logout(response: Response):
    """登出"""
    response.delete_cookie(key="access_token")
    return {"status": "success", "message": "已登出"}


@router.get("/check")
async def check_auth(request: Request, config: Config = Depends(get_config)):
    """检查认证状态"""
    
    auth_manager = AuthManager(config)
    is_authenticated = await auth_manager.get_current_user(request)
    is_password_set = config.is_password_set()
    
    return {
        "authenticated": is_authenticated,
        "password_set": is_password_set
    }


@router.post("/set-password")
async def set_password(
    request: Request,
    password_data: PasswordSetRequest,
    config: Config = Depends(get_config)
):
    """设置密码（首次设置或重置）"""
    client_ip = request.client.host if request.client else "unknown"
    password_length = len(password_data.password)
    password_bytes = len(password_data.password.encode('utf-8'))
    
    logger.info(f"[设置密码] IP: {client_ip}, 密码长度: {password_length} 字符, {password_bytes} 字节")
    
    # 检查是否已设置密码
    is_password_set = config.is_password_set()
    logger.debug(f"[设置密码] IP: {client_ip}, 当前密码已设置: {is_password_set}")
    
    if is_password_set:
        # 如果已设置密码，需要先登录才能修改
        auth_manager = AuthManager(config)
        is_authenticated = await auth_manager.get_current_user(request)
        if not is_authenticated:
            logger.warning(f"[设置密码失败] IP: {client_ip}, 原因: 需要登录才能修改密码")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="密码已设置，请先登录后再修改密码，或使用重置密码脚本"
            )
    
    # 验证密码长度
    if password_bytes > 72:
        logger.warning(f"[设置密码失败] IP: {client_ip}, 原因: 密码长度超过72字节")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="密码长度不能超过72字节（约24个中文字符或72个英文字符）"
        )
    
    try:
        config.set_password(password_data.password)
        logger.info(f"[设置密码成功] IP: {client_ip}")
        return {"status": "success", "message": "密码设置成功"}
    except ValueError as e:
        logger.error(f"[设置密码失败] IP: {client_ip}, 错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/reset-password")
async def reset_password(
    request: Request,
    reset_data: PasswordResetRequest,
    config: Config = Depends(get_config)
):
    """重置密码（需要提供旧密码）"""
    client_ip = request.client.host if request.client else "unknown"
    
    logger.info(f"[重置密码] IP: {client_ip}")
    
    # 验证旧密码
    if not config.verify_password(reset_data.old_password):
        logger.warning(f"[重置密码失败] IP: {client_ip}, 原因: 旧密码错误")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="旧密码错误"
        )
    
    # 验证新密码长度
    password_bytes = len(reset_data.new_password.encode('utf-8'))
    if password_bytes > 72:
        logger.warning(f"[重置密码失败] IP: {client_ip}, 原因: 新密码长度超过72字节")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="密码长度不能超过72字节（约24个中文字符或72个英文字符）"
        )
    
    try:
        config.set_password(reset_data.new_password)
        logger.info(f"[重置密码成功] IP: {client_ip}")
        return {"status": "success", "message": "密码重置成功"}
    except ValueError as e:
        logger.error(f"[重置密码失败] IP: {client_ip}, 错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
