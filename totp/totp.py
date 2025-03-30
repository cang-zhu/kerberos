import time
import base64
import hmac
import hashlib
import os
from typing import Optional

class TOTP:
    """基于时间的一次性密码生成器"""
    
    def __init__(self, secret: Optional[str] = None):
        """
        初始化TOTP生成器
        
        Args:
            secret: TOTP密钥，如果为None则生成新的密钥
        """
        if secret is None:
            # 生成32字节的随机密钥
            self.secret = base64.b32encode(os.urandom(20)).decode('utf-8')
        else:
            self.secret = secret
    
    def get_current_code(self) -> str:
        """
        获取当前的TOTP代码
        
        Returns:
            6位数字的TOTP代码
        """
        # 获取当前时间戳（30秒为一个周期）
        t = int(time.time() / 30)
        
        # 将时间戳转换为字节
        t_bytes = t.to_bytes(8, 'big')
        
        # 解码密钥
        key = base64.b32decode(self.secret)
        
        # 计算HMAC-SHA1
        hmac_obj = hmac.new(key, t_bytes, hashlib.sha1)
        hmac_result = hmac_obj.digest()
        
        # 获取偏移量
        offset = hmac_result[-1] & 0xf
        
        # 提取4字节
        code_bytes = hmac_result[offset:offset + 4]
        
        # 转换为整数
        code_int = int.from_bytes(code_bytes, 'big')
        
        # 生成6位数字代码
        code = str(code_int % 1000000).zfill(6)
        
        return code
    
    def verify_code(self, code: str) -> bool:
        """
        验证TOTP代码
        
        Args:
            code: 要验证的6位数字代码
            
        Returns:
            验证是否成功
        """
        # 获取当前代码
        current_code = self.get_current_code()
        
        # 验证代码
        return code == current_code
    
    def get_remaining_seconds(self) -> int:
        """
        获取当前TOTP代码的剩余有效时间（秒）
        
        Returns:
            剩余秒数
        """
        return 30 - (int(time.time()) % 30) 