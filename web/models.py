from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# 用户-角色关联表
user_roles = db.Table('user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True)
)

# 角色-权限关联表
role_permissions = db.Table('role_permissions',
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permissions.id'), primary_key=True)
)

class Permission(db.Model):
    """权限模型"""
    __tablename__ = 'permissions'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(255))

    def __repr__(self):
        return f'<Permission {self.name}>'

class Role(db.Model):
    """角色模型"""
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(255))
    
    # 角色-权限关系
    permissions = db.relationship('Permission', secondary=role_permissions,
                                backref=db.backref('roles', lazy=True))

    def __repr__(self):
        return f'<Role {self.name}>'

class User(db.Model):
    """用户模型"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    totp_secret = db.Column(db.String(32))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 用户-角色关系
    roles = db.relationship('Role', secondary=user_roles,
                          backref=db.backref('users', lazy=True))
    
    def has_permission(self, permission_name: str) -> bool:
        """检查用户是否具有指定权限"""
        for role in self.roles:
            for permission in role.permissions:
                if permission.name == permission_name:
                    return True
        return False
    
    def get_available_services(self) -> list:
        """获取用户可访问的服务列表"""
        services = []
        service_permissions = {
            'hdfs': 'use_hdfs',
            'yarn': 'use_yarn',
            'hive': 'use_hive'
        }
        
        for service, permission in service_permissions.items():
            if self.has_permission(permission):
                services.append(service)
        
        return services

    def has_role(self, role_name):
        """检查用户是否具有指定角色"""
        return any(role.name == role_name for role in self.roles)

    def __repr__(self):
        return f'<User {self.username}>'

class LoginAttempt(db.Model):
    """登录尝试记录模型"""
    __tablename__ = 'login_attempts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45))
    success = db.Column(db.Boolean, default=False)
    failure_reason = db.Column(db.String(255))
    
    # 登录尝试-用户关系
    user = db.relationship('User', backref=db.backref('attempts', lazy=True)) 