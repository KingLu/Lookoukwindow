"""Google Photos 服务"""
import os
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import httpx
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..core.config import Config


class GooglePhotosService:
    """Google Photos 服务类"""
    
    SCOPES = ['https://www.googleapis.com/auth/photoslibrary.readonly']
    
    def __init__(self, config: Config):
        self.config = config
        self.credentials: Optional[Credentials] = None
        self.service = None
        self._load_credentials()
    
    def start_desktop_authorization(self) -> bool:
        """启动桌面应用本地回调授权（会在本机打开浏览器进行授权）"""
        try:
            # 注意：此方式会在运行该进程的机器上打开浏览器（通常是服务器本机）
            # 若服务器无图形界面，请改用“网页授权（备用）”
            client_secrets_path = self._get_client_secrets_path()
            if not client_secrets_path.exists():
                raise FileNotFoundError("未找到 client_secrets.json")
            
            flow = Flow.from_client_secrets_file(
                str(client_secrets_path),
                scopes=self.SCOPES
            )
            # 在本地随机端口启动回调服务器，并自动打开默认浏览器
            creds = flow.run_local_server(port=0)
            self.credentials = creds
            self._save_credentials()
            self.service = build('photoslibrary', 'v1', credentials=self.credentials, static_discovery=False)
            return True
        except Exception as e:
            print(f"桌面授权失败: {e}")
            return False

    def clear_credentials(self) -> bool:
        """清除已保存的授权凭据"""
        try:
            creds_path = self._get_credentials_path()
            if creds_path.exists():
                creds_path.unlink()
            self.credentials = None
            self.service = None
            return True
        except Exception as e:
            print(f"清除凭据失败: {e}")
            return False
    
    def _get_credentials_path(self) -> Path:
        """获取凭据文件路径"""
        return self.config.tokens_dir / "google_photos_token.json"
    
    def _get_client_secrets_path(self) -> Path:
        """获取客户端密钥文件路径"""
        return self.config.tokens_dir / "client_secrets.json"
    
    def _load_credentials(self):
        """加载凭据"""
        creds_path = self._get_credentials_path()
        if creds_path.exists():
            try:
                self.credentials = Credentials.from_authorized_user_file(str(creds_path), self.SCOPES)
                if self.credentials:
                    # 如果 token 过期，尝试刷新
                    if self.credentials.expired and self.credentials.refresh_token:
                        try:
                            self.credentials.refresh(Request())
                            self._save_credentials()
                        except Exception as e:
                            print(f"刷新凭据失败: {e}")
                            self.credentials = None
                            self.service = None
                            return
                    
                    # 验证凭据是否有效
                    if self.credentials.valid:
                        self.service = build('photoslibrary', 'v1', credentials=self.credentials, static_discovery=False)
                    else:
                        print("凭据无效")
                        self.credentials = None
                        self.service = None
            except Exception as e:
                print(f"加载凭据失败: {e}")
                self.credentials = None
                self.service = None
    
    def _save_credentials(self):
        """保存凭据"""
        if self.credentials:
            creds_path = self._get_credentials_path()
            with open(creds_path, 'w') as token:
                token.write(self.credentials.to_json())
    
    def is_authenticated(self) -> bool:
        """检查是否已认证"""
        return self.service is not None
    
    def get_authorization_url(self, redirect_uri: str) -> tuple[str, str]:
        """获取授权URL"""
        client_secrets_path = self._get_client_secrets_path()
        if not client_secrets_path.exists():
            raise FileNotFoundError("请先上传 client_secrets.json 文件")
        
        flow = Flow.from_client_secrets_file(
            str(client_secrets_path),
            scopes=self.SCOPES,
            redirect_uri=redirect_uri
        )
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        # 保存state
        state_path = self.config.tokens_dir / "oauth_state.txt"
        with open(state_path, 'w') as f:
            f.write(state)
        
        return authorization_url, state
    
    def handle_oauth_callback(self, code: str, redirect_uri: str, state: str) -> bool:
        """处理OAuth回调"""
        # 验证state
        state_path = self.config.tokens_dir / "oauth_state.txt"
        if state_path.exists():
            with open(state_path, 'r') as f:
                saved_state = f.read().strip()
            if saved_state != state:
                return False
        
        try:
            client_secrets_path = self._get_client_secrets_path()
            flow = Flow.from_client_secrets_file(
                str(client_secrets_path),
                scopes=self.SCOPES,
                redirect_uri=redirect_uri
            )
            flow.fetch_token(code=code)
            self.credentials = flow.credentials
            self._save_credentials()
            self.service = build('photoslibrary', 'v1', credentials=self.credentials, static_discovery=False)
            return True
        except Exception as e:
            print(f"OAuth回调处理失败: {e}")
            return False
    
    def list_albums(self) -> List[Dict]:
        """列出所有相册"""
        if not self.service:
            return []
        
        try:
            albums = []
            page_token = None
            
            while True:
                results = self.service.albums().list(
                    pageSize=50,
                    pageToken=page_token
                ).execute()
                
                items = results.get('albums', [])
                albums.extend(items)
                
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
            
            return albums
        except HttpError as e:
            # 不要吞掉错误，抛给上层以便返回明确的错误信息（如作用域不足）
            print(f"列出相册失败: {e}")
            raise
    
    def get_album_media_items(self, album_id: str, page_token: Optional[str] = None) -> tuple[List[Dict], Optional[str]]:
        """获取相册中的媒体项"""
        if not self.service:
            return [], None
        
        try:
            results = self.service.mediaItems().search(
                body={
                    'albumId': album_id,
                    'pageSize': 100,
                    'pageToken': page_token
                }
            ).execute()
            
            media_items = results.get('mediaItems', [])
            next_page_token = results.get('nextPageToken')
            
            return media_items, next_page_token
        except HttpError as e:
            print(f"获取相册媒体项失败: {e}")
            return [], None
    
    def get_all_album_media_items(self, album_id: str) -> List[Dict]:
        """获取相册中的所有媒体项"""
        all_items = []
        page_token = None
        
        while True:
            items, page_token = self.get_album_media_items(album_id, page_token)
            all_items.extend(items)
            
            if not page_token:
                break
        
        return all_items
    
    def download_media_item(self, media_item: Dict, size: str = 'medium') -> Optional[bytes]:
        """下载媒体项"""
        if not self.service:
            return None
        
        try:
            base_url = media_item.get('baseUrl', '')
            if not base_url:
                return None
            
            # 根据size选择URL参数
            url = f"{base_url}=w{self._get_size_width(size)}"
            
            response = httpx.get(url, timeout=30.0)
            if response.status_code == 200:
                return response.content
            return None
        except Exception as e:
            print(f"下载媒体项失败: {e}")
            return None
    
    def _get_size_width(self, size: str) -> int:
        """获取尺寸宽度"""
        sizes = {
            'thumbnail': 200,
            'small': 640,
            'medium': 1920,
            'large': 2560
        }
        return sizes.get(size, 1920)
    
    def get_media_item_metadata(self, media_item: Dict) -> Dict:
        """提取媒体项元数据"""
        metadata = media_item.get('mediaMetadata', {})
        creation_time = metadata.get('creationTime', '')
        
        # 解析时间
        photo_time = None
        if creation_time:
            try:
                photo_time = datetime.fromisoformat(creation_time.replace('Z', '+00:00'))
            except:
                pass
        
        # 提取位置信息
        location = None
        if 'location' in media_item:
            loc = media_item['location']
            location = {
                'lat': loc.get('latLng', {}).get('latitude'),
                'lng': loc.get('latLng', {}).get('longitude'),
                'locationName': loc.get('locationName', '')
            }
        
        return {
            'id': media_item.get('id'),
            'filename': media_item.get('filename', ''),
            'mimeType': media_item.get('mimeType', ''),
            'creationTime': creation_time,
            'photoTime': photo_time,
            'location': location,
            'description': media_item.get('description', '')
        }
