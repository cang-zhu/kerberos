import os
import sys
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import logging
import random
import string
import hmac
import hashlib
import time
import base64
import secrets
import pyotp
import subprocess
from werkzeug.urls import url_parse
from src.hadoop_service import HadoopService
from kerberos_auth import KerberosAuth

# 加载环境变量
load_dotenv()

# 检查必要的环境变量
required_env_vars = [
    'HADOOP_HOME', 
    'JAVA_HOME',
    'KRB5_CONFIG',
    'KRB5_KDC_PROFILE',
    'KDC_DB_PATH'
]
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    print(f"错误: 缺少必要的环境变量: {', '.join(missing_vars)}")
    print("请确保.env文件存在并包含所有必要的环境变量")
    sys.exit(1)

# 打印环境变量信息
print(f"HADOOP_HOME: {os.getenv('HADOOP_HOME')}")
print(f"JAVA_HOME: {os.getenv('JAVA_HOME')}")
print(f"KRB5_CONFIG: {os.getenv('KRB5_CONFIG')}")
print(f"KRB5_KDC_PROFILE: {os.getenv('KRB5_KDC_PROFILE')}")
print(f"KDC_DB_PATH: {os.getenv('KDC_DB_PATH')}")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # 输出到控制台
        logging.FileHandler('kerberos.log', encoding='utf-8')  # 同时输出到文件
    ]
)
logger = logging.getLogger(__name__)

# 设置Hadoop相关日志级别为WARNING，以减少不必要的输出
logging.getLogger('hadoop').setLevel(logging.WARNING)
logging.getLogger('hdfs').setLevel(logging.WARNING)
logging.getLogger('yarn').setLevel(logging.WARNING)

# 数据库路径
db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app.db')

# 创建应用实例
app = Flask(__name__)

# 配置
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'hard_to_guess_string')
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

logger.info("数据库路径: {}".format(db_path))
logger.info("数据库URI: {}".format(app.config['SQLALCHEMY_DATABASE_URI']))

# 初始化扩展
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = '请先登录'

# 创建Hadoop服务管理实例
hadoop_service = None
kerberos_auth = None

# 使用环境变量中的配置
KRB5_CONFIG = os.getenv('KRB5_CONFIG')
KRB5_KDC_PROFILE = os.getenv('KRB5_KDC_PROFILE')
KDC_DB_PATH = os.getenv('KDC_DB_PATH')

# Kerberos 命令路径
KRB5_UTIL_PATH = os.getenv('KRB5_UTIL_PATH', 'kdb5_util')
KRB5KDC_PATH = os.getenv('KRB5KDC_PATH', 'krb5kdc')
KADMIND_PATH = os.getenv('KADMIND_PATH', 'kadmind')

# PID文件路径
KRB5KDC_PID_PATH = os.getenv('KRB5KDC_PID_PATH', os.path.join(os.path.dirname(__file__), 'var', 'krb5kdc', 'krb5kdc.pid'))

def find_kerberos_command(command_name):
    """查找Kerberos命令的完整路径
    
    Args:
        command_name (str): 命令名称，如 'kadmin.local', 'krb5kdc' 等
        
    Returns:
        str: 命令的完整路径，如果找不到则返回None
    """
    # 常见的命令路径
    common_paths = [
        '/usr/sbin',                    # CentOS/RHEL默认路径
        '/usr/local/sbin',              # 通用Linux路径
        '/usr/local/opt/krb5/sbin',     # macOS Homebrew安装路径
        '/opt/krb5/sbin',               # 自定义安装路径
        '/usr/local/bin',               # 其他可能的路径
        '/usr/bin'
    ]
    
    # 首先检查环境变量中是否有定义
    env_var = 'KRB5_{}_PATH'.format(command_name.upper())
    if os.getenv(env_var):
        cmd_path = os.getenv(env_var)
        if os.path.exists(cmd_path):
            return cmd_path
    
    # 在常见路径中查找
    for path in common_paths:
        cmd_path = os.path.join(path, command_name)
        if os.path.exists(cmd_path):
            return cmd_path
    
    # 如果都找不到，返回None
    return None

def init_services():
    """初始化所有服务"""
    global hadoop_service, kerberos_auth
    
    # 初始化Hadoop服务
    try:
        hadoop_service = HadoopService()
        # 检查Hadoop配置
        config_ok, issues = hadoop_service.check_hadoop_config()
        if not config_ok:
            logger.error("Hadoop配置检查失败: {}".format(', '.join(issues)))
        else:
            # 启动Hadoop服务
            success, message = hadoop_service.start_services()
            if success:
                logger.info(message)
            else:
                logger.error(message)
    except Exception as e:
        logger.error("初始化Hadoop服务时出错: {}".format(str(e)))

    # 初始化Kerberos服务
    try:
        # 初始化Kerberos认证服务
        kerberos_auth = KerberosAuth()
        
        # 检查必要的环境变量和路径
        if not all([KRB5_CONFIG, KRB5_KDC_PROFILE, KDC_DB_PATH]):
            logger.error("缺少必要的Kerberos配置路径")
            return
            
        # 确保配置目录存在
        for path in [os.path.dirname(KRB5_CONFIG), os.path.dirname(KRB5_KDC_PROFILE)]:
            if not os.path.exists(path):
                try:
                    os.makedirs(path, mode=0o755, exist_ok=True)
                    logger.info("创建目录: {}".format(path))
                except Exception as e:
                    logger.error("创建目录失败 {}: {}".format(path, str(e)))
                    return
        
        # 确保KDC数据库目录存在
        kdc_db_dir = os.path.dirname(KDC_DB_PATH)
        if not os.path.exists(kdc_db_dir):
            try:
                os.makedirs(kdc_db_dir, mode=0o700, exist_ok=True)
                logger.info("创建KDC数据库目录: {}".format(kdc_db_dir))
            except Exception as e:
                logger.error("创建KDC数据库目录失败: {}".format(str(e)))
                return
            
        # 检查配置文件是否存在
        if not all(os.path.exists(path) for path in [KRB5_CONFIG, KRB5_KDC_PROFILE]):
            logger.error("Kerberos配置文件不存在")
            return
            
        kerberos_auth.conf_file = KRB5_CONFIG
        kerberos_auth.kdc_conf = KRB5_KDC_PROFILE
        kerberos_auth.kdc_db_path = KDC_DB_PATH
        kerberos_auth.dev_mode = True
        
        # 初始化KDC服务
        kerberos_auth.initialize()
        
        # 检查并启动KDC服务
        if not os.path.exists(KDC_DB_PATH):
            logger.info("初始化KDC数据库...")
            create_kdc_database()
        
        # 启动KDC服务
        logger.info("启动KDC服务...")
        start_kdc_server()
        
        # 启动kadmin服务
        logger.info("启动kadmin服务...")
        start_kadmin_server()
        
        logger.info("Kerberos服务初始化完成")
    except Exception as e:
        logger.error("初始化Kerberos服务时出错: {}".format(str(e)))

def create_kdc_database():
    try:
        # 查找kdb5_util命令
        kdb5_util_cmd = find_kerberos_command('kdb5_util')
        if not kdb5_util_cmd:
            raise FileNotFoundError("找不到kdb5_util命令，请确保已安装Kerberos")
        
        # 确保KDC数据库目录存在并有正确的权限
        kdc_db_dir = os.path.dirname(KDC_DB_PATH)
        if not os.path.exists(kdc_db_dir):
            os.makedirs(kdc_db_dir, mode=0o700)
            logger.info(f"创建KDC数据库目录: {kdc_db_dir}")
        
        # 设置环境变量
        env = os.environ.copy()
        env.update({
            'KRB5_CONFIG': KRB5_CONFIG,
            'KRB5_KDC_PROFILE': KRB5_KDC_PROFILE,
            'KRB5_TRACE': '/dev/stdout'  # 启用详细调试输出
        })
        
        # 检查数据库是否已存在
        if os.path.exists(KDC_DB_PATH):
            logger.info("KDC数据库已存在，跳过创建")
            return True
        
        # 构建命令
        master_password = os.getenv('KRB5_MASTER_PASSWORD', 'your_master_password')
        command = [
            kdb5_util_cmd,
            'create',
            '-r', 'HADOOP.COM',
            '-s'
        ]
        
        # 通过管道提供master password
        process = subprocess.Popen(
            command,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # 输入master password两次
        stdout, stderr = process.communicate(input=f"{master_password}\n{master_password}\n")
        
        if process.returncode == 0:
            logger.info("KDC数据库创建成功")
            
            # 设置数据库文件权限
            for file in os.listdir(kdc_db_dir):
                if file.startswith('K') or file.endswith('.kadm5'):
                    file_path = os.path.join(kdc_db_dir, file)
                    os.chmod(file_path, 0o600)
                    logger.info(f"设置数据库文件权限: {file_path}")
            
            return True
        else:
            logger.error(f"KDC数据库创建失败: {stderr}")
            raise Exception(stderr)
            
    except Exception as e:
        logger.error(f"创建KDC数据库时出错: {str(e)}")
        raise

def start_kdc_server():
    try:
        # 查找krb5kdc命令
        krb5kdc_cmd = find_kerberos_command('krb5kdc')
        if not krb5kdc_cmd:
            raise FileNotFoundError("找不到krb5kdc命令，请确保已安装Kerberos")
        
        env = os.environ.copy()
        env.update({
            'KRB5_CONFIG': KRB5_CONFIG,
            'KRB5_KDC_PROFILE': KRB5_KDC_PROFILE
        })
        
        # 修改为兼容Python 3.6的参数
        process = subprocess.Popen(
            [krb5kdc_cmd],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        logger.info("KDC服务启动成功")
    except Exception as e:
        logger.error("启动KDC服务时出错: {}".format(str(e)))
        raise

def start_kadmin_server():
    try:
        # 查找kadmind命令
        kadmind_cmd = find_kerberos_command('kadmind')
        if not kadmind_cmd:
            raise FileNotFoundError("找不到kadmind命令，请确保已安装Kerberos")
        
        env = os.environ.copy()
        env.update({
            'KRB5_CONFIG': KRB5_CONFIG,
            'KRB5_KDC_PROFILE': KRB5_KDC_PROFILE
        })
        
        # 修改为兼容Python 3.6的参数
        process = subprocess.Popen(
            [kadmind_cmd, '-nofork'],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        logger.info("kadmin服务启动成功")
    except Exception as e:
        logger.error("启动kadmin服务时出错: {}".format(str(e)))
        raise

# 替换before_first_request装饰器
with app.app_context():
    init_services()

# 添加Hadoop服务状态检查路由
@app.route('/hadoop/status')
@login_required
def hadoop_status():
    """检查Hadoop服务状态"""
    if not hadoop_service:
        return jsonify({
            'status': 'error',
            'message': 'Hadoop服务未初始化'
        })
    
    running_services = hadoop_service.check_service_status()
    service_ports = hadoop_service.get_service_ports()
    
    return jsonify({
        'status': 'success',
        'running_services': running_services,
        'service_ports': service_ports
    })

@app.route('/hadoop/start')
@login_required
def hadoop_start():
    """启动Hadoop服务"""
    if not hadoop_service:
        return jsonify({
            'status': 'error',
            'message': 'Hadoop服务未初始化'
        })
    
    success, message = hadoop_service.start_services()
    return jsonify({
        'status': 'success' if success else 'error',
        'message': message
    })

@app.route('/hadoop/stop')
@login_required
def hadoop_stop():
    """停止Hadoop服务"""
    if not hadoop_service:
        return jsonify({
            'status': 'error',
            'message': 'Hadoop服务未初始化'
        })
    
    success, message = hadoop_service.stop_services()
    return jsonify({
        'status': 'success' if success else 'error',
        'message': message
    })

# 定义模型
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(128))
    totp_secret = db.Column(db.String(32), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    last_login = db.Column(db.DateTime)
    roles = db.Column(db.String(255))  # 存储角色列表，用逗号分隔
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    last_realm = db.Column(db.String(50), nullable=True)  # 存储最后使用的Kerberos领域
    
    def __init__(self, username, email=None, is_admin=False, realm=None):
        self.username = username
        self.email = email
        self.roles = ""
        self.is_admin = is_admin
        self.last_realm = realm
        self.created_at = datetime.now()
        self.is_active = True
    
    def set_password(self, password):
        """设置密码"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """验证密码"""
        return check_password_hash(self.password_hash, password)
    
    @property
    def has_admin_role(self):
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

# TOTP 实现
class TOTP:
    def __init__(self, secret=None):
        if secret is None:
            secret = pyotp.random_base32()
        self.secret = secret
        self.totp = pyotp.TOTP(secret)
    
    def generate_code(self):
        return self.totp.now()
    
    def verify_code(self, code):
        return self.totp.verify(code)
    
    def get_provisioning_uri(self, username):
        return self.totp.provisioning_uri(username, issuer_name="Kerberos系统")

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def init_db():
    """初始化数据库"""
    logger.info(f"数据库路径: {db_path}")
    logger.info(f"数据库URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    
    try:
        # 确保包含数据库的目录存在
        db_dir = os.path.dirname(db_path)
        if not os.path.exists(db_dir) and db_dir:
            os.makedirs(db_dir)
            logger.info(f"创建数据库目录: {db_dir}")
            
        # 只在数据库文件不存在时初始化
        if not os.path.exists(db_path):
            logger.info(f"数据库文件不存在，创建新数据库: {db_path}")
            db.create_all()
            logger.info("创建数据库表成功")
            
            # 检查是否存在管理员用户
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                admin = User(username='admin', is_admin=True)
                admin.set_password('admin123')
                admin.add_role('admin')
                db.session.add(admin)
                db.session.commit()
                logger.info("创建管理员用户成功")
            else:
                logger.info("管理员用户已存在")
        else:
            logger.info(f"使用现有数据库文件: {db_path}")
            # 确保数据库表结构是最新的
            db.create_all()
        
        return True
    except Exception as e:
        logger.error(f"数据库初始化失败: {str(e)}")
        return False

# 装饰器：需要 TOTP 验证
def totp_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('totp_verified'):
            return redirect(url_for('verify_totp'))
        return f(*args, **kwargs)
    return decorated_function

# 需要角色装饰器
def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('请先登录', 'warning')
                return redirect(url_for('login'))
            
            if not current_user.has_role(role):
                flash(f'你没有 {role} 角色权限', 'danger')
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/')
def index():
    """根路由重定向到登录页面"""
    # 根据认证状态重定向
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    elif session.get('kerberos_authenticated'):
        return redirect(url_for('kerberos_dashboard'))
    else:
        # 检查是否在开发模式下
        if app.debug:
            return render_template('auth_choice.html')
        else:
            return redirect(url_for('kerberos_login'))

@app.route('/auth_choice')
def auth_choice():
    if app.debug:
        return render_template('auth_choice.html')
    else:
        return redirect(url_for('kerberos_login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    # 检查是否已经登录
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    # 检查是否在开发模式下
    if not app.debug:
        # 非开发模式下，重定向到Kerberos认证
        return redirect(url_for('kerberos_login'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user is None or not user.check_password(password):
            flash('用户名或密码错误', 'danger')
            return render_template('login.html')
        
        # 更新最后登录时间
        user.last_login = datetime.now()
        db.session.commit()
        
        # 如果用户没有TOTP密钥，则生成一个
        if not user.totp_secret:
            totp = TOTP()
            user.totp_secret = totp.secret
            db.session.commit()
        
        # 保存用户ID，以便在TOTP验证时使用
        session['user_id_for_totp'] = user.id
        session.modified = True
        
        # 记录一下session中的值，用于调试
        logger.info(f"Setting user_id_for_totp in session: {user.id}")
        logger.info(f"Current session: {session}")
        
        # 重定向到TOTP验证页面
        return redirect(url_for('verify_totp'))
    
    return render_template('login.html')

@app.route('/totp/verify', methods=['GET', 'POST'])
@app.route('/verify_totp', methods=['GET', 'POST'])  # 添加一个别名路由，以兼容可能的前端链接
def verify_totp():
    # 检查会话中是否有用户ID
    user_id = session.get('user_id_for_totp')
    logger.info(f"Retrieved user_id_for_totp from session: {user_id}")
    logger.info(f"Current session: {session}")
    
    # 对于已经通过Kerberos认证的用户或已经登录的用户，尝试查找TOTP关联用户
    if not user_id:
        if session.get('kerberos_authenticated'):
            principal = session.get('kerberos_principal')
            username = principal.split('@')[0] if '@' in principal else principal
            user = User.query.filter_by(username=username).first()
            if user:
                user_id = user.id
                session['user_id_for_totp'] = user_id
        elif current_user.is_authenticated:
            user_id = current_user.id
            session['user_id_for_totp'] = user_id
    
    if not user_id:
        flash('未找到需要验证的用户，请重新登录', 'warning')
        return redirect(url_for('auth_choice'))
    
    user = User.query.get(user_id)
    if not user:
        session.pop('user_id_for_totp', None)
        flash('未找到用户信息，请重新登录', 'warning')
        return redirect(url_for('auth_choice'))
    
    if request.method == 'POST':
        code = request.form.get('code')
        totp = TOTP(user.totp_secret)
        
        if totp.verify_code(code):
            # 设置TOTP验证标志
            session['totp_verified'] = True
            
            # 检查是否通过Kerberos认证
            if session.get('temp_kerberos_authenticated'):
                # 将临时Kerberos信息转为正式
                session['kerberos_authenticated'] = session.get('temp_kerberos_authenticated')
                session['kerberos_principal'] = session.get('temp_kerberos_principal')
                session['kerberos_login_time'] = session.get('temp_kerberos_login_time')
                session['kerberos_expiry'] = session.get('temp_kerberos_expiry')
                session['kerberos_realm'] = session.get('temp_kerberos_realm')  # 添加领域到正式会话
                
                # 清除临时数据
                session.pop('temp_kerberos_authenticated', None)
                session.pop('temp_kerberos_principal', None)
                session.pop('temp_kerberos_login_time', None)
                session.pop('temp_kerberos_expiry', None)
                session.pop('temp_kerberos_realm', None)  # 清除临时领域信息
            else:
                # 普通用户名/密码登录
                if not current_user.is_authenticated:
                    login_user(user)
            
            # 清除TOTP验证用户ID
            session.pop('user_id_for_totp', None)
            
            # 确保session已保存
            session.modified = True
            
            flash('二次验证成功', 'success')
            
            # 检查是否需要返回到dashboard
            if session.get('return_to_dashboard'):
                session.pop('return_to_dashboard', None)
                return redirect(url_for('dashboard'))
            
            # 统一跳转到dashboard页面，该页面会根据认证方式显示不同内容
            return redirect(url_for('dashboard'))
        else:
            flash('验证码无效', 'danger')
    
    # 创建TOTP对象生成验证码
    totp = TOTP(user.totp_secret)
    current_code = totp.generate_code()
    
    # 准备显示信息
    username = user.username
    kerberos_mode = session.get('temp_kerberos_authenticated', False) or session.get('kerberos_authenticated', False)
    
    if kerberos_mode:
        # 提取Kerberos主体信息用于显示
        principal = session.get('temp_kerberos_principal') or session.get('kerberos_principal', '')
        username = principal.split('@')[0] if '@' in principal else principal
        realm = principal.split('@')[1] if '@' in principal else 'HADOOP.COM'
        return render_template('totp_verify.html', 
                           secret=user.totp_secret,
                           current_code=current_code,
                           username=username,
                           kerberos_mode=True,
                           principal=principal,
                           realm=realm)
    
    # 普通用户名/密码登录的TOTP验证
    return render_template('totp_verify.html', 
                        secret=user.totp_secret,
                        current_code=current_code,
                        username=username,
                        kerberos_mode=False)

@app.route('/generate_totp')
def generate_totp():
    """统一的TOTP代码生成器，同时支持普通和Kerberos认证"""
    # 获取用户ID
    user_id = session.get('user_id_for_totp')
    if not user_id:
        return jsonify({'error': 'User not found'}), 404
        
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    totp = TOTP(user.totp_secret)
    current_code = totp.generate_code()
    remaining_time = 30 - (int(datetime.now().timestamp()) % 30)
    return jsonify({
        'code': current_code,
        'remainingSeconds': remaining_time
    })

# 添加一个辅助函数来检查用户是否为管理员
def is_admin_user():
    """检查当前用户是否具有管理员权限，支持Flask-Login和Kerberos认证"""
    # 检查通过Flask-Login认证的用户
    if current_user.is_authenticated:
        return current_user.has_role('admin')
    
    # 检查通过Kerberos认证的用户
    if session.get('kerberos_authenticated'):
        principal = session.get('kerberos_principal')
        username = principal.split('@')[0] if '@' in principal else principal
        
        # 如果用户名是admin，则认为是管理员
        if username.lower() == 'admin':
            return True
            
        # 查询数据库确认是否有管理员权限
        user = User.query.filter_by(username=username).first()
        return user and (user.has_role('admin') or user.is_admin)
    
    return False

@app.route('/dashboard')
def dashboard():
    """统一的用户仪表板，同时支持普通登录和Kerberos登录"""
    # 检查是否通过认证
    if not (current_user.is_authenticated or session.get('kerberos_authenticated')):
        flash('请先登录', 'warning')
        return redirect(url_for('auth_choice'))
    
    # 检查是否完成TOTP验证
    if not session.get('totp_verified'):
        flash('请先完成二次验证', 'warning')
        # 保存当前认证状态到session，以便在验证后返回仪表板
        session['return_to_dashboard'] = True
        if session.get('kerberos_authenticated'):
            return redirect(url_for('verify_totp'))
        else:
            return redirect(url_for('verify_totp'))
    
    # 获取当前时间，用于显示
    now = datetime.now()
    
    # 检查认证方式
    if session.get('kerberos_authenticated'):
        # Kerberos认证用户
        principal = session.get('kerberos_principal')
        realm = session.get('kerberos_realm', 'HADOOP.COM')
        if '@' in principal:
            # 如果主体中已包含领域，则从主体中提取
            parts = principal.split('@')
            username = parts[0]
            realm = parts[1]
        else:
            username = principal
        
        # 设置管理员标志到session中，供模板使用
        is_admin = is_admin_user()
        session['is_admin'] = is_admin
        
        # 计算票据时间
        try:
            login_time_str = session.get('kerberos_login_time', datetime.now().isoformat())
            expiry_time_str = session.get('kerberos_expiry', (datetime.now() + timedelta(hours=10)).isoformat())
            
            # 使用strptime替代fromisoformat
            try:
                login_time = datetime.strptime(login_time_str, '%Y-%m-%dT%H:%M:%S.%f')
            except ValueError:
                login_time = datetime.strptime(login_time_str, '%Y-%m-%dT%H:%M:%S')
                
            try:
                expiry_time = datetime.strptime(expiry_time_str, '%Y-%m-%dT%H:%M:%S.%f')
            except ValueError:
                expiry_time = datetime.strptime(expiry_time_str, '%Y-%m-%dT%H:%M:%S')
        except Exception:
            # 如果解析失败，使用当前时间
            login_time = datetime.now()
            expiry_time = datetime.now() + timedelta(hours=10)
        
        return render_template('dashboard.html',
                           username=username,
                           is_admin=is_admin,  # 使用通用函数判断管理员权限
                           is_kerberos=True,
                           principal=principal,
                           realm=realm,
                           issue_time=login_time.strftime('%Y-%m-%d %H:%M:%S'),
                           expiry_time=expiry_time.strftime('%Y-%m-%d %H:%M:%S'),
                           now=now)
    else:
        # 普通登录用户
        user = current_user
        
        return render_template('dashboard.html', 
                          username=user.username,
                          is_admin=is_admin_user(),  # 使用通用函数判断管理员权限
                          is_kerberos=False,
                          now=now)

@app.route('/users')
def user_management():
    """用户管理页面"""
    # 检查认证和TOTP验证
    if not (current_user.is_authenticated or session.get('kerberos_authenticated')):
        flash('请先登录', 'warning')
        return redirect(url_for('auth_choice'))
    
    if not session.get('totp_verified'):
        flash('请先完成二次验证', 'warning')
        return redirect(url_for('auth_choice'))
    
    # 检查管理员权限
    if not is_admin_user():
        flash('需要管理员权限才能访问此页面', 'danger')
        return redirect(url_for('dashboard'))
    
    # 获取所有用户
    users = User.query.all()
    return render_template('user_management.html', users=users)

@app.route('/api/admin/users', methods=['GET'])
def get_users():
    """获取所有用户信息"""
    # 检查认证和TOTP验证
    if not (current_user.is_authenticated or session.get('kerberos_authenticated')):
        return jsonify({'success': False, 'error': '请先登录'}), 401
    
    if not session.get('totp_verified'):
        return jsonify({'success': False, 'error': '请先完成二次验证'}), 401
    
    # 检查管理员权限
    if not is_admin_user():
        return jsonify({'success': False, 'error': '需要管理员权限'}), 403
    
    try:
        users = User.query.all()
        user_list = []
        for user in users:
            user_list.append({
                'username': user.username,
                'roles': user.roles,
                'is_active': user.is_active,
                'totp_enabled': bool(user.totp_secret),
                'last_login': user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else None
            })
        return jsonify({'success': True, 'users': user_list})
    except Exception as e:
        app.logger.error(f"获取用户列表失败: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/users', methods=['POST'])
def create_user():
    """创建新用户"""
    # 检查认证和TOTP验证
    if not (current_user.is_authenticated or session.get('kerberos_authenticated')):
        return jsonify({'success': False, 'error': '请先登录'}), 401
    
    if not session.get('totp_verified'):
        return jsonify({'success': False, 'error': '请先完成二次验证'}), 401
    
    # 检查管理员权限
    if not is_admin_user():
        return jsonify({'success': False, 'error': '需要管理员权限'}), 403
    
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        roles = data.get('roles', [])
        
        if not username or not password:
            return jsonify({'success': False, 'error': '用户名和密码不能为空'}), 400
            
        if User.query.filter_by(username=username).first():
            return jsonify({'success': False, 'error': '用户名已存在'}), 400
            
        user = User(username=username)
        user.set_password(password)
        user.roles = roles
        db.session.add(user)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"创建用户失败: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/users/<username>', methods=['DELETE'])
def delete_user(username):
    """删除用户"""
    # 检查认证和TOTP验证
    if not (current_user.is_authenticated or session.get('kerberos_authenticated')):
        return jsonify({'success': False, 'error': '请先登录'}), 401
    
    if not session.get('totp_verified'):
        return jsonify({'success': False, 'error': '请先完成二次验证'}), 401
    
    # 检查管理员权限
    if not is_admin_user():
        return jsonify({'success': False, 'error': '需要管理员权限'}), 403
    
    try:
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({'success': False, 'error': '用户不存在'}), 404
            
        # 防止删除最后一个管理员账户
        if user.has_role('admin'):
            admin_count = User.query.filter(User.roles.contains('admin')).count()
            if admin_count <= 1:
                return jsonify({'success': False, 'error': '不能删除唯一的管理员账户'}), 400
        
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"删除用户失败: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/service_management')
def service_management():
    """服务管理页面"""
    # 检查认证和TOTP验证
    if not (current_user.is_authenticated or session.get('kerberos_authenticated')):
        flash('请先登录', 'warning')
        return redirect(url_for('auth_choice'))
    
    if not session.get('totp_verified'):
        flash('请先完成二次验证', 'warning')
        return redirect(url_for('auth_choice'))
    
    return render_template('service_management.html')

@app.route('/security')
def security_settings():
    """安全设置页面"""
    # 检查认证和TOTP验证
    if not (current_user.is_authenticated or session.get('kerberos_authenticated')):
        flash('请先登录', 'warning')
        return redirect(url_for('auth_choice'))
    
    if not session.get('totp_verified'):
        flash('请先完成二次验证', 'warning')
        return redirect(url_for('auth_choice'))
    
    # 检查管理员权限
    if not is_admin_user():
        flash('需要管理员权限才能访问此页面', 'danger')
        return redirect(url_for('dashboard'))
    
    return render_template('security_settings.html')

@app.route('/system')
def system_settings():
    """系统设置页面"""
    # 检查认证和TOTP验证
    if not (current_user.is_authenticated or session.get('kerberos_authenticated')):
        flash('请先登录', 'warning')
        return redirect(url_for('auth_choice'))
    
    if not session.get('totp_verified'):
        flash('请先完成二次验证', 'warning')
        return redirect(url_for('auth_choice'))
    
    # 检查管理员权限
    if not is_admin_user():
        flash('需要管理员权限才能访问此页面', 'danger')
        return redirect(url_for('dashboard'))
    
    return render_template('system_settings.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash('您已成功退出登录', 'success')
    return redirect(url_for('auth_choice'))  # 修改为重定向到认证选择页面

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # 获取请求数据
        if request.is_json:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
            confirm_password = data.get('confirm_password')
            email = data.get('email', '').strip()
            realm = data.get('realm', 'HADOOP.COM')
        else:
            username = request.form.get('username')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            email = request.form.get('email', '').strip()
            realm = request.form.get('realm', 'HADOOP.COM')
        
        # 检查是否是管理员在添加用户
        is_admin_creating = is_admin_user()
        
        # 简单表单验证
        if not username or not password:
            error_msg = '用户名和密码不能为空'
            if is_admin_creating:
                return jsonify({'success': False, 'error': error_msg}), 400
            flash(error_msg, 'danger')
            return render_template('register.html')
            
        if password != confirm_password:
            error_msg = '两次输入的密码不一致'
            if is_admin_creating:
                return jsonify({'success': False, 'error': error_msg}), 400
            flash(error_msg, 'danger')
            return render_template('register.html')
            
        # 检查用户名是否已存在
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            error_msg = '用户名已存在'
            if is_admin_creating:
                return jsonify({'success': False, 'error': error_msg}), 400
            flash(error_msg, 'danger')
            return render_template('register.html')
        
        # 只有当提供了电子邮件时才检查是否已存在
        if email:
            existing_email = User.query.filter_by(email=email).first()
            if existing_email:
                error_msg = '电子邮件地址已被使用'
                if is_admin_creating:
                    return jsonify({'success': False, 'error': error_msg}), 400
                flash(error_msg, 'danger')
                return render_template('register.html')
        
        try:
            # 创建新用户
            new_user = User(username=username, email=email if email else None, is_admin=False, realm=realm)
            new_user.set_password(password)
            
            # 生成TOTP密钥
            totp = TOTP()
            new_user.totp_secret = totp.secret
            
            db.session.add(new_user)
            db.session.commit()
            
            # 同时在Kerberos KDC中创建主体
            try:
                app.logger.info(f"正在KDC中创建主体: {username}@{realm}")
                kerberos_result = kerberos_auth.create_principal(username, password, realm)
                if kerberos_result:
                    app.logger.info(f"成功在KDC中创建主体: {username}@{realm}")
                    success_msg = '注册成功，已同步创建Kerberos主体'
                else:
                    app.logger.warning(f"在KDC中创建主体失败: {username}@{realm}")
                    success_msg = '注册成功，但Kerberos主体创建失败，可能无法使用Kerberos认证'
            except Exception as e:
                app.logger.error(f"创建Kerberos主体时出错: {str(e)}")
                success_msg = '注册成功，但Kerberos主体创建出错'
            
            if is_admin_creating:
                app.logger.info(f"管理员创建用户成功: {username}")
                return jsonify({
                    'success': True,
                    'message': success_msg,
                    'user': {
                        'id': new_user.id,
                        'username': new_user.username,
                        'email': new_user.email,
                        'is_admin': new_user.is_admin,
                        'is_active': new_user.is_active,
                        'totp_secret': new_user.totp_secret
                    }
                }), 200
            
            flash(success_msg, 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"用户注册失败: {str(e)}")
            error_msg = '注册过程中发生错误，请稍后再试'
            if is_admin_creating:
                app.logger.error(f"管理员创建用户失败: {username}, 错误: {str(e)}")
                return jsonify({
                    'success': False,
                    'error': error_msg
                }), 500
            flash(error_msg, 'danger')
            return render_template('register.html')
    
    # GET 请求直接返回注册页面
    return render_template('register.html')

# Kerberos认证视图
@app.route('/kerberos/login', methods=['GET', 'POST'])
def kerberos_login():
    if request.method == 'POST':
        principal = request.form.get('principal')
        password = request.form.get('password')
        realm = request.form.get('realm', 'HADOOP.COM')
        remember = 'remember' in request.form
        
        # 使用模拟认证（开发环境）
        if kerberos_auth.simulate_auth(principal, password, realm):
            # 提取用户名（去掉@realm部分）
            username = principal.split('@')[0] if '@' in principal else principal
            
            # 查找或创建用户记录，用于TOTP验证
            user = User.query.filter_by(username=username).first()
            if not user:
                # 如果用户不存在，创建一个新用户记录用于TOTP
                user = User(username=username, realm=realm)
                # 设置一个随机密码，因为我们不需要密码认证
                random_password = secrets.token_hex(16)
                user.set_password(random_password)
                db.session.add(user)
            
            # 更新最后登录时间和领域
            user.last_login = datetime.now()
            user.last_realm = realm
            db.session.commit()
            
            # 如果用户没有TOTP密钥，则生成一个
            if not user.totp_secret:
                totp = TOTP()
                user.totp_secret = totp.secret
                db.session.commit()
            
            # 临时存储Kerberos认证信息
            session['temp_kerberos_authenticated'] = True
            session['temp_kerberos_principal'] = f"{principal}@{realm}" if '@' not in principal else principal
            session['temp_kerberos_login_time'] = datetime.now().isoformat()
            session['temp_kerberos_expiry'] = (datetime.now() + timedelta(hours=10)).isoformat()
            session['temp_kerberos_realm'] = realm  # 添加领域到会话
            
            # 设置用户ID，以便在TOTP验证时使用
            session['user_id_for_totp'] = user.id
            session.modified = True
            
            # 重定向到统一的TOTP验证页面
            return redirect(url_for('verify_totp'))
        else:
            flash('Kerberos认证失败，请检查您的主体名称和密码', 'danger')
    
    return render_template('kerberos_login.html', error=None)

@app.route('/kerberos/dashboard')
def kerberos_dashboard():
    # 验证Kerberos认证状态
    if not session.get('kerberos_authenticated'):
        flash('请先完成Kerberos认证', 'warning')
        return redirect(url_for('kerberos_login'))
    
    # 重定向到统一的仪表板
    return redirect(url_for('dashboard'))

@app.route('/kerberos/logout')
def kerberos_logout():
    # 清除Kerberos票据
    kerberos_auth.logout()
    # 清除会话
    session.clear()
    flash('已成功销毁Kerberos票据，您已安全退出', 'success')
    return redirect(url_for('auth_choice'))  # 修改为重定向到认证选择页面

@app.route('/api/service/status')
def get_service_status():
    """获取所有服务的状态"""
    # 检查认证和TOTP验证
    if not (current_user.is_authenticated or session.get('kerberos_authenticated')):
        return jsonify({'success': False, 'error': '请先登录'}), 401
    
    if not session.get('totp_verified'):
        return jsonify({'success': False, 'error': '请先完成二次验证'}), 401
    
    try:
        app.logger.info("正在获取服务状态...")
        config_path = os.path.join(app.root_path, 'config')
        manager = HadoopServiceManager(config_path)
        
        # 获取用户名
        username = None
        if session.get('kerberos_authenticated'):
            principal = session.get('kerberos_principal')
            username = principal.split('@')[0] if '@' in principal else principal
        else:
            username = current_user.username
            
        status = manager.check_all_services(username)
        app.logger.info(f"服务状态: {status}")
        return jsonify({'success': True, 'status': status})
    except Exception as e:
        app.logger.error(f"获取服务状态失败: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/service/start/<service>', methods=['POST'])
def start_service(service):
    """启动指定服务"""
    # 检查认证和TOTP验证
    if not (current_user.is_authenticated or session.get('kerberos_authenticated')):
        return jsonify({'success': False, 'error': '请先登录'}), 401
    
    if not session.get('totp_verified'):
        return jsonify({'success': False, 'error': '请先完成二次验证'}), 401
    
    try:
        app.logger.info(f"正在启动服务: {service}")
        config_path = os.path.join(app.root_path, 'config')
        manager = HadoopServiceManager(config_path)
        
        # 获取用户名
        username = None
        if session.get('kerberos_authenticated'):
            principal = session.get('kerberos_principal')
            username = principal.split('@')[0] if '@' in principal else principal
        else:
            username = current_user.username
            
        if manager.start_service(service, username):
            app.logger.info(f"服务 {service} 启动成功")
            return jsonify({'success': True})
        app.logger.error(f"服务 {service} 启动失败")
        return jsonify({'success': False, 'error': '启动服务失败'}), 500
    except Exception as e:
        app.logger.error(f"启动服务 {service} 失败: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/service/stop/<service>', methods=['POST'])
def stop_service(service):
    """停止指定服务"""
    # 检查认证和TOTP验证
    if not (current_user.is_authenticated or session.get('kerberos_authenticated')):
        return jsonify({'success': False, 'error': '请先登录'}), 401
    
    if not session.get('totp_verified'):
        return jsonify({'success': False, 'error': '请先完成二次验证'}), 401
    
    try:
        app.logger.info(f"正在停止服务: {service}")
        config_path = os.path.join(app.root_path, 'config')
        manager = HadoopServiceManager(config_path)
        
        # 获取用户名
        username = None
        if session.get('kerberos_authenticated'):
            principal = session.get('kerberos_principal')
            username = principal.split('@')[0] if '@' in principal else principal
        else:
            username = current_user.username
            
        if manager.stop_service(service, username):
            app.logger.info(f"服务 {service} 停止成功")
            return jsonify({'success': True})
        app.logger.error(f"服务 {service} 停止失败")
        return jsonify({'success': False, 'error': '停止服务失败'}), 500
    except Exception as e:
        app.logger.error(f"停止服务 {service} 失败: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/service/start-all', methods=['POST'])
def start_all_services():
    """启动所有服务"""
    # 检查认证和TOTP验证
    if not (current_user.is_authenticated or session.get('kerberos_authenticated')):
        return jsonify({'success': False, 'error': '请先登录'}), 401
    
    if not session.get('totp_verified'):
        return jsonify({'success': False, 'error': '请先完成二次验证'}), 401
    
    try:
        config_path = os.path.join(app.root_path, 'config')
        manager = HadoopServiceManager(config_path)
        
        # 获取用户名
        username = None
        if session.get('kerberos_authenticated'):
            principal = session.get('kerberos_principal')
            username = principal.split('@')[0] if '@' in principal else principal
        else:
            username = current_user.username
            
        if manager.start_all_services(username):
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': '启动所有服务失败'}), 500
    except Exception as e:
        app.logger.error(f"启动所有服务失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/service/stop-all', methods=['POST'])
def stop_all_services():
    """停止所有服务"""
    # 检查认证和TOTP验证
    if not (current_user.is_authenticated or session.get('kerberos_authenticated')):
        return jsonify({'success': False, 'error': '请先登录'}), 401
    
    if not session.get('totp_verified'):
        return jsonify({'success': False, 'error': '请先完成二次验证'}), 401
    
    try:
        config_path = os.path.join(app.root_path, 'config')
        manager = HadoopServiceManager(config_path)
        
        # 获取用户名
        username = None
        if session.get('kerberos_authenticated'):
            principal = session.get('kerberos_principal')
            username = principal.split('@')[0] if '@' in principal else principal
        else:
            username = current_user.username
            
        if manager.stop_all_services(username):
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': '停止所有服务失败'}), 500
    except Exception as e:
        app.logger.error(f"停止所有服务失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/kerberos/mode', methods=['POST'])
def set_kerberos_mode():
    """设置Kerberos认证模式（开发/生产）"""
    # 检查认证和TOTP验证
    if not (current_user.is_authenticated or session.get('kerberos_authenticated')):
        return jsonify({'success': False, 'error': '请先登录'}), 401
    
    if not session.get('totp_verified'):
        return jsonify({'success': False, 'error': '请先完成二次验证'}), 401
    
    # 检查管理员权限
    if not is_admin_user():
        return jsonify({'success': False, 'error': '需要管理员权限'}), 403
    
    try:
        data = request.get_json()
        dev_mode = data.get('dev_mode', True)
        
        # 设置认证模式
        kerberos_auth.set_mode(dev_mode)
        
        mode_name = '开发模式' if dev_mode else '生产模式'
        return jsonify({
            'success': True, 
            'message': f'已切换到{mode_name}',
            'dev_mode': dev_mode
        })
    except Exception as e:
        app.logger.error(f"设置Kerberos认证模式失败: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/kerberos/mode', methods=['GET'])
def get_kerberos_mode():
    """获取当前Kerberos认证模式"""
    # 检查认证和TOTP验证
    if not (current_user.is_authenticated or session.get('kerberos_authenticated')):
        return jsonify({'success': False, 'error': '请先登录'}), 401
    
    if not session.get('totp_verified'):
        return jsonify({'success': False, 'error': '请先完成二次验证'}), 401
    
    dev_mode = kerberos_auth.dev_mode
    mode_name = '开发模式' if dev_mode else '生产模式'
    return jsonify({
        'success': True,
        'dev_mode': dev_mode,
        'mode_name': mode_name
    })

@app.route('/api/admin/users/search', methods=['GET'])
def search_users():
    """搜索用户"""
    # 检查认证和TOTP验证
    if not (current_user.is_authenticated or session.get('kerberos_authenticated')):
        return jsonify({'success': False, 'error': '请先登录'}), 401
    
    if not session.get('totp_verified'):
        return jsonify({'success': False, 'error': '请先完成二次验证'}), 401
    
    # 检查管理员权限
    if not is_admin_user():
        return jsonify({'success': False, 'error': '需要管理员权限'}), 403
    
    try:
        # 获取搜索关键词
        query = request.args.get('query', '')
        
        # 如果没有搜索关键词，返回所有用户
        if not query:
            users = User.query.all()
        else:
            # 使用模糊匹配搜索用户名和邮箱
            users = User.query.filter(
                db.or_(
                    User.username.ilike(f'%{query}%'),
                    User.email.ilike(f'%{query}%') if User.email else False
                )
            ).all()
        
        # 格式化用户数据
        user_list = []
        for user in users:
            user_list.append({
                'id': user.id,
                'username': user.username,
                'email': user.email or '未设置',
                'password_hash': user.password_hash,
                'totp_secret': user.totp_secret or '未设置',
                'roles': user.roles,
                'is_admin': user.is_admin,
                'is_active': user.is_active,
                'last_login': user.last_login.strftime('%Y-%m-%d %H:%M') if user.last_login else '从未登录'
            })
        
        return jsonify({
            'success': True,
            'users': user_list
        })
    except Exception as e:
        app.logger.error(f"搜索用户失败: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/services/status')
@login_required
def get_services_status():
    """获取服务状态"""
    # 获取用户角色
    user = current_user
    is_admin = is_admin_user()
    
    # 获取用户有权限的服务
    available_services = []
    if is_admin:
        # 管理员可以看到所有服务
        available_services = list(SERVICE_PERMISSIONS.keys())
    else:
        # 普通用户只能看到其角色对应的服务
        for service, roles in SERVICE_PERMISSIONS.items():
            if any(role in user.roles.split(',') for role in roles):
                available_services.append(service)
    
    # 返回服务状态
    status = {}
    for service in available_services:
        status[service] = {
            'status': 'running' if service != 'hiveserver2' else 'stopped',
            'has_permission': True
        }
    
    return jsonify(status)

@app.route('/api/services/<service_name>/<action>', methods=['POST'])
@login_required
def control_service(service_name, action):
    """控制服务（启动/停止/重启）"""
    # 获取用户角色
    user = current_user
    is_admin = is_admin_user()
    
    # 检查权限
    has_permission = False
    if is_admin:
        has_permission = True
    else:
        service_roles = SERVICE_PERMISSIONS.get(service_name, [])
        has_permission = any(role in user.roles.split(',') for role in service_roles)
    
    if not has_permission:
        return jsonify({'error': '没有权限操作该服务'}), 403
        
    if action not in ['start', 'stop', 'restart']:
        return jsonify({'error': '无效的操作'}), 400
        
    # 这里应该实现实际的服务控制逻辑
    # 目前返回模拟的成功响应
    return jsonify({
        'success': True,
        'message': f'服务 {service_name} {action} 操作已执行',
        'status': 'running' if action in ['start', 'restart'] else 'stopped'
    })

@app.route('/api/services/<service_name>/logs')
@login_required
def get_service_logs(service_name):
    """获取服务日志"""
    # 获取用户角色
    user = current_user
    is_admin = is_admin_user()
    
    # 检查权限
    has_permission = False
    if is_admin:
        has_permission = True
    else:
        service_roles = SERVICE_PERMISSIONS.get(service_name, [])
        has_permission = any(role in user.roles.split(',') for role in service_roles)
    
    if not has_permission:
        return jsonify({'error': '没有权限查看该服务日志'}), 403
        
    # 这里应该实现实际的日志获取逻辑
    # 目前返回模拟的日志数据
    logs = [
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: {service_name} 服务运行中...",
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: 内存使用率: {random.randint(30, 80)}%",
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: 处理请求..."
    ]
    
    return jsonify({'logs': logs})

if __name__ == '__main__':
    with app.app_context():
        if init_db():
            logger.info("数据库初始化成功，正在启动应用...")
            # 初始化Kerberos认证服务
            kerberos_auth = KerberosAuth()
            kerberos_auth.conf_file = KRB5_CONFIG
            kerberos_auth.kdc_conf = KRB5_KDC_PROFILE
            kerberos_auth.kdc_db_path = KDC_DB_PATH
            kerberos_auth.dev_mode = True
            kerberos_auth.initialize()
            app.run(host='0.0.0.0', port=5002, debug=True)
        else:
            logger.error("无法初始化数据库，应用无法启动") 