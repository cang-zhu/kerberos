from cryptography.fernet import Fernet
from datetime import datetime, timedelta
from typing import Tuple, Dict, Any
import base64
import json
import os

class KerberosCrypto:
    def __init__(self):
        # 在实际环境中，这些密钥应该安全存储
        self.as_key = Fernet.generate_key()
        self.tgs_key = Fernet.generate_key()
        self.service_key = Fernet.generate_key()
        
        self.as_crypto = Fernet(self.as_key)
        self.tgs_crypto = Fernet(self.tgs_key)
        self.service_crypto = Fernet(self.service_key)

    def create_session_key(self):
        """生成会话密钥"""
        return Fernet.generate_key()

    def create_ticket(self, client_id: str, server_id: str, session_key: bytes,
                     timestamp: datetime, lifetime: timedelta, crypto: Fernet) -> str:
        """
        创建票据
        """
        ticket_data = {
            'client_id': client_id,
            'server_id': server_id,
            'session_key': session_key.decode(),
            'timestamp': timestamp.isoformat(),
            'lifetime': lifetime.total_seconds()
        }
        
        # 加密票据数据
        encrypted_data = crypto.encrypt(json.dumps(ticket_data).encode())
        return base64.b64encode(encrypted_data).decode()

    def verify_ticket(self, ticket: str, crypto: Fernet) -> Tuple[bool, Dict[str, Any]]:
        """
        验证票据
        """
        try:
            encrypted_data = base64.b64decode(ticket.encode())
            decrypted_data = crypto.decrypt(encrypted_data)
            ticket_data = json.loads(decrypted_data.decode())
            
            # 检查票据是否过期
            timestamp = datetime.fromisoformat(ticket_data['timestamp'])
            lifetime = timedelta(seconds=ticket_data['lifetime'])
            if datetime.utcnow() > timestamp + lifetime:
                return False, {'error': '票据已过期'}
                
            return True, ticket_data
            
        except Exception as e:
            return False, {'error': f'票据验证失败: {str(e)}'}

    def create_authenticator(self, client_id: str, timestamp: datetime,
                           session_key: bytes) -> str:
        """
        创建认证器
        """
        auth_data = {
            'client_id': client_id,
            'timestamp': timestamp.isoformat()
        }
        
        crypto = Fernet(session_key)
        encrypted_data = crypto.encrypt(json.dumps(auth_data).encode())
        return base64.b64encode(encrypted_data).decode()

    def verify_authenticator(self, authenticator: str, session_key: bytes) -> Tuple[bool, Dict[str, Any]]:
        """
        验证认证器
        """
        try:
            crypto = Fernet(session_key)
            encrypted_data = base64.b64decode(authenticator.encode())
            decrypted_data = crypto.decrypt(encrypted_data)
            auth_data = json.loads(decrypted_data.decode())
            
            # 检查时间戳是否在允许范围内（例如5分钟）
            timestamp = datetime.fromisoformat(auth_data['timestamp'])
            if datetime.utcnow() - timestamp > timedelta(minutes=5):
                return False, {'error': '认证器已过期'}
                
            return True, auth_data
            
        except Exception as e:
            return False, {'error': f'认证器验证失败: {str(e)}'} 