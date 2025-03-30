from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# 创建扩展实例
db = SQLAlchemy()
login_manager = LoginManager()

# 配置登录管理器
login_manager.login_view = 'login'
login_manager.login_message = '请先登录'
login_manager.login_message_category = 'info' 