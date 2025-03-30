import logging
import os
from typing import Optional, Tuple

class MockKerberosAuth:
    def __init__(self, service_name: str, realm: str):
        self.service_name = service_name
        self.realm = realm
        self.logger = logging.getLogger(__name__)
        # 测试用户
        self.test_users = {
            'admin': 'admin123',
            'user1': 'user123',
            'user2': 'user123'
        }
        self.session_keys = {}  # 添加session_keys字典

    def authenticate(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """
        模拟Kerberos认证
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            Tuple[bool, Optional[str]]: (认证是否成功, 错误信息)
        """
        # 开发环境下接受任意用户名和密码
        if os.getenv('FLASK_ENV') == 'development':
            # 生成一个模拟的会话密钥
            self.session_keys[username] = f"mock_ticket_{username}"
            return True, None
            
        if username in self.test_users and self.test_users[username] == password:
            return True, None
        return False, "用户名或密码错误"

    def verify_ticket(self, ticket: str) -> bool:
        """
        模拟票据验证
        
        Args:
            ticket: 模拟的票据
            
        Returns:
            bool: 验证是否成功
        """
        # 开发环境下接受任意票据
        if os.getenv('FLASK_ENV') == 'development':
            return True
            
        return ticket in self.session_keys.values() 