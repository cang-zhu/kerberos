import subprocess
import logging
from typing import Dict, List, Optional
import os

class HadoopServiceManager:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.logger = logging.getLogger(__name__)
        self.services = {
            'namenode': {
                'host': 'master-node',
                'start_cmd': 'hadoop-daemon.sh start namenode',
                'stop_cmd': 'hadoop-daemon.sh stop namenode',
                'status_cmd': 'jps | grep NameNode',
            },
            'datanode': {
                'hosts': ['slave-node1', 'slave-node2'],
                'start_cmd': 'hadoop-daemon.sh start datanode',
                'stop_cmd': 'hadoop-daemon.sh stop datanode',
                'status_cmd': 'jps | grep DataNode',
            },
            'resourcemanager': {
                'host': 'master-node',
                'start_cmd': 'yarn-daemon.sh start resourcemanager',
                'stop_cmd': 'yarn-daemon.sh stop resourcemanager',
                'status_cmd': 'jps | grep ResourceManager',
            },
            'nodemanager': {
                'hosts': ['slave-node1', 'slave-node2'],
                'start_cmd': 'yarn-daemon.sh start nodemanager',
                'stop_cmd': 'yarn-daemon.sh stop nodemanager',
                'status_cmd': 'jps | grep NodeManager',
            },
            'hiveserver2': {
                'host': 'master-node',
                'start_cmd': 'hiveserver2',
                'stop_cmd': 'pkill -f hiveserver2',
                'status_cmd': 'jps | grep HiveServer2',
            }
        }

    def execute_remote_command(self, host: str, command: str, user: str) -> bool:
        """
        在远程主机上执行命令
        
        Args:
            host: 主机名
            command: 要执行的命令
            user: 执行命令的用户
            
        Returns:
            bool: 命令是否执行成功
        """
        try:
            ssh_command = f'ssh {user}@{host} "source /etc/profile && {command}"'
            result = subprocess.run(ssh_command, shell=True, check=True)
            return result.returncode == 0
        except subprocess.CalledProcessError as e:
            self.logger.error(f"在{host}上执行命令失败: {e}")
            return False

    def start_service(self, service_name: str, user: str) -> bool:
        """
        启动指定的Hadoop服务
        
        Args:
            service_name: 服务名称
            user: 执行命令的用户
            
        Returns:
            bool: 服务是否成功启动
        """
        service = self.services.get(service_name)
        if not service:
            self.logger.error(f"未知服务: {service_name}")
            return False

        if 'host' in service:
            # 单节点服务
            return self.execute_remote_command(
                service['host'],
                service['start_cmd'],
                user
            )
        elif 'hosts' in service:
            # 多节点服务
            success = True
            for host in service['hosts']:
                if not self.execute_remote_command(host, service['start_cmd'], user):
                    success = False
            return success
        return False

    def stop_service(self, service_name: str, user: str) -> bool:
        """
        停止指定的Hadoop服务
        
        Args:
            service_name: 服务名称
            user: 执行命令的用户
            
        Returns:
            bool: 服务是否成功停止
        """
        service = self.services.get(service_name)
        if not service:
            self.logger.error(f"未知服务: {service_name}")
            return False

        if 'host' in service:
            # 单节点服务
            return self.execute_remote_command(
                service['host'],
                service['stop_cmd'],
                user
            )
        elif 'hosts' in service:
            # 多节点服务
            success = True
            for host in service['hosts']:
                if not self.execute_remote_command(host, service['stop_cmd'], user):
                    success = False
            return success
        return False

    def check_service_status(self, service_name: str, user: str) -> Dict[str, bool]:
        """
        检查指定服务的状态
        
        Args:
            service_name: 服务名称
            user: 执行命令的用户
            
        Returns:
            Dict[str, bool]: 各节点的服务状态
        """
        service = self.services.get(service_name)
        if not service:
            self.logger.error(f"未知服务: {service_name}")
            return {}

        status = {}
        if 'host' in service:
            # 单节点服务
            status[service['host']] = self.execute_remote_command(
                service['host'],
                service['status_cmd'],
                user
            )
        elif 'hosts' in service:
            # 多节点服务
            for host in service['hosts']:
                status[host] = self.execute_remote_command(
                    host,
                    service['status_cmd'],
                    user
                )
        return status

    def start_hdfs(self, user: str) -> bool:
        """
        启动HDFS服务
        
        Args:
            user: 执行命令的用户
            
        Returns:
            bool: 是否成功启动
        """
        # 首先启动NameNode
        if not self.start_service('namenode', user):
            return False
        
        # 然后启动DataNode
        return self.start_service('datanode', user)

    def start_yarn(self, user: str) -> bool:
        """
        启动YARN服务
        
        Args:
            user: 执行命令的用户
            
        Returns:
            bool: 是否成功启动
        """
        # 首先启动ResourceManager
        if not self.start_service('resourcemanager', user):
            return False
        
        # 然后启动NodeManager
        return self.start_service('nodemanager', user)

    def start_hive(self, user: str) -> bool:
        """
        启动Hive服务
        
        Args:
            user: 执行命令的用户
            
        Returns:
            bool: 是否成功启动
        """
        return self.start_service('hiveserver2', user)

    def stop_all_services(self, user: str) -> bool:
        """
        停止所有Hadoop服务
        
        Args:
            user: 执行命令的用户
            
        Returns:
            bool: 是否成功停止所有服务
        """
        success = True
        # 按照依赖关系的相反顺序停止服务
        services_to_stop = ['hiveserver2', 'nodemanager', 'resourcemanager', 'datanode', 'namenode']
        for service in services_to_stop:
            if not self.stop_service(service, user):
                success = False
        return success

    def check_all_services(self, user: str) -> Dict[str, Dict[str, bool]]:
        """
        检查所有服务的状态
        
        Args:
            user: 执行命令的用户
            
        Returns:
            Dict[str, Dict[str, bool]]: 所有服务的状态
        """
        status = {}
        for service in self.services:
            status[service] = self.check_service_status(service, user)
        return status 