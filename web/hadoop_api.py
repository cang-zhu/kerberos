from flask import Blueprint, request, jsonify, current_app
from functools import wraps
from typing import Dict, Optional, Tuple
import json
import os

from hadoop.manager import HadoopManager

# 创建Blueprint
hadoop_api = Blueprint('hadoop_api', __name__)

# 初始化Hadoop管理器
hadoop_manager = None

def init_hadoop_manager(config_dir: str):
    """
    初始化Hadoop管理器
    """
    global hadoop_manager
    hadoop_manager = HadoopManager(config_dir)

def require_hadoop_auth(f):
    """
    Hadoop认证装饰器
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': '未提供认证信息'}), 401
            
        try:
            # 从session中获取用户信息
            username = request.headers.get('X-Hadoop-User')
            if not username:
                return jsonify({'error': '未提供用户信息'}), 401
                
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({'error': str(e)}), 401
    return decorated

@hadoop_api.route('/cluster/init', methods=['POST'])
@require_hadoop_auth
def initialize_cluster():
    """
    初始化Hadoop集群
    """
    try:
        config = request.json
        if not config:
            return jsonify({'error': '未提供集群配置'}), 400
            
        success, error = hadoop_manager.initialize_cluster(config)
        if not success:
            return jsonify({'error': error}), 500
            
        return jsonify({'message': '集群初始化成功'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@hadoop_api.route('/cluster/status', methods=['GET'])
@require_hadoop_auth
def get_cluster_status():
    """
    获取集群状态
    """
    try:
        status = hadoop_manager.get_service_status()
        return jsonify({'status': status})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@hadoop_api.route('/hdfs/command', methods=['POST'])
@require_hadoop_auth
def execute_hdfs_command():
    """
    执行HDFS命令
    """
    try:
        data = request.json
        if not data or 'command' not in data:
            return jsonify({'error': '未提供HDFS命令'}), 400
            
        username = request.headers.get('X-Hadoop-User')
        success, output, error = hadoop_manager.execute_hdfs_command(
            username,
            data['command']
        )
        
        if not success:
            return jsonify({'error': error}), 500
            
        return jsonify({'output': output})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@hadoop_api.route('/yarn/submit', methods=['POST'])
@require_hadoop_auth
def submit_yarn_application():
    """
    提交YARN应用
    """
    try:
        data = request.json
        if not data or 'application_path' not in data:
            return jsonify({'error': '未提供应用程序路径'}), 400
            
        username = request.headers.get('X-Hadoop-User')
        success, app_id, error = hadoop_manager.submit_yarn_application(
            username,
            data['application_path'],
            data.get('args', [])
        )
        
        if not success:
            return jsonify({'error': error}), 500
            
        return jsonify({'application_id': app_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@hadoop_api.route('/hive/query', methods=['POST'])
@require_hadoop_auth
def execute_hive_query():
    """
    执行Hive查询
    """
    try:
        data = request.json
        if not data or 'query' not in data:
            return jsonify({'error': '未提供HiveQL查询'}), 400
            
        username = request.headers.get('X-Hadoop-User')
        success, result, error = hadoop_manager.execute_hive_query(
            username,
            data['query']
        )
        
        if not success:
            return jsonify({'error': error}), 500
            
        return jsonify({'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@hadoop_api.route('/auth/test', methods=['POST'])
def test_hadoop_auth():
    """
    测试Hadoop认证
    """
    try:
        data = request.json
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({'error': '未提供用户名或密码'}), 400
            
        success, error = hadoop_manager.authenticate_user(
            data['username'],
            data['password']
        )
        
        if not success:
            return jsonify({'error': error}), 401
            
        return jsonify({'message': '认证成功'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 错误处理
@hadoop_api.errorhandler(Exception)
def handle_error(error):
    """
    全局错误处理
    """
    return jsonify({'error': str(error)}), 500 