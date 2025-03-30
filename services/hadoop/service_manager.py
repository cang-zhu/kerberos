"""Hadoop服务管理"""
import logging
import subprocess
import os
from typing import Dict, Optional
from services.hadoop.auth_service import HadoopAuthService

class HadoopServiceManager:
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self.auth_service = HadoopAuthService()
        self.logger = logging.getLogger(__name__)
        
        # 服务配置
        self.services = {
            'namenode': {
                'user': 'hdfs_user',
                'keytab': 'nn.service.keytab',
                'principal': 'nn/localhost@TEST.COM',
                'start_cmd': 'hadoop-daemon.sh start namenode',
                'stop_cmd': 'hadoop-daemon.sh stop namenode'
            },
            'datanode': {
                'user': 'hdfs_user',
                'keytab': 'dn.service.keytab',
                'principal': 'dn/localhost@TEST.COM',
                'start_cmd': 'hadoop-daemon.sh start datanode',
                'stop_cmd': 'hadoop-daemon.sh stop datanode'
            },
            'resourcemanager': {
                'user': 'yarn_user',
                'keytab': 'rm.service.keytab',
                'principal': 'rm/localhost@TEST.COM',
                'start_cmd': 'yarn-daemon.sh start resourcemanager',
                'stop_cmd': 'yarn-daemon.sh stop resourcemanager'
            },
            'nodemanager': {
                'user': 'yarn_user',
                'keytab': 'nm.service.keytab',
                'principal': 'nm/localhost@TEST.COM',
                'start_cmd': 'yarn-daemon.sh start nodemanager',
                'stop_cmd': 'yarn-daemon.sh stop nodemanager'
            }
        }
        
    def start_service(self, service_name: str, principal: str) -> bool:
        """启动Hadoop服务"""
        try:
            # 检查权限
            if not self.auth_service.check_service_permission(principal, service_name):
                self.logger.warning(f"用户 {principal} 没有权限管理服务 {service_name}")
                return False
            
            # 获取服务配置
            service_config = self.services.get(service_name)
            if not service_config:
                self.logger.error(f"未知服务: {service_name}")
                return False
            
            # 使用对应的keytab和主体启动服务
            keytab_path = os.path.join(self.config_path, 'keytabs', service_config['keytab'])
            service_principal = service_config['principal']
            
            # 进行Kerberos认证
            cmd = f"kinit -kt {keytab_path} {service_principal}"
            subprocess.run(cmd, shell=True, check=True)
            
            # 启动服务
            cmd = service_config['start_cmd']
            subprocess.run(cmd, shell=True, check=True)
            
            self.logger.info(f"服务 {service_name} 启动成功")
            return True
        except Exception as e:
            self.logger.error(f"启动服务失败: {str(e)}")
            return False
            
    def stop_service(self, service_name: str, principal: str) -> bool:
        """停止Hadoop服务"""
        try:
            # 检查权限
            if not self.auth_service.check_service_permission(principal, service_name):
                self.logger.warning(f"用户 {principal} 没有权限管理服务 {service_name}")
                return False
            
            # 获取服务配置
            service_config = self.services.get(service_name)
            if not service_config:
                self.logger.error(f"未知服务: {service_name}")
                return False
            
            # 停止服务
            cmd = service_config['stop_cmd']
            subprocess.run(cmd, shell=True, check=True)
            
            self.logger.info(f"服务 {service_name} 停止成功")
            return True
        except Exception as e:
            self.logger.error(f"停止服务失败: {str(e)}")
            return False 