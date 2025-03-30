from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any
from .crypto import KerberosCrypto
import hashlib

class KerberosAS:
    """认证服务器(Authentication Server)"""
    def __init__(self, crypto: KerberosCrypto):
        self.crypto = crypto
        # 模拟用户数据库，实际应用中应该使用真实的数据库
        self.users = {
            'test_user': hashlib.sha256('test_password'.encode()).hexdigest()
        }
        
    def authenticate(self, username: str, password: str) -> Tuple[bool, Optional[str], Optional[bytes]]:
        """
        AS认证：验证用户身份并发放TGT
        """
        # 验证用户凭据
        if username not in self.users or \
           self.users[username] != hashlib.sha256(password.encode()).hexdigest():
            return False, "用户名或密码错误", None
            
        # 生成客户端/TGS会话密钥
        session_key = self.crypto.create_session_key()
        
        # 创建TGT
        tgt = self.crypto.create_ticket(
            client_id=username,
            server_id='krbtgs',
            session_key=session_key,
            timestamp=datetime.utcnow(),
            lifetime=timedelta(hours=10),
            crypto=self.crypto.tgs_crypto
        )
        
        return True, tgt, session_key

class KerberosTGS:
    """票据授予服务器(Ticket Granting Server)"""
    def __init__(self, crypto: KerberosCrypto):
        self.crypto = crypto
        
    def grant_service_ticket(self, tgt: str, authenticator: str,
                           service_id: str) -> Tuple[bool, Optional[str], Optional[bytes]]:
        """
        TGS服务：验证TGT和认证器，发放服务票据
        """
        # 验证TGT
        tgt_valid, tgt_data = self.crypto.verify_ticket(tgt, self.crypto.tgs_crypto)
        if not tgt_valid:
            return False, "TGT无效", None
            
        # 验证认证器
        auth_valid, auth_data = self.crypto.verify_authenticator(
            authenticator,
            tgt_data['session_key'].encode()
        )
        if not auth_valid:
            return False, "认证器无效", None
            
        # 验证客户端身份
        if auth_data['client_id'] != tgt_data['client_id']:
            return False, "客户端身份不匹配", None
            
        # 生成新的会话密钥
        service_session_key = self.crypto.create_session_key()
        
        # 创建服务票据
        service_ticket = self.crypto.create_ticket(
            client_id=tgt_data['client_id'],
            server_id=service_id,
            session_key=service_session_key,
            timestamp=datetime.utcnow(),
            lifetime=timedelta(hours=10),
            crypto=self.crypto.service_crypto
        )
        
        return True, service_ticket, service_session_key

class KerberosService:
    """Kerberos应用服务器"""
    def __init__(self, service_id: str, crypto: KerberosCrypto):
        self.service_id = service_id
        self.crypto = crypto
        
    def verify_client(self, service_ticket: str,
                     authenticator: str) -> Tuple[bool, Optional[str]]:
        """
        服务认证：验证服务票据和认证器
        """
        # 验证服务票据
        ticket_valid, ticket_data = self.crypto.verify_ticket(
            service_ticket,
            self.crypto.service_crypto
        )
        if not ticket_valid:
            return False, "服务票据无效"
            
        # 验证服务ID
        if ticket_data['server_id'] != self.service_id:
            return False, "服务ID不匹配"
            
        # 验证认证器
        auth_valid, auth_data = self.crypto.verify_authenticator(
            authenticator,
            ticket_data['session_key'].encode()
        )
        if not auth_valid:
            return False, "认证器无效"
            
        # 验证客户端身份
        if auth_data['client_id'] != ticket_data['client_id']:
            return False, "客户端身份不匹配"
            
        return True, None 