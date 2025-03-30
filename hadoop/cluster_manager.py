import os
import logging
import paramiko
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class NodeInfo:
    hostname: str
    ip: str
    role: List[str]  # 可能的角色: namenode, datanode, resourcemanager, nodemanager, hiveserver
    status: str = 'unknown'  # unknown, running, stopped, error

class HadoopClusterManager:
    def __init__(self, config_dir: str):
        self.config_dir = config_dir
        self.logger = logging.getLogger(__name__)
        self.nodes: Dict[str, NodeInfo] = {}
        self.ssh_clients: Dict[str, paramiko.SSHClient] = {}

    def add_node(self, hostname: str, ip: str, roles: List[str]) -> bool:
        """
        添加集群节点
        
        Args:
            hostname: 节点主机名
            ip: 节点IP地址
            roles: 节点角色列表
            
        Returns:
            bool: 是否成功添加
        """
        try:
            self.nodes[hostname] = NodeInfo(hostname=hostname, ip=ip, role=roles)
            return True
        except Exception as e:
            self.logger.error(f"添加节点失败: {e}")
            return False

    def connect_node(self, hostname: str, username: str, password: str = None, key_filename: str = None) -> bool:
        """
        连接到节点
        
        Args:
            hostname: 节点主机名
            username: SSH用户名
            password: SSH密码（可选）
            key_filename: SSH密钥文件路径（可选）
            
        Returns:
            bool: 是否成功连接
        """
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            if key_filename:
                client.connect(hostname, username=username, key_filename=key_filename)
            else:
                client.connect(hostname, username=username, password=password)
                
            self.ssh_clients[hostname] = client
            return True
        except Exception as e:
            self.logger.error(f"连接节点失败: {e}")
            return False

    def execute_command(self, hostname: str, command: str) -> tuple:
        """
        在节点上执行命令
        
        Args:
            hostname: 节点主机名
            command: 要执行的命令
            
        Returns:
            tuple: (exit_code, stdout, stderr)
        """
        try:
            if hostname not in self.ssh_clients:
                raise Exception(f"节点 {hostname} 未连接")
                
            client = self.ssh_clients[hostname]
            stdin, stdout, stderr = client.exec_command(command)
            exit_code = stdout.channel.recv_exit_status()
            
            return (
                exit_code,
                stdout.read().decode('utf-8'),
                stderr.read().decode('utf-8')
            )
        except Exception as e:
            self.logger.error(f"执行命令失败: {e}")
            return (-1, '', str(e))

    def check_node_status(self, hostname: str) -> str:
        """
        检查节点状态
        
        Args:
            hostname: 节点主机名
            
        Returns:
            str: 节点状态
        """
        try:
            if hostname not in self.nodes:
                return 'unknown'
                
            node = self.nodes[hostname]
            
            # 检查各个服务的状态
            for role in node.role:
                if role == 'namenode':
                    code, _, _ = self.execute_command(hostname, 'jps | grep NameNode')
                    if code != 0:
                        return 'error'
                elif role == 'datanode':
                    code, _, _ = self.execute_command(hostname, 'jps | grep DataNode')
                    if code != 0:
                        return 'error'
                elif role == 'resourcemanager':
                    code, _, _ = self.execute_command(hostname, 'jps | grep ResourceManager')
                    if code != 0:
                        return 'error'
                elif role == 'nodemanager':
                    code, _, _ = self.execute_command(hostname, 'jps | grep NodeManager')
                    if code != 0:
                        return 'error'
                elif role == 'hiveserver':
                    code, _, _ = self.execute_command(hostname, 'jps | grep HiveServer')
                    if code != 0:
                        return 'error'
            
            return 'running'
        except Exception as e:
            self.logger.error(f"检查节点状态失败: {e}")
            return 'error'

    def update_cluster_status(self) -> Dict[str, str]:
        """
        更新所有节点状态
        
        Returns:
            Dict[str, str]: 节点状态字典
        """
        status = {}
        for hostname in self.nodes:
            status[hostname] = self.check_node_status(hostname)
            self.nodes[hostname].status = status[hostname]
        return status

    def close_connections(self):
        """
        关闭所有SSH连接
        """
        for client in self.ssh_clients.values():
            try:
                client.close()
            except:
                pass
        self.ssh_clients.clear() 