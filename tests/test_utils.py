"""测试工具类"""

import os
import tempfile
import shutil
from typing import Dict, Any, Optional
from unittest.mock import MagicMock

from web.models import db, User, Role, Permission
from web.app import create_app
from tests.test_data import (
    TEST_USERS,
    TEST_ROLES,
    TEST_PERMISSIONS,
    TEST_ENV
)

class TestUtils:
    """测试工具类"""
    
    @staticmethod
    def create_test_app():
        """创建测试应用实例"""
        # 创建临时目录作为测试配置目录
        test_config_dir = tempfile.mkdtemp()
        
        # 设置测试环境变量
        for key, value in TEST_ENV.items():
            os.environ[key] = value
            
        # 创建测试应用
        app = create_app()
        app.config.update({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'WTF_CSRF_ENABLED': False,
            'SECRET_KEY': 'test_secret_key'
        })
        
        return app, test_config_dir
        
    @staticmethod
    def init_test_db(app):
        """初始化测试数据库"""
        with app.app_context():
            # 创建所有表
            db.create_all()
            
            # 创建权限
            for perm_data in TEST_PERMISSIONS.values():
                perm = Permission(
                    name=perm_data['name'],
                    description=perm_data['description']
                )
                db.session.add(perm)
            db.session.commit()
            
            # 创建角色
            for role_data in TEST_ROLES.values():
                role = Role(
                    name=role_data['name'],
                    description=role_data['description']
                )
                # 添加权限
                for perm_name in role_data['permissions']:
                    perm = Permission.query.filter_by(name=perm_name).first()
                    if perm:
                        role.permissions.append(perm)
                db.session.add(role)
            db.session.commit()
            
            # 创建用户
            for user_data in TEST_USERS.values():
                user = User(
                    username=user_data['username'],
                    is_active=user_data['is_active']
                )
                user.set_password(user_data['password'])
                # 添加角色
                for role_name in user_data['roles']:
                    role = Role.query.filter_by(name=role_name).first()
                    if role:
                        user.roles.append(role)
                db.session.add(user)
            db.session.commit()
    
    @staticmethod
    def cleanup_test_env(test_config_dir: str):
        """清理测试环境"""
        # 删除临时目录
        if os.path.exists(test_config_dir):
            shutil.rmtree(test_config_dir)
            
        # 清理环境变量
        for key in TEST_ENV.keys():
            if key in os.environ:
                del os.environ[key]
    
    @staticmethod
    def create_mock_hadoop_manager() -> MagicMock:
        """创建模拟的Hadoop管理器"""
        mock_manager = MagicMock()
        
        # 模拟初始化集群
        mock_manager.initialize_cluster.return_value = (True, None)
        
        # 模拟启动服务
        mock_manager.start_services.return_value = (True, None)
        
        # 模拟获取服务状态
        mock_manager.get_service_status.return_value = {
            'namenode': 'RUNNING',
            'datanode': 'RUNNING',
            'resourcemanager': 'RUNNING',
            'nodemanager': 'RUNNING',
            'hiveserver2': 'RUNNING'
        }
        
        # 模拟执行HDFS命令
        mock_manager.execute_hdfs_command.return_value = (True, 'Command executed successfully', None)
        
        # 模拟提交YARN应用
        mock_manager.submit_yarn_application.return_value = (True, 'application_123456789', None)
        
        # 模拟执行Hive查询
        mock_manager.execute_hive_query.return_value = (True, [{'id': 1, 'name': 'test'}], None)
        
        return mock_manager
    
    @staticmethod
    def login_test_client(client, username: str, password: str) -> Dict[str, Any]:
        """登录测试客户端"""
        response = client.post('/login', json={
            'username': username,
            'password': password
        })
        return response.get_json()
    
    @staticmethod
    def verify_totp_test_client(client, totp_code: str) -> Dict[str, Any]:
        """验证TOTP"""
        response = client.post('/verify_totp', json={
            'totp_code': totp_code
        })
        return response.get_json()
    
    @staticmethod
    def get_test_headers(token: Optional[str] = None) -> Dict[str, str]:
        """获取测试请求头"""
        headers = {
            'Content-Type': 'application/json'
        }
        if token:
            headers['Authorization'] = f'Bearer {token}'
        return headers 