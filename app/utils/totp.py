import hmac
import time
import base64
import struct
import secrets
import qrcode
import io

class TOTP:
    def __init__(self, secret=None, digits=6, interval=30):
        """
        初始化 TOTP 实例
        :param secret: 密钥（如果不提供，将自动生成）
        :param digits: TOTP 代码的位数
        :param interval: TOTP 更新间隔（秒）
        """
        self.digits = digits
        self.interval = interval
        if secret is None:
            # 生成一个随机的 32 字节密钥
            self.secret = base64.b32encode(secrets.token_bytes(20)).decode('utf-8')
        else:
            self.secret = secret

    def generate_code(self, timestamp=None):
        """
        生成 TOTP 代码
        :param timestamp: 时间戳（如果不提供，使用当前时间）
        :return: TOTP 代码
        """
        if timestamp is None:
            timestamp = time.time()
        
        # 计算时间步数
        time_step = int(timestamp / self.interval)
        
        # 将时间步数转换为字节串
        time_bytes = struct.pack(">Q", time_step)
        
        # 计算 HMAC-SHA1
        key = base64.b32decode(self.secret)
        hmac_obj = hmac.new(key, time_bytes, 'sha1')
        hmac_result = hmac_obj.digest()
        
        # 获取偏移量
        offset = hmac_result[-1] & 0xf
        
        # 生成 4 字节的代码
        code_bytes = hmac_result[offset:offset + 4]
        code = struct.unpack('>L', code_bytes)[0]
        
        # 提取指定位数的代码
        code = code & ((1 << 32) - 1)
        code = code % (10 ** self.digits)
        
        # 补齐前导零
        return str(code).zfill(self.digits)

    def verify_code(self, code, timestamp=None, valid_window=1):
        """
        验证 TOTP 代码
        :param code: 要验证的代码
        :param timestamp: 时间戳（如果不提供，使用当前时间）
        :param valid_window: 验证窗口（前后各多少个时间步长有效）
        :return: 是否有效
        """
        if timestamp is None:
            timestamp = time.time()
            
        # 检查当前时间步长及其前后的代码
        for i in range(-valid_window, valid_window + 1):
            check_time = timestamp + i * self.interval
            if self.generate_code(check_time) == str(code):
                return True
        return False

    def get_remaining_seconds(self):
        """
        获取当前 TOTP 代码的剩余有效秒数
        :return: 剩余秒数
        """
        current_time = time.time()
        return self.interval - (int(current_time) % self.interval)

    def get_current_code(self):
        """
        获取当前的 TOTP 代码
        :return: 当前代码
        """
        return self.generate_code() 