"""配置管理模块"""
import os
import yaml
import secrets
import logging
from pathlib import Path
from typing import Dict, List, Optional
from pydantic_settings import BaseSettings
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
logger = logging.getLogger(__name__)


class Config:
    """配置管理类"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._get_default_config_path()
        self.config_dir = Path(self.config_path).parent
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载配置
        self._config = self._load_config()
        
        # 确保必要的目录存在
        self._ensure_directories()
        
        # 确保安全配置
        self._ensure_security()
    
    def _get_default_config_path(self) -> str:
        """获取默认配置文件路径"""
        config_dir = Path.home() / ".local" / "share" / "lookoukwindow"
        config_dir.mkdir(parents=True, exist_ok=True)
        return str(config_dir / "config.yaml")
    
    def _load_config(self) -> Dict:
        """加载配置文件"""
        config_path = Path(self.config_path)
        
        # 如果配置文件不存在，从示例文件创建
        if not config_path.exists():
            example_path = Path(__file__).parent.parent.parent / "config.yaml.example"
            if example_path.exists():
                import shutil
                shutil.copy(example_path, config_path)
                print(f"已创建配置文件: {config_path}")
            else:
                # 创建默认配置
                self._create_default_config(config_path)
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
        
        return config
    
    def _create_default_config(self, config_path: Path):
        """创建默认配置"""
        default_config = {
            'youtube': {
                'presets': [
                    # ISS 4K 地球和太空直播（支持嵌入）
                    {'name': 'NASA TV', 'url': 'https://www.youtube.com/embed/fO9e9jnhYK8', 'channel_id': 'UCLA_DiR1FfKNvjuUpBHmylQ'},
                    {'name': 'ISS Live', 'url': 'https://www.youtube.com/embed/fO9e9jnhYK8', 'channel_id': 'UCLA_DiR1FfKNvjuUpBHmylQ'},
                    {'name': 'NASA Live', 'url': 'https://www.youtube.com/embed/fO9e9jnhYK8', 'channel_id': 'UCLA_DiR1FfKNvjuUpBHmylQ'},
                    # 备用：频道直播流方式
                    {'name': 'NASA Live Stream', 'url': 'https://www.youtube.com/embed/live_stream?channel=UCLA_DiR1FfKNvjuUpBHmylQ', 'channel_id': 'UCLA_DiR1FfKNvjuUpBHmylQ'}
                ],
                'custom_channels': [],
                'default_channel': 'NASA TV'
            },
            'google': {
                'album_id': '',
                'sync_interval_minutes': 60,
                'max_cache_gb': 2
            },
            'ui': {
                'layout': 'side-by-side',
                'slideshow_interval_seconds': 10,
                'show_metadata': True,
                'language': 'zh-CN',
                'timezone': 'Asia/Shanghai'
            },
            'display': {
                'kiosk': True,
                'screen_rotation': 'normal',
                'scale': 1.0
            },
            'security': {
                'login_password': '',
                'session_secret': secrets.token_urlsafe(32),
                'lan_subnet_allowlist': []
            },
            'paths': {
                'cache_dir': '~/.local/share/lookoukwindow/cache',
                'tokens_dir': '~/.local/share/lookoukwindow/tokens',
                'config_dir': '~/.local/share/lookoukwindow'
            },
            'server': {
                'host': '0.0.0.0',
                'port': 8000,
                'reload': False
            }
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(default_config, f, allow_unicode=True, default_flow_style=False)
    
    def _ensure_directories(self):
        """确保必要的目录存在"""
        cache_dir = Path(self.get('paths.cache_dir', '~/.local/share/lookoukwindow/cache')).expanduser()
        tokens_dir = Path(self.get('paths.tokens_dir', '~/.local/share/lookoukwindow/tokens')).expanduser()
        
        cache_dir.mkdir(parents=True, exist_ok=True)
        tokens_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建照片缓存子目录
        (cache_dir / 'photos').mkdir(parents=True, exist_ok=True)
        (cache_dir / 'thumbnails').mkdir(parents=True, exist_ok=True)
    
    def _ensure_security(self):
        """确保安全配置"""
        if not self.get('security.session_secret'):
            self.set('security.session_secret', secrets.token_urlsafe(32))
            self.save()
    
    def get(self, key: str, default=None):
        """获取配置值，支持点号分隔的嵌套键"""
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        return value
    
    def set(self, key: str, value):
        """设置配置值，支持点号分隔的嵌套键"""
        keys = key.split('.')
        config = self._config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
    
    def save(self):
        """保存配置到文件"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self._config, f, allow_unicode=True, default_flow_style=False)
    
    def verify_password(self, plain_password: str) -> bool:
        """验证密码"""
        password_hash = self.get('security.login_password_hash')
        if not password_hash:
            # 如果还没有设置密码，使用明文密码（首次设置）
            plain = self.get('security.login_password', '')
            if plain:
                result = plain_password == plain
                logger.debug(f"[密码验证] 使用明文密码比较, 结果: {result}")
                return result
            logger.debug("[密码验证] 未找到密码hash和明文密码")
            return False
        
        try:
            result = pwd_context.verify(plain_password, password_hash)
            logger.debug(f"[密码验证] 使用bcrypt验证, 结果: {result}")
            return result
        except Exception as e:
            logger.error(f"[密码验证] bcrypt验证出错: {str(e)}")
            return False
    
    def set_password(self, plain_password: str, clear_old: bool = True):
        """设置密码（会自动hash）
        
        Args:
            plain_password: 明文密码
            clear_old: 是否清除旧的明文密码（默认True）
        """
        # bcrypt 限制密码长度不超过72字节
        password_bytes = len(plain_password.encode('utf-8'))
        if password_bytes > 72:
            logger.error(f"[设置密码] 密码长度超过限制: {password_bytes} 字节")
            raise ValueError("密码长度不能超过72字节")
        
        logger.debug(f"[设置密码] 开始生成密码hash, 密码长度: {password_bytes} 字节")
        password_hash = pwd_context.hash(plain_password)
        logger.debug(f"[设置密码] 密码hash生成成功, hash长度: {len(password_hash)}")
        
        self.set('security.login_password_hash', password_hash)
        # 清除明文密码
        if clear_old and self.get('security.login_password'):
            logger.debug("[设置密码] 清除旧明文密码")
            self.set('security.login_password', '')
        self.save()
        logger.info("[设置密码] 密码已保存到配置文件")
    
    def is_password_set(self) -> bool:
        """检查是否已设置密码"""
        return bool(self.get('security.login_password_hash') or self.get('security.login_password'))
    
    @property
    def cache_dir(self) -> Path:
        """获取缓存目录"""
        return Path(self.get('paths.cache_dir', '~/.local/share/lookoukwindow/cache')).expanduser()
    
    @property
    def tokens_dir(self) -> Path:
        """获取tokens目录"""
        return Path(self.get('paths.tokens_dir', '~/.local/share/lookoukwindow/tokens')).expanduser()
    
    @property
    def session_secret(self) -> str:
        """获取会话密钥"""
        return self.get('security.session_secret', secrets.token_urlsafe(32))
