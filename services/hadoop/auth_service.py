"""Hadoop认证服务"""
import logging
import subprocess
from models.hadoop.auth import HadoopGroups

class HadoopAuthService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def check_service_permission(self, principal: str, service: str) -> bool:
        """检查用户是否有权限管理指定服务"""
        try:
            # 获取用户组信息
            cmd = f"kadmin.local -q 'get_groups {principal}'"
            result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            groups = result.stdout.strip().split('\n')
            
            # 检查权限
            if service.startswith('namenode') or service.startswith('datanode'):
                return HadoopGroups.HDFS_ADMINS in groups
            elif service.startswith('resourcemanager') or service.startswith('nodemanager'):
                return HadoopGroups.YARN_ADMINS in groups
            elif service.startswith('hiveserver2') or service.startswith('metastore'):
                return HadoopGroups.HIVE_ADMINS in groups
            
            return False
        except Exception as e:
            self.logger.error(f"检查服务权限失败: {str(e)}")
            return False
            
    def get_user_groups(self, principal: str) -> list:
        """获取用户所属的组"""
        try:
            cmd = f"kadmin.local -q 'get_groups {principal}'"
            result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            return result.stdout.strip().split('\n')
        except Exception as e:
            self.logger.error(f"获取用户组失败: {str(e)}")
            return [] 