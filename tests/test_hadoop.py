"""Hadoop功能测试"""

import unittest
from unittest.mock import patch
from tests.test_utils import TestUtils
from tests.test_data import (
    TEST_USERS,
    TEST_CLUSTER_CONFIG,
    TEST_HDFS_COMMANDS,
    TEST_YARN_APPLICATIONS,
    TEST_HIVE_QUERIES
)

class TestHadoopIntegration(unittest.TestCase):
    """Hadoop集成测试类"""
    
    def setUp(self):
        """测试前准备"""
        # 创建测试应用
        self.app, self.test_config_dir = TestUtils.create_test_app()
        self.client = self.app.test_client()
        
        # 初始化测试数据库
        TestUtils.init_test_db(self.app)
        
        # 创建模拟的Hadoop管理器
        self.mock_hadoop_manager = TestUtils.create_mock_hadoop_manager()
        
        # 登录管理员用户
        admin_data = TEST_USERS['admin']
        response = TestUtils.login_test_client(
            self.client,
            admin_data['username'],
            admin_data['password']
        )
        self.admin_token = response.get('token')
        
        # 登录HDFS用户
        hdfs_user_data = TEST_USERS['hdfs_user']
        response = TestUtils.login_test_client(
            self.client,
            hdfs_user_data['username'],
            hdfs_user_data['password']
        )
        self.hdfs_token = response.get('token')
        
        # 登录YARN用户
        yarn_user_data = TEST_USERS['yarn_user']
        response = TestUtils.login_test_client(
            self.client,
            yarn_user_data['username'],
            yarn_user_data['password']
        )
        self.yarn_token = response.get('token')
        
        # 登录Hive用户
        hive_user_data = TEST_USERS['hive_user']
        response = TestUtils.login_test_client(
            self.client,
            hive_user_data['username'],
            hive_user_data['password']
        )
        self.hive_token = response.get('token')
    
    def tearDown(self):
        """测试后清理"""
        TestUtils.cleanup_test_env(self.test_config_dir)
    
    @patch('hadoop.manager.HadoopManager')
    def test_cluster_initialization(self, mock_manager_class):
        """测试集群初始化"""
        mock_manager_class.return_value = self.mock_hadoop_manager
        
        # 测试未授权访问
        response = self.client.post('/api/hadoop/init',
            json=TEST_CLUSTER_CONFIG
        )
        self.assertEqual(response.status_code, 401)
        
        # 测试无权限用户访问
        headers = TestUtils.get_test_headers(self.hdfs_token)
        response = self.client.post('/api/hadoop/init',
            json=TEST_CLUSTER_CONFIG,
            headers=headers
        )
        self.assertEqual(response.status_code, 403)
        
        # 测试管理员初始化集群
        headers = TestUtils.get_test_headers(self.admin_token)
        response = self.client.post('/api/hadoop/init',
            json=TEST_CLUSTER_CONFIG,
            headers=headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        
        # 验证调用
        self.mock_hadoop_manager.initialize_cluster.assert_called_once_with(TEST_CLUSTER_CONFIG)
    
    @patch('hadoop.manager.HadoopManager')
    def test_service_management(self, mock_manager_class):
        """测试服务管理"""
        mock_manager_class.return_value = self.mock_hadoop_manager
        
        # 测试启动服务
        headers = TestUtils.get_test_headers(self.admin_token)
        response = self.client.post('/api/hadoop/services/start',
            headers=headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        
        # 测试获取服务状态
        response = self.client.get('/api/hadoop/services/status',
            headers=headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status']['namenode'], 'RUNNING')
        
        # 验证调用
        self.mock_hadoop_manager.start_services.assert_called_once()
        self.mock_hadoop_manager.get_service_status.assert_called_once()
    
    @patch('hadoop.manager.HadoopManager')
    def test_hdfs_operations(self, mock_manager_class):
        """测试HDFS操作"""
        mock_manager_class.return_value = self.mock_hadoop_manager
        
        # 测试执行HDFS命令
        headers = TestUtils.get_test_headers(self.hdfs_token)
        for cmd_name, cmd in TEST_HDFS_COMMANDS.items():
            response = self.client.post('/api/hadoop/hdfs/execute',
                json={'command': cmd},
                headers=headers
            )
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertTrue(data['success'])
            self.assertEqual(data['result'], 'Command executed successfully')
        
        # 验证调用
        self.assertEqual(
            self.mock_hadoop_manager.execute_hdfs_command.call_count,
            len(TEST_HDFS_COMMANDS)
        )
    
    @patch('hadoop.manager.HadoopManager')
    def test_yarn_applications(self, mock_manager_class):
        """测试YARN应用"""
        mock_manager_class.return_value = self.mock_hadoop_manager
        
        # 测试提交YARN应用
        headers = TestUtils.get_test_headers(self.yarn_token)
        for app_name, app_data in TEST_YARN_APPLICATIONS.items():
            response = self.client.post('/api/hadoop/yarn/submit',
                json=app_data,
                headers=headers
            )
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertTrue(data['success'])
            self.assertEqual(data['application_id'], 'application_123456789')
        
        # 验证调用
        self.assertEqual(
            self.mock_hadoop_manager.submit_yarn_application.call_count,
            len(TEST_YARN_APPLICATIONS)
        )
    
    @patch('hadoop.manager.HadoopManager')
    def test_hive_queries(self, mock_manager_class):
        """测试Hive查询"""
        mock_manager_class.return_value = self.mock_hadoop_manager
        
        # 测试执行Hive查询
        headers = TestUtils.get_test_headers(self.hive_token)
        for query_name, query in TEST_HIVE_QUERIES.items():
            response = self.client.post('/api/hadoop/hive/execute',
                json={'query': query},
                headers=headers
            )
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertTrue(data['success'])
            self.assertEqual(len(data['results']), 1)
            self.assertEqual(data['results'][0]['id'], 1)
        
        # 验证调用
        self.assertEqual(
            self.mock_hadoop_manager.execute_hive_query.call_count,
            len(TEST_HIVE_QUERIES)
        )
    
    @patch('hadoop.manager.HadoopManager')
    def test_permission_control(self, mock_manager_class):
        """测试权限控制"""
        mock_manager_class.return_value = self.mock_hadoop_manager
        
        # 测试HDFS用户无法执行YARN操作
        headers = TestUtils.get_test_headers(self.hdfs_token)
        response = self.client.post('/api/hadoop/yarn/submit',
            json=TEST_YARN_APPLICATIONS['wordcount'],
            headers=headers
        )
        self.assertEqual(response.status_code, 403)
        
        # 测试YARN用户无法执行Hive操作
        headers = TestUtils.get_test_headers(self.yarn_token)
        response = self.client.post('/api/hadoop/hive/execute',
            json={'query': TEST_HIVE_QUERIES['select_data']},
            headers=headers
        )
        self.assertEqual(response.status_code, 403)
        
        # 测试Hive用户无法执行HDFS操作
        headers = TestUtils.get_test_headers(self.hive_token)
        response = self.client.post('/api/hadoop/hdfs/execute',
            json={'command': TEST_HDFS_COMMANDS['list_root']},
            headers=headers
        )
        self.assertEqual(response.status_code, 403)

if __name__ == '__main__':
    unittest.main() 