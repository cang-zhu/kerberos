from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import pyotp

# 用户-角色关联表
user_roles = db.Table('user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('role_name', db.String(50), primary_key=True)
)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    email = db.Column(db.String(120))
    totp_secret = db.Column(db.String(32))
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    roles = db.Column(db.String(255))  # 存储角色列表，用逗号分隔
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(self, username, email=None):
        self.username = username
        self.email = email
        self.roles = ""
        self.is_active = True
    
    def set_password(self, password):
        """设置密码"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """验证密码"""
        return check_password_hash(self.password_hash, password)
    
    def update_last_login(self):
        """更新最后登录时间"""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    @property
    def is_admin(self):
        """检查是否是管理员"""
        return 'admin' in self.roles.split(',') if self.roles else False
    
    def has_role(self, role):
        """检查用户是否具有指定角色"""
        if self.roles:
            return role in self.roles.split(',')
        return False
    
    def add_role(self, role_name):
        """添加角色"""
        if not self.roles:
            self.roles = role_name
        elif role_name not in self.roles.split(','):
            self.roles = f"{self.roles},{role_name}"
    
    def remove_role(self, role_name):
        """移除角色"""
        if self.roles:
            roles = self.roles.split(',')
            if role_name in roles:
                roles.remove(role_name)
                self.roles = ','.join(roles)
    
    def get_totp_uri(self):
        """获取TOTP URI，用于生成二维码"""
        return pyotp.totp.TOTP(self.totp_secret).provisioning_uri(
            name=self.username,
            issuer_name="Hadoop集群管理系统"
        )
        
    def verify_totp(self, token):
        """验证TOTP令牌"""
        if not self.totp_secret:
            return False
        totp = pyotp.TOTP(self.totp_secret)
        return totp.verify(token)
    
    def __repr__(self):
        return f'<User {self.username}>' 