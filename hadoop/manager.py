import os
import logging
from typing import Dict, Optional, Tuple, List
from .config_manager import HadoopConfigManager
from .cluster_manager import HadoopClusterManager
from .auth_manager import HadoopAuthManager
from .service_manager import HadoopServiceManager

class HadoopManager:
    def __init__(self, config_dir: str):
        self.config_dir = config_dir
        self.logger = logging.getLogger(__name__)
        
        # 初始化各个管理器
        self.config_manager = HadoopConfigManager(config_dir)
        self.cluster_manager = HadoopClusterManager(config_dir)
        self.auth_manager = HadoopAuthManager(config_dir)
        self.service_manager = HadoopServiceManager(config_dir)
        
    def initialize_cluster(self, cluster_config: Dict) -> Tuple[bool, Optional[str]]:
        """
        初始化Hadoop集群
        
        Args:
            cluster_config: 集群配置信息
            
        Returns:
            Tuple[bool, Optional[str]]: (是否成功, 错误信息)
        """
        try:
            # 更新HDFS配置
            namenode_host = cluster_config.get('namenode_host')
            if not self.config_manager.update_hdfs_config(namenode_host):
                return False, "更新HDFS配置失败"
                
            # 更新YARN配置
            resourcemanager_host = cluster_config.get('resourcemanager_host')
            if not self.config_manager.update_yarn_config(resourcemanager_host):
                return False, "更新YARN配置失败"
                
            # 更新Hive配置
            metastore_host = cluster_config.get('metastore_host')
            if not self.config_manager.update_hive_config(metastore_host):
                return False, "更新Hive配置失败"
                
            # 添加集群节点
            nodes = cluster_config.get('nodes', [])
            for node in nodes:
                if not self.cluster_manager.add_node(
                    node['hostname'],
                    node['ip'],
                    node['roles']
                ):
                    return False, f"添加节点 {node['hostname']} 失败"
                    
            # 同步配置到所有节点
            if not self.config_manager.sync_configs_to_nodes(
                [node['hostname'] for node in nodes],
                cluster_config.get('ssh_user')
            ):
                return False, "同步配置文件失败"
                
            return True, None
        except Exception as e:
            self.logger.error(f"初始化集群失败: {e}")
            return False, str(e)
            
    def start_services(self) -> Tuple[bool, Optional[str]]:
        """
        启动Hadoop服务
        
        Returns:
            Tuple[bool, Optional[str]]: (是否成功, 错误信息)
        """
        try:
            # 启动HDFS
            if not self.service_manager.start_hdfs():
                return False, "启动HDFS失败"
                
            # 启动YARN
            if not self.service_manager.start_yarn():
                return False, "启动YARN失败"
                
            # 启动Hive
            if not self.service_manager.start_hive():
                return False, "启动Hive失败"
                
            return True, None
        except Exception as e:
            self.logger.error(f"启动服务失败: {e}")
            return False, str(e)
            
    def authenticate_user(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """
        用户认证
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            Tuple[bool, Optional[str]]: (是否认证成功, 错误信息)
        """
        return self.auth_manager.authenticate_user(username, password)
        
    def verify_service_access(self, username: str, service: str) -> Tuple[bool, Optional[str]]:
        """
        验证服务访问权限
        
        Args:
            username: 用户名
            service: 服务名称
            
        Returns:
            Tuple[bool, Optional[str]]: (是否有权限, 错误信息)
        """
        try:
            if service == 'admin':
                return True, None
            return self.auth_manager.verify_service_access(username, service)
        except Exception as e:
            self.logger.error(f"验证服务访问权限失败: {e}")
            return False, str(e)
            
    def setup_user_environment(self, username: str) -> Tuple[bool, Optional[str]]:
        """
        设置用户环境
        
        Args:
            username: 用户名
            
        Returns:
            Tuple[bool, Optional[str]]: (是否成功, 错误信息)
        """
        try:
            return self.auth_manager.setup_user_environment(username)
        except Exception as e:
            self.logger.error(f"设置用户环境失败: {e}")
            return False, str(e)
        
    def get_service_status(self) -> Dict[str, str]:
        """
        获取服务状态
        
        Returns:
            Dict[str, str]: 服务状态字典
        """
        return self.cluster_manager.update_cluster_status()
        
    def execute_hdfs_command(self, username: str, command: str) -> Tuple[bool, str, Optional[str]]:
        """
        执行HDFS命令
        
        Args:
            username: 用户名
            command: HDFS命令
            
        Returns:
            Tuple[bool, str, Optional[str]]: (是否成功, 输出结果, 错误信息)
        """
        try:
            # 验证HDFS访问权限
            access_ok, error = self.auth_manager.verify_service_access(username, 'hdfs')
            if not access_ok:
                return False, '', error
                
            # 设置用户环境
            env_ok, error = self.auth_manager.setup_user_environment(username)
            if not env_ok:
                return False, '', error
                
            # 执行命令
            full_command = f"hadoop fs {command}"
            exit_code, output, error = self.cluster_manager.execute_command(
                self.config_manager.config_files['core-site.xml']['fs.defaultFS'].split('://')[1].split(':')[0],
                full_command
            )
            
            return exit_code == 0, output, error
        except Exception as e:
            self.logger.error(f"执行HDFS命令失败: {e}")
            return False, '', str(e)
            
    def submit_yarn_application(self, username: str, application_path: str, args: List[str] = None) -> Tuple[bool, str, Optional[str]]:
        """
        提交YARN应用
        
        Args:
            username: 用户名
            application_path: 应用程序路径
            args: 应用程序参数
            
        Returns:
            Tuple[bool, str, Optional[str]]: (是否成功, 应用ID, 错误信息)
        """
        try:
            # 验证YARN访问权限
            access_ok, error = self.auth_manager.verify_service_access(username, 'yarn')
            if not access_ok:
                return False, '', error
                
            # 设置用户环境
            env_ok, error = self.auth_manager.setup_user_environment(username)
            if not env_ok:
                return False, '', error
                
            # 构建命令
            cmd_args = ' '.join(args) if args else ''
            command = f"yarn jar {application_path} {cmd_args}"
            
            # 执行命令
            exit_code, output, error = self.cluster_manager.execute_command(
                self.config_manager.config_files['yarn-site.xml']['yarn.resourcemanager.hostname'],
                command
            )
            
            return exit_code == 0, output, error
        except Exception as e:
            self.logger.error(f"提交YARN应用失败: {e}")
            return False, '', str(e)
            
    def execute_hive_query(self, username: str, query: str) -> Tuple[bool, str, Optional[str]]:
        """
        执行Hive查询
        
        Args:
            username: 用户名
            query: HiveQL查询
            
        Returns:
            Tuple[bool, str, Optional[str]]: (是否成功, 查询结果, 错误信息)
        """
        try:
            # 验证Hive访问权限
            access_ok, error = self.auth_manager.verify_service_access(username, 'hive')
            if not access_ok:
                return False, '', error
                
            # 设置用户环境
            env_ok, error = self.auth_manager.setup_user_environment(username)
            if not env_ok:
                return False, '', error
                
            # 执行查询
            command = f"hive -e '{query}'"
            exit_code, output, error = self.cluster_manager.execute_command(
                self.config_manager.config_files['hive-site.xml']['hive.metastore.uris'].split('://')[1].split(':')[0],
                command
            )
            
            return exit_code == 0, output, error
        except Exception as e:
            self.logger.error(f"执行Hive查询失败: {e}")
            return False, '', str(e)
            
    def cleanup(self):
        """
        清理资源
        """
        try:
            self.cluster_manager.close_connections()
        except Exception as e:
            self.logger.error(f"清理资源失败: {e}") 