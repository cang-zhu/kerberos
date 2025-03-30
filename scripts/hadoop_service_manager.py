#!/usr/bin/env python3
import os
import sys
import subprocess
import logging
import json
from typing import Dict, List, Optional

class HadoopServiceManager:
    def __init__(self, config_path: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        # 设置日志级别
        self.logger.setLevel(logging.INFO)
        # 添加控制台处理器
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            
        self.config_path = config_path
        self.services = {
            'namenode': {'user': 'hdfs_user', 'keytab': 'nn.service.keytab'},
            'datanode': {'user': 'hdfs_user', 'keytab': 'dn.service.keytab'},
            'resourcemanager': {'user': 'yarn_user', 'keytab': 'rm.service.keytab'},
            'nodemanager': {'user': 'yarn_user', 'keytab': 'nm.service.keytab'},
            'hiveserver2': {'user': 'hive_user', 'keytab': 'hive.service.keytab'},
            'metastore': {'user': 'hive_user', 'keytab': 'hive.service.keytab'}
        }
        
        # 服务对应的进程名称
        self.process_names = {
            'namenode': 'NameNode',
            'datanode': 'DataNode',
            'resourcemanager': 'ResourceManager',
            'nodemanager': 'NodeManager',
            'hiveserver2': 'HiveServer2',
            'metastore': 'MetaStore'
        }
        
        # 获取环境变量
        self.hadoop_home = os.getenv('HADOOP_HOME', '/usr/local/hadoop')
        self.java_home = os.getenv('JAVA_HOME', '/usr/lib/jvm/java-11-openjdk')
        self.hive_home = os.getenv('HIVE_HOME', '/usr/local/hive')
        self.keytab_dir = os.getenv('KEYTAB_DIR', '/var/hadoop/kerberos/keytabs')
        self.krb5_config = os.getenv('KRB5_CONFIG', '/usr/local/etc/krb5.conf')
        self.krb5_kdc_profile = os.getenv('KRB5_KDC_PROFILE', '/usr/local/opt/krb5/var/krb5kdc/kdc.conf')
        self.kerberos_path = os.getenv('KERBEROS_PATH', '/usr/local/opt/krb5/sbin')
        
        self.logger.info(f"HADOOP_HOME: {self.hadoop_home}")
        self.logger.info(f"JAVA_HOME: {self.java_home}")
        self.logger.info(f"HIVE_HOME: {self.hive_home}")
        
        # 设置命令路径
        self.hdfs_cmd = os.path.join(self.hadoop_home, 'bin/hdfs')
        self.yarn_cmd = os.path.join(self.hadoop_home, 'bin/yarn')
        self.hive_cmd = os.path.join(self.hive_home, 'bin/hive')
        
        # 检查命令文件是否存在
        self.available_commands = {}
        for service, cmd in [
            ('hdfs', self.hdfs_cmd),
            ('yarn', self.yarn_cmd),
            ('hive', self.hive_cmd)
        ]:
            if os.path.exists(cmd):
                self.available_commands[service] = True
                self.logger.info(f"Found {service} command at: {cmd}")
            else:
                self.available_commands[service] = False
                self.logger.warning(f"Command not found: {cmd}")
                
        # 设置环境变量
        os.environ.update({
            'HADOOP_HOME': self.hadoop_home,
            'HADOOP_COMMON_HOME': self.hadoop_home,
            'HADOOP_HDFS_HOME': self.hadoop_home,
            'HADOOP_MAPRED_HOME': self.hadoop_home,
            'HADOOP_YARN_HOME': self.hadoop_home,
            'HADOOP_CONF_DIR': os.path.join(self.hadoop_home, 'etc/hadoop'),
            'HADOOP_COMMON_LIB_NATIVE_DIR': os.path.join(self.hadoop_home, 'lib/native'),
            'HADOOP_OPTS': f"-Djava.library.path={os.path.join(self.hadoop_home, 'lib/native')}",
            'HIVE_HOME': self.hive_home,
            'HIVE_CONF_DIR': os.path.join(self.hive_home, 'conf'),
            'JAVA_HOME': self.java_home,
            'PATH': f"{os.path.join(self.hadoop_home, 'bin')}:{os.path.join(self.hadoop_home, 'sbin')}:{os.path.join(self.hive_home, 'bin')}:{os.getenv('PATH', '')}"
        })

    def check_service_status(self, service_name: str, username: Optional[str] = None) -> bool:
        """检查指定服务的运行状态"""
        try:
            # 检查服务所需的命令是否可用
            if service_name in ['namenode', 'datanode'] and not self.available_commands.get('hdfs'):
                self.logger.warning(f"HDFS commands not available, cannot check {service_name}")
                return False
            elif service_name in ['resourcemanager', 'nodemanager'] and not self.available_commands.get('yarn'):
                self.logger.warning(f"YARN commands not available, cannot check {service_name}")
                return False
            elif service_name in ['hiveserver2', 'metastore'] and not self.available_commands.get('hive'):
                self.logger.warning(f"Hive commands not available, cannot check {service_name}")
                return False

            # 使用jps命令检查Java进程
            result = subprocess.run(['jps', '-l'], capture_output=True, text=True)
            if result.returncode != 0:
                self.logger.error(f"Failed to run jps command: {result.stderr}")
                return False
                
            # 检查进程是否在运行
            process_name = self.process_names.get(service_name)
            if not process_name:
                self.logger.error(f"Unknown service: {service_name}")
                return False
            
            self.logger.info(f"JPS output for {service_name}: {result.stdout}")
            
            # 定义进程类名映射
            process_classes = {
                'NameNode': ['org.apache.hadoop.hdfs.server.namenode.NameNode', 'namenode', 'NameNode'],
                'DataNode': ['org.apache.hadoop.hdfs.server.datanode.DataNode', 'datanode', 'DataNode'],
                'ResourceManager': ['org.apache.hadoop.yarn.server.resourcemanager.ResourceManager', 'resourcemanager', 'ResourceManager'],
                'NodeManager': ['org.apache.hadoop.yarn.server.nodemanager.NodeManager', 'nodemanager', 'NodeManager'],
                'HiveServer2': ['org.apache.hive.service.server.HiveServer2', 'hiveserver2', 'HiveServer2'],
                'MetaStore': ['org.apache.hadoop.hive.metastore.HiveMetaStore', 'metastore', 'MetaStore']
            }
            
            # 获取目标进程的可能类名
            target_classes = process_classes.get(process_name, [])
            
            # 检查进程是否在运行
            is_running = False
            for line in result.stdout.splitlines():
                if not line.strip():
                    continue
                self.logger.debug(f"Checking line: {line}")
                for target_class in target_classes:
                    if target_class.lower() in line.lower():
                        is_running = True
                        self.logger.info(f"Found running process for {service_name}: {line}")
                        break
                if is_running:
                    break
            
            self.logger.info(f"Service {service_name} status: {'running' if is_running else 'stopped'}")
            return is_running
            
        except Exception as e:
            self.logger.error(f"Error checking service status: {str(e)}", exc_info=True)
            return False

    def check_all_services(self, username: Optional[str] = None) -> Dict[str, bool]:
        """检查所有服务的状态"""
        status = {}
        for service in self.services.keys():
            status[service] = self.check_service_status(service, username)
        return status

    def start_service(self, service_name: str, username: Optional[str] = None) -> bool:
        """启动指定的服务"""
        try:
            # 获取并设置环境变量
            env = os.environ.copy()
            env.update({
                'HADOOP_HOME': self.hadoop_home,
                'HADOOP_COMMON_HOME': self.hadoop_home,
                'HADOOP_HDFS_HOME': self.hadoop_home,
                'HADOOP_MAPRED_HOME': self.hadoop_home,
                'HADOOP_YARN_HOME': self.hadoop_home,
                'HADOOP_CONF_DIR': os.path.join(self.hadoop_home, 'etc/hadoop'),
                'HADOOP_COMMON_LIB_NATIVE_DIR': os.path.join(self.hadoop_home, 'lib/native'),
                'HADOOP_OPTS': f"-Djava.library.path={os.path.join(self.hadoop_home, 'lib/native')}",
                'HIVE_HOME': self.hive_home,
                'HIVE_CONF_DIR': os.path.join(self.hive_home, 'conf'),
                'JAVA_HOME': os.getenv('JAVA_HOME', '/usr/local/opt/openjdk@11'),
                'PATH': f"{os.path.join(self.hadoop_home, 'bin')}:{os.path.join(self.hadoop_home, 'sbin')}:{os.path.join(self.hive_home, 'bin')}:{os.getenv('PATH', '')}"
            })
            
            self.logger.info(f"Starting service: {service_name}")
            
            cmd = []
            if service_name == 'namenode':
                cmd = [self.hdfs_cmd, '--daemon', 'start', 'namenode']
            elif service_name == 'datanode':
                cmd = [self.hdfs_cmd, '--daemon', 'start', 'datanode']
            elif service_name == 'resourcemanager':
                cmd = [self.yarn_cmd, '--daemon', 'start', 'resourcemanager']
            elif service_name == 'nodemanager':
                cmd = [self.yarn_cmd, '--daemon', 'start', 'nodemanager']
            elif service_name == 'hiveserver2':
                cmd = [os.path.join(self.hive_home, 'bin/hiveserver2')]
            elif service_name == 'metastore':
                cmd = [os.path.join(self.hive_home, 'bin/hive'), '--service', 'metastore']
            else:
                self.logger.error(f"Unknown service: {service_name}")
                return False
            
            self.logger.info(f"Executing command: {' '.join(cmd)}")
            process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 等待一段时间检查进程是否启动
            import time
            max_retries = 5
            retry_interval = 2
            
            for i in range(max_retries):
                time.sleep(retry_interval)
                if self.check_service_status(service_name):
                    self.logger.info(f"Service {service_name} started successfully")
                    return True
                self.logger.info(f"Waiting for service {service_name} to start (attempt {i+1}/{max_retries})")
            
            # 如果进程没有启动，获取错误输出
            stdout, stderr = process.communicate(timeout=1)
            if stderr:
                self.logger.error(f"Service {service_name} failed to start: {stderr}")
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error starting service {service_name}: {str(e)}")
            return False

    def stop_service(self, service_name: str, username: Optional[str] = None) -> bool:
        """停止指定的服务"""
        try:
            env = os.environ.copy()
            self.logger.info(f"Stopping service: {service_name}")
            
            cmd = []
            if service_name == 'namenode':
                cmd = [self.hdfs_cmd, '--daemon', 'stop', 'namenode']
            elif service_name == 'datanode':
                cmd = [self.hdfs_cmd, '--daemon', 'stop', 'datanode']
            elif service_name == 'resourcemanager':
                cmd = [self.yarn_cmd, '--daemon', 'stop', 'resourcemanager']
            elif service_name == 'nodemanager':
                cmd = [self.yarn_cmd, '--daemon', 'stop', 'nodemanager']
            elif service_name == 'hiveserver2':
                cmd = [os.path.join(self.hive_home, 'bin/hive'), '--service', 'hiveserver2', '--shutdown']
            elif service_name == 'metastore':
                cmd = [os.path.join(self.hive_home, 'bin/hive'), '--service', 'metastore', '--shutdown']
            else:
                self.logger.error(f"Unknown service: {service_name}")
                return False
            
            if cmd:
                self.logger.info(f"Executing command: {' '.join(cmd)}")
                result = subprocess.run(cmd, env=env, capture_output=True, text=True)
                if result.returncode != 0:
                    self.logger.error(f"Failed to stop {service_name}: {result.stderr}")
                    return False
            
            # 等待服务停止
            import time
            max_retries = 5
            retry_interval = 2
            
            for i in range(max_retries):
                time.sleep(retry_interval)
                if not self.check_service_status(service_name):
                    self.logger.info(f"Service {service_name} stopped successfully")
                    return True
                self.logger.info(f"Waiting for service {service_name} to stop (attempt {i+1}/{max_retries})")
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error stopping service {service_name}: {str(e)}")
            return False

    def start_all_services(self, username: Optional[str] = None) -> bool:
        """启动所有服务"""
        try:
            # 按顺序启动服务
            services_order = ['namenode', 'datanode', 'resourcemanager', 'nodemanager', 'hiveserver2', 'metastore']
            for service in services_order:
                if not self.start_service(service, username):
                    return False
            return True
        except Exception as e:
            self.logger.error(f"Error starting all services: {str(e)}")
            return False

    def stop_all_services(self, username: Optional[str] = None) -> bool:
        """停止所有服务"""
        try:
            # 按照依赖关系的相反顺序停止服务
            services_order = ['metastore', 'hiveserver2', 'nodemanager', 'resourcemanager', 'datanode', 'namenode']
            for service in services_order:
                if not self.stop_service(service, username):
                    return False
            return True
        except Exception as e:
            self.logger.error(f"Error stopping all services: {str(e)}")
            return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 hadoop-service-manager.py <command> [service_name]")
        print("Commands: start, stop, start-all, stop-all, status")
        sys.exit(1)
        
    manager = HadoopServiceManager()
    command = sys.argv[1]
    
    if command == "start" and len(sys.argv) == 3:
        manager.start_service(sys.argv[2])
    elif command == "stop" and len(sys.argv) == 3:
        manager.stop_service(sys.argv[2])
    elif command == "start-all":
        manager.start_all_services()
    elif command == "stop-all":
        manager.stop_all_services()
    elif command == "status":
        status = manager.check_all_services()
        print(json.dumps(status))
    else:
        print("Invalid command")
        sys.exit(1)

if __name__ == "__main__":
    main() 