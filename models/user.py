from datetime import datetime
import pyotp
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    email = db.Column(db.String(120), unique=True)
    role = db.Column(db.String(20), default='user')  # admin 或 user
    totp_secret = db.Column(db.String(32))  # TOTP密钥
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    def __init__(self, username, password, email=None, role='user'):
        self.username = username
        self.set_password(password)
        self.email = email
        self.role = role
        self.totp_secret = pyotp.random_base32()  # 生成TOTP密钥
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_totp_uri(self):
        """获取TOTP二维码URI"""
        totp = pyotp.TOTP(self.totp_secret)
        return totp.provisioning_uri(self.username, issuer_name="Kerberos管理系统")
    
    def verify_totp(self, token):
        """验证TOTP令牌"""
        totp = pyotp.TOTP(self.totp_secret)
        return totp.verify(token)
    
    @property
    def is_admin(self):
        return self.role == 'admin' 