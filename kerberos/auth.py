import logging
from typing import Optional, Tuple
from datetime import datetime
from .crypto import KerberosCrypto
from .servers import KerberosAS, KerberosTGS, KerberosService
from kerberos.mock_auth import MockKerberosAuth
import os

class KerberosAuth:
    def __init__(self, service_name: str, realm: str):
        self.service_name = service_name
        self.realm = realm
        self.logger = logging.getLogger(__name__)
        
        # 初始化Kerberos组件
        self.crypto = KerberosCrypto()
        self.as_server = KerberosAS(self.crypto)
        self.tgs_server = KerberosTGS(self.crypto)
        self.service = KerberosService(service_name, self.crypto)
        
        # 存储会话信息
        self.session_keys = {}

        self.mock_auth = MockKerberosAuth(service_name, realm)

    def authenticate(self, username: str, password: str):
        """
        Kerberos认证
        在开发环境中使用模拟认证
        """
        success, error = self.mock_auth.authenticate(username, password)
        if success:
            self.session_keys = self.mock_auth.session_keys
        return success, error

    def verify_ticket(self, ticket: str):
        """
        验证Kerberos票据
        在开发环境中使用模拟验证
        """
        return self.mock_auth.verify_ticket(ticket)

    def authenticate_full(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """
        完整的Kerberos认证流程
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            Tuple[bool, Optional[str]]: (认证是否成功, 错误信息)
        """
        try:
            # 1. AS认证，获取TGT
            as_success, tgt, client_tgs_key = self.as_server.authenticate(username, password)
            if not as_success:
                return False, tgt  # tgt此时包含错误信息
                
            # 存储会话密钥
            self.session_keys[username] = client_tgs_key
                
            # 2. 创建认证器
            authenticator = self.crypto.create_authenticator(
                username,
                datetime.utcnow(),
                client_tgs_key
            )
            
            # 3. 向TGS请求服务票据
            tgs_success, service_ticket, service_session_key = \
                self.tgs_server.grant_service_ticket(tgt, authenticator, self.service_name)
            if not tgs_success:
                return False, service_ticket  # service_ticket此时包含错误信息
                
            # 4. 创建服务认证器
            service_authenticator = self.crypto.create_authenticator(
                username,
                datetime.utcnow(),
                service_session_key
            )
            
            # 5. 验证服务票据
            service_success, error = self.service.verify_client(
                service_ticket,
                service_authenticator
            )
            if not service_success:
                return False, error
                
            return True, None

        except Exception as e:
            self.logger.error(f"Kerberos认证错误: {str(e)}")
            return False, f"Kerberos认证错误: {str(e)}"

    def verify_ticket_full(self, ticket: str) -> Tuple[bool, Optional[str]]:
        """
        验证服务票据
        
        Args:
            ticket: 服务票据
            
        Returns:
            Tuple[bool, Optional[str]]: (验证是否成功, 错误信息)
        """
        try:
            valid, ticket_data = self.crypto.verify_ticket(
                ticket,
                self.crypto.service_crypto
            )
            if not valid:
                return False, "票据验证失败"
                
            return True, None

        except Exception as e:
            self.logger.error(f"票据验证错误: {str(e)}")
            return False, f"票据验证错误: {str(e)}" 