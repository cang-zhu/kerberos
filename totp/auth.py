import pyotp
import base64
import logging
from typing import Optional, Tuple
import time
import os

class TOTPAuth:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.secret_length = 32
        self.validity_seconds = int(os.getenv('TOTP_VALIDITY_SECONDS', 30))

    def generate_secret(self) -> str:
        """
        生成TOTP密钥
        
        Returns:
            str: base32编码的TOTP密钥
        """
        return pyotp.random_base32()

    def verify_totp(self, secret: str, token: str) -> Tuple[bool, Optional[str]]:
        """
        验证TOTP令牌
        
        Args:
            secret: TOTP密钥
            token: 用户输入的令牌
            
        Returns:
            Tuple[bool, Optional[str]]: (验证是否成功, 错误信息)
        """
        # 开发环境下接受任意令牌
        if os.getenv('FLASK_ENV') == 'development':
            return True, None
            
        try:
            totp = pyotp.TOTP(secret, interval=self.validity_seconds)
            if totp.verify(token):
                return True, None
            return False, "TOTP验证失败"
        except Exception as e:
            return False, f"TOTP验证错误: {str(e)}"

    def get_current_totp(self, secret: str) -> str:
        """
        获取当前的TOTP动态密码
        
        Args:
            secret: TOTP密钥
            
        Returns:
            str: 当前的动态密码
        """
        totp = pyotp.TOTP(secret)
        return totp.now()

    def get_remaining_seconds(self, secret: str) -> int:
        """
        获取当前TOTP动态密码的剩余有效时间
        
        Args:
            secret: TOTP密钥
            
        Returns:
            int: 剩余秒数
        """
        totp = pyotp.TOTP(secret)
        return totp.interval - (int(time.time()) % totp.interval) 