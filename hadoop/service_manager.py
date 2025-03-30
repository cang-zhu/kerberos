import subprocess
import logging
from typing import Dict, List, Optional
import os
import requests
from urllib.parse import urljoin
import time

class HadoopServiceManager:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.logger = logging.getLogger(__name__)
        
        # 伪分布式环境服务配置
        self.services = {
            'namenode': {
                'host': 'localhost',
                'port': 9870,
                'start_cmd': 'hdfs --daemon start namenode',
                'stop_cmd': 'hdfs --daemon stop namenode',
                'status_cmd': 'jps | grep NameNode',
                'web_url': 'http://localhost:9870',
                'required_role': 'hdfs_admin'
            },
            'datanode': {
                'host': 'localhost',
                'port': 9864,
                'start_cmd': 'hdfs --daemon start datanode',
                'stop_cmd': 'hdfs --daemon stop datanode',
                'status_cmd': 'jps | grep DataNode',
                'web_url': 'http://localhost:9864',
                'required_role': 'hdfs_admin'
            },
            'resourcemanager': {
                'host': 'localhost',
                'port': 8088,
                'start_cmd': 'yarn --daemon start resourcemanager',
                'stop_cmd': 'yarn --daemon stop resourcemanager',
                'status_cmd': 'jps | grep ResourceManager',
                'web_url': 'http://localhost:8088',
                'required_role': 'yarn_admin'
            },
            'nodemanager': {
                'host': 'localhost',
                'port': 8042,
                'start_cmd': 'yarn --daemon start nodemanager',
                'stop_cmd': 'yarn --daemon stop nodemanager',
                'status_cmd': 'jps | grep NodeManager',
                'web_url': 'http://localhost:8042',
                'required_role': 'yarn_admin'
            },
            'hiveserver2': {
                'host': 'localhost',
                'port': 10000,
                'start_cmd': '$HIVE_HOME/bin/hiveserver2',
                'stop_cmd': 'pkill -f hiveserver2',
                'status_cmd': 'jps | grep HiveServer2',
                'jdbc_url': 'jdbc:hive2://localhost:10000',
                'required_role': 'hive_admin'
            }
        }

    def check_service_health(self, service_name: str) -> bool:
        """检查服务健康状态"""
        service = self.services.get(service_name)
        if not service:
            return False

        try:
            # 检查进程是否存在
            result = subprocess.run(
                service['status_cmd'],
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if result.returncode != 0:
                return False

            # 检查Web界面是否可访问（如果有）
            if 'web_url' in service:
                try:
                    response = requests.get(service['web_url'], timeout=5)
                    return response.status_code == 200
                except:
                    return False

            return True
        except Exception as e:
            self.logger.error(f"检查服务 {service_name} 状态失败: {e}")
            return False

    def execute_command(self, command: str) -> bool:
        """在本地执行命令"""
        try:
            # 设置环境变量
            env = os.environ.copy()
            if 'HADOOP_HOME' not in env:
                env['HADOOP_HOME'] = '/usr/local/hadoop'  # 根据实际安装路径调整
            if 'HIVE_HOME' not in env:
                env['HIVE_HOME'] = '/usr/local/hive'  # 根据实际安装路径调整
            if 'JAVA_HOME' not in env:
                env['JAVA_HOME'] = '/usr/lib/jvm/java-8-openjdk'  # 根据实际安装路径调整

            result = subprocess.run(
                command,
                shell=True,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if result.returncode != 0:
                self.logger.error(f"命令执行失败: {result.stderr}")
                return False
            return True
        except Exception as e:
            self.logger.error(f"执行命令失败: {e}")
            return False

    def check_user_permission(self, username: str, service_name: str) -> bool:
        """检查用户是否有权限操作服务"""
        service = self.services.get(service_name)
        if not service:
            return False
            
        required_role = service.get('required_role')
        if not required_role:
            return False
            
        # TODO: 从数据库或其他地方检查用户角色
        # 这里暂时返回True，您需要根据实际情况实现权限检查
        return True

    def start_service(self, service_name: str, username: str) -> bool:
        """启动指定服务"""
        if not self.check_user_permission(username, service_name):
            self.logger.warning(f"用户 {username} 没有权限启动服务 {service_name}")
            return False

        service = self.services.get(service_name)
        if not service:
            self.logger.error(f"未知服务: {service_name}")
            return False

        if self.check_service_health(service_name):
            self.logger.info(f"服务 {service_name} 已经在运行")
            return True

        return self.execute_command(service['start_cmd'])

    def stop_service(self, service_name: str, username: str) -> bool:
        """停止指定服务"""
        if not self.check_user_permission(username, service_name):
            self.logger.warning(f"用户 {username} 没有权限停止服务 {service_name}")
            return False

        service = self.services.get(service_name)
        if not service:
            self.logger.error(f"未知服务: {service_name}")
            return False

        return self.execute_command(service['stop_cmd'])

    def check_service_status(self, service_name: str) -> Dict[str, bool]:
        """检查服务状态"""
        service = self.services.get(service_name)
        if not service:
            return {'running': False, 'healthy': False}

        is_running = self.check_service_health(service_name)
        return {
            'running': is_running,
            'healthy': is_running,
            'web_url': service.get('web_url'),
            'jdbc_url': service.get('jdbc_url')
        }

    def check_all_services(self, username: Optional[str] = None) -> Dict[str, Dict[str, bool]]:
        """检查所有服务的状态"""
        status = {}
        for service_name in self.services:
            if username and not self.check_user_permission(username, service_name):
                continue
            status[service_name] = self.check_service_status(service_name)
        return status

    def start_all_services(self, username: str) -> bool:
        """启动所有服务"""
        success = True
        # 按照依赖关系顺序启动服务
        service_order = ['namenode', 'datanode', 'resourcemanager', 'nodemanager', 'hiveserver2']
        for service in service_order:
            if not self.start_service(service, username):
                success = False
        return success

    def stop_all_services(self, username: str) -> bool:
        """停止所有服务"""
        success = True
        # 按照依赖关系的相反顺序停止服务
        service_order = ['hiveserver2', 'nodemanager', 'resourcemanager', 'datanode', 'namenode']
        for service in service_order:
            if not self.stop_service(service, username):
                success = False
        return success 