import os
import subprocess
import logging
from typing import Tuple, List

logger = logging.getLogger(__name__)

class HadoopService:
    """Hadoop服务管理类"""
    
    def __init__(self):
        # 获取Hadoop相关环境变量
        self.hadoop_home = os.environ.get('HADOOP_HOME', '')
        self.java_home = os.environ.get('JAVA_HOME', '')
        
        if not self.hadoop_home:
            raise EnvironmentError("HADOOP_HOME环境变量未设置")
        if not self.java_home:
            raise EnvironmentError("JAVA_HOME环境变量未设置")
            
        # Hadoop服务脚本路径
        self.start_dfs_script = os.path.join(self.hadoop_home, 'sbin', 'start-dfs.sh')
        self.start_yarn_script = os.path.join(self.hadoop_home, 'sbin', 'start-yarn.sh')
        self.stop_dfs_script = os.path.join(self.hadoop_home, 'sbin', 'stop-dfs.sh')
        self.stop_yarn_script = os.path.join(self.hadoop_home, 'sbin', 'stop-yarn.sh')
    
    def check_service_status(self) -> List[str]:
        """检查Hadoop服务状态"""
        try:
            result = subprocess.run(['jps'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            running_services = []
            for line in result.stdout.splitlines():
                if any(service in line for service in ['NameNode', 'DataNode', 'ResourceManager', 'NodeManager']):
                    running_services.append(line)
            return running_services
        except Exception as e:
            logger.error(f"检查服务状态时出错: {str(e)}")
            return []
    
    def start_services(self) -> Tuple[bool, str]:
        """启动Hadoop服务"""
        try:
            # 检查服务是否已经在运行
            running_services = self.check_service_status()
            if running_services:
                return True, f"Hadoop服务已在运行: {', '.join(running_services)}"
            
            # 启动HDFS
            logger.info("正在启动HDFS...")
            subprocess.run([self.start_dfs_script], check=True)
            
            # 启动YARN
            logger.info("正在启动YARN...")
            subprocess.run([self.start_yarn_script], check=True)
            
            # 验证服务是否成功启动
            running_services = self.check_service_status()
            if running_services:
                return True, f"Hadoop服务启动成功: {', '.join(running_services)}"
            else:
                return False, "Hadoop服务启动失败，请检查日志"
                
        except Exception as e:
            error_msg = f"启动Hadoop服务时出错: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def stop_services(self) -> Tuple[bool, str]:
        """停止Hadoop服务"""
        try:
            # 停止YARN
            logger.info("正在停止YARN...")
            subprocess.run([self.stop_yarn_script], check=True)
            
            # 停止HDFS
            logger.info("正在停止HDFS...")
            subprocess.run([self.stop_dfs_script], check=True)
            
            # 验证服务是否已停止
            running_services = self.check_service_status()
            if not running_services:
                return True, "Hadoop服务已成功停止"
            else:
                return False, f"部分服务仍在运行: {', '.join(running_services)}"
                
        except Exception as e:
            error_msg = f"停止Hadoop服务时出错: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def check_hadoop_config(self) -> Tuple[bool, List[str]]:
        """检查Hadoop配置"""
        issues = []
        
        # 检查必要的环境变量
        if not self.hadoop_home:
            issues.append("HADOOP_HOME环境变量未设置")
        if not self.java_home:
            issues.append("JAVA_HOME环境变量未设置")
            
        # 检查必要的配置文件
        config_files = [
            os.path.join(self.hadoop_home, 'etc/hadoop/core-site.xml'),
            os.path.join(self.hadoop_home, 'etc/hadoop/hdfs-site.xml'),
            os.path.join(self.hadoop_home, 'etc/hadoop/yarn-site.xml'),
            os.path.join(self.hadoop_home, 'etc/hadoop/mapred-site.xml')
        ]
        
        for config_file in config_files:
            if not os.path.exists(config_file):
                issues.append(f"配置文件不存在: {config_file}")
                
        return len(issues) == 0, issues
    
    def get_service_ports(self) -> dict:
        """获取Hadoop服务端口信息"""
        return {
            'namenode_http': 9870,
            'datanode_http': 9864,
            'resourcemanager_http': 8088,
            'nodemanager_http': 8042,
            'secondary_namenode_http': 9868,
        } 