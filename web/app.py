from flask import Flask, render_template, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import logging
import os
from dotenv import load_dotenv
from flask_migrate import Migrate
import hashlib
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from kerberos.auth import KerberosAuth
from web.models import db, User, LoginAttempt, Role, Permission
from web.decorators import admin_required, permission_required
from web.hadoop_api import hadoop_api, init_hadoop_manager, HadoopManager
from totp.totp import TOTP

# 全局变量
hadoop_manager = None

def create_app():
    """创建Flask应用实例"""
    global hadoop_manager
    
    # 加载环境变量
    env = os.getenv('FLASK_ENV', 'development')
    if env == 'development':
        load_dotenv('.env.test')
    else:
        load_dotenv(f'.env.{env}')
    
    # 创建应用实例
    app = Flask(__name__)
    app.secret_key = os.getenv('SECRET_KEY')
    
    # 配置数据库
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # 初始化数据库
    db.init_app(app)
    
    # 配置迁移
    migrate = Migrate(app, db)
    
    # 配置日志
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # 初始化认证组件
    kerberos_auth = KerberosAuth(
        service_name=os.getenv('KERBEROS_SERVICE_NAME', 'HTTP'),
        realm=os.getenv('KERBEROS_REALM', 'TEST.COM')
    )
    
    # 初始化Hadoop管理器
    hadoop_config_dir = os.getenv('HADOOP_CONFIG_DIR', '/etc/hadoop/conf')
    hadoop_manager = HadoopManager(hadoop_config_dir)
    
    # 注册Hadoop API蓝图
    app.register_blueprint(hadoop_api, url_prefix='/api/hadoop')
    
    @app.route('/')
    def index():
        """首页"""
        return render_template('index.html')
    
    @app.route('/login', methods=['POST'])
    def login():
        """用户登录"""
        try:
            data = request.json
            username = data.get('username')
            password = data.get('password')
            service = data.get('service')
            
            if not username or not password:
                return jsonify({'error': '用户名和密码不能为空'}), 400
            
            # 检查用户是否存在
            user = User.query.filter_by(username=username).first()
            if not user:
                return jsonify({'error': '用户不存在'}), 404
            
            # 管理员可以选择 'admin' 服务
            if service == 'admin':
                if not user.has_role('admin'):
                    return jsonify({'error': '您没有管理员权限'}), 403
            else:
                if service not in ['hdfs', 'yarn', 'hive']:
                    return jsonify({'error': '请指定要访问的服务（hdfs/yarn/hive）'}), 400
                
                # 检查普通服务的权限
                service_permission = f'use_{service}'
                if not user.has_permission(service_permission):
                    return jsonify({'error': f'您没有访问{service}的权限'}), 403
            
            # Kerberos认证
            if not kerberos_auth.authenticate(username, password):
                return jsonify({'error': 'Kerberos认证失败'}), 401
            
            # 如果不是管理员服务，则获取服务票据
            if service != 'admin':
                success, error = hadoop_manager.authenticate_user(username, password)
                if not success:
                    return jsonify({'error': f'获取{service}服务票据失败: {error}'}), 401
            
            # 生成或获取TOTP密钥
            if not user.totp_secret:
                totp = TOTP()
                user.totp_secret = totp.secret
                db.session.commit()
                session['totp_secret'] = totp.secret
            else:
                session['totp_secret'] = user.totp_secret
            
            session['username'] = username
            session['service'] = service
            
            return jsonify({
                'message': '请输入TOTP验证码',
                'totp_secret': session['totp_secret']
            })
        except Exception as e:
            logger.error(f"登录失败: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/generate_totp', methods=['POST'])
    def generate_totp():
        """生成TOTP代码"""
        try:
            data = request.json
            secret = data.get('secret')
            
            if not secret:
                return jsonify({'error': 'TOTP密钥不能为空'}), 400
            
            totp = TOTP(secret=secret)
            code = totp.get_current_code()
            
            return jsonify({
                'code': code,
                'remaining_seconds': totp.get_remaining_seconds()
            })
        except Exception as e:
            logger.error(f"生成TOTP失败: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/verify', methods=['POST'])
    def verify_totp():
        """验证TOTP"""
        try:
            data = request.json
            totp_code = data.get('totp_code')
            
            if not totp_code:
                return jsonify({'error': 'TOTP验证码不能为空'}), 400
            
            if 'totp_secret' not in session or 'service' not in session:
                return jsonify({'error': '请先登录'}), 401
            
            # 验证TOTP
            totp = TOTP(secret=session['totp_secret'])
            if not totp.verify_code(totp_code):
                return jsonify({'error': 'TOTP验证失败'}), 401
            
            # 验证服务访问权限
            service = session['service']
            username = session['username']
            success, error = hadoop_manager.verify_service_access(username, service)
            if not success:
                return jsonify({'error': f'服务访问验证失败: {error}'}), 401
            
            # 设置用户环境
            success, error = hadoop_manager.setup_user_environment(username)
            if not success:
                return jsonify({'error': f'设置用户环境失败: {error}'}), 500
            
            # 设置登录状态
            session['authenticated'] = True
            
            return jsonify({
                'message': '登录成功',
                'service': service,
                'username': username
            })
        except Exception as e:
            logger.error(f"TOTP验证失败: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/logout', methods=['POST'])
    def logout():
        """用户登出"""
        session.clear()
        return jsonify({'message': '登出成功'})
    
    @app.route('/admin/users', methods=['GET'])
    @admin_required
    def list_users():
        """获取所有用户列表"""
        users = User.query.all()
        return jsonify({
            'success': True,
            'users': [{
                'id': user.id,
                'username': user.username,
                'is_active': user.is_active,
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'roles': [role.name for role in user.roles]
            } for user in users]
        })
    
    @app.route('/admin/users', methods=['POST'])
    @admin_required
    def create_user():
        """创建新用户"""
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        role_names = data.get('roles', ['user'])  # 默认为普通用户角色
        
        if not username or not password:
            return jsonify({'success': False, 'error': '用户名和密码不能为空'}), 400
            
        if User.query.filter_by(username=username).first():
            return jsonify({'success': False, 'error': '用户名已存在'}), 400
        
        # 创建新用户
        user = User(
            username=username,
            password_hash=hash_password(password)
        )
        
        # 分配角色
        for role_name in role_names:
            role = Role.query.filter_by(name=role_name).first()
            if role:
                user.roles.append(role)
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '用户创建成功',
            'user': {
                'id': user.id,
                'username': user.username,
                'roles': [role.name for role in user.roles]
            }
        })
    
    @app.route('/admin/users/<int:user_id>', methods=['PUT'])
    @admin_required
    def update_user(user_id):
        """更新用户信息"""
        user = User.query.get_or_404(user_id)
        data = request.get_json()
        
        if 'is_active' in data:
            user.is_active = data['is_active']
            
        if 'roles' in data:
            # 清除现有角色
            user.roles = []
            # 添加新角色
            for role_name in data['roles']:
                role = Role.query.filter_by(name=role_name).first()
                if role:
                    user.roles.append(role)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '用户信息更新成功',
            'user': {
                'id': user.id,
                'username': user.username,
                'is_active': user.is_active,
                'roles': [role.name for role in user.roles]
            }
        })
    
    @app.route('/admin/users/<int:user_id>', methods=['DELETE'])
    @admin_required
    def delete_user(user_id):
        """删除用户"""
        user = User.query.get_or_404(user_id)
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '用户删除成功'
        })
    
    @app.route('/admin')
    @admin_required
    def admin_panel():
        """管理员面板"""
        return render_template('admin.html')
    
    return app

# 工具函数
def hash_password(password):
    """对密码进行哈希处理"""
    return hashlib.sha256(password.encode()).hexdigest()

def check_login_attempts(user_id):
    """检查用户登录尝试次数"""
    timeout = datetime.utcnow() - timedelta(minutes=int(os.getenv('LOGIN_TIMEOUT_MINUTES', 15)))
    attempts = LoginAttempt.query.filter(
        LoginAttempt.user_id == user_id,
        LoginAttempt.timestamp > timeout
    ).count()
    return attempts < int(os.getenv('MAX_LOGIN_ATTEMPTS', 5))

def record_login_attempt(user_id, ip_address, success, failure_reason=None):
    """记录登录尝试"""
    attempt = LoginAttempt(
        user_id=user_id,
        ip_address=ip_address,
        success=success,
        failure_reason=failure_reason
    )
    db.session.add(attempt)
    db.session.commit()

# 创建应用实例
app = create_app() 