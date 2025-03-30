import os
import logging
from typing import Optional, Dict, Tuple
from kerberos.auth import KerberosAuth
from kerberos.crypto import KerberosCrypto

class HadoopAuthManager:
    def __init__(self, config_dir: str):
        self.config_dir = config_dir
        self.logger = logging.getLogger(__name__)
        
        # 从环境变量获取Kerberos配置
        service_name = os.getenv('KERBEROS_SERVICE_NAME', 'HTTP')
        realm = os.getenv('KERBEROS_REALM', 'TEST.COM')
        self.kerberos_auth = KerberosAuth(service_name=service_name, realm=realm)
        
        self.service_tickets: Dict[str, str] = {}  # 用户服务票据缓存
        
        # 设置Hadoop命令路径
        hadoop_home = os.getenv('HADOOP_HOME', '/usr/local/hadoop')
        hadoop_bin = os.path.join(hadoop_home, 'bin')
        hadoop_cmd = os.path.join(hadoop_bin, 'hadoop')

        # 设置Kerberos配置
        krb5_config = os.getenv('KRB5_CONFIG', '/usr/local/etc/krb5.conf')
        keytab_dir = os.getenv('KEYTAB_DIR', '/var/hadoop/kerberos/keytabs')
        
    def authenticate_user(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """
        用户认证
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            Tuple[bool, Optional[str]]: (是否认证成功, 错误信息)
        """
        try:
            # 使用Kerberos进行认证
            tgt = self.kerberos_auth.authenticate(username, password)
            if not tgt:
                return False, "Kerberos认证失败"
                
            # 获取HDFS服务票据
            hdfs_ticket = self.kerberos_auth.get_service_ticket(tgt, "hdfs")
            if not hdfs_ticket:
                return False, "获取HDFS服务票据失败"
            self.service_tickets[f"{username}_hdfs"] = hdfs_ticket
            
            # 获取YARN服务票据
            yarn_ticket = self.kerberos_auth.get_service_ticket(tgt, "yarn")
            if not yarn_ticket:
                return False, "获取YARN服务票据失败"
            self.service_tickets[f"{username}_yarn"] = yarn_ticket
            
            # 获取Hive服务票据
            hive_ticket = self.kerberos_auth.get_service_ticket(tgt, "hive")
            if not hive_ticket:
                return False, "获取Hive服务票据失败"
            self.service_tickets[f"{username}_hive"] = hive_ticket
            
            return True, None
        except Exception as e:
            self.logger.error(f"用户认证失败: {e}")
            return False, str(e)
            
    def verify_service_access(self, username: str, service: str) -> Tuple[bool, Optional[str]]:
        """
        验证服务访问权限
        
        Args:
            username: 用户名
            service: 服务名称 (hdfs/yarn/hive)
            
        Returns:
            Tuple[bool, Optional[str]]: (是否有权限, 错误信息)
        """
        try:
            ticket_key = f"{username}_{service}"
            if ticket_key not in self.service_tickets:
                return False, f"未找到{service}服务票据"
                
            ticket = self.service_tickets[ticket_key]
            if not self.kerberos_auth.verify_ticket(ticket, service):
                return False, f"{service}服务票据验证失败"
                
            return True, None
        except Exception as e:
            self.logger.error(f"验证服务访问权限失败: {e}")
            return False, str(e)
            
    def generate_delegation_token(self, username: str, service: str) -> Tuple[Optional[str], Optional[str]]:
        """
        生成委托令牌
        
        Args:
            username: 用户名
            service: 服务名称 (hdfs/yarn/hive)
            
        Returns:
            Tuple[Optional[str], Optional[str]]: (委托令牌, 错误信息)
        """
        try:
            # 验证服务访问权限
            access_ok, error = self.verify_service_access(username, service)
            if not access_ok:
                return None, error
                
            # 生成委托令牌
            token = KerberosCrypto.generate_token()
            return token, None
        except Exception as e:
            self.logger.error(f"生成委托令牌失败: {e}")
            return None, str(e)
            
    def setup_user_environment(self, username: str) -> Tuple[bool, Optional[str]]:
        """
        设置用户环境
        
        Args:
            username: 用户名
            
        Returns:
            Tuple[bool, Optional[str]]: (是否设置成功, 错误信息)
        """
        try:
            # 设置Hadoop用户环境变量
            os.environ['HADOOP_USER_NAME'] = username
            
            # 在开发环境下跳过Hadoop命令执行
            if os.getenv('FLASK_ENV') == 'development':
                return True, None
            
            # 设置Hadoop命令路径
            hadoop_home = os.getenv('HADOOP_HOME', '/usr/local/hadoop')
            hadoop_bin = os.path.join(hadoop_home, 'bin')
            hadoop_cmd = os.path.join(hadoop_bin, 'hadoop')
            
            if not os.path.exists(hadoop_cmd):
                return False, f"Hadoop命令不存在: {hadoop_cmd}"
            
            # 创建用户目录
            hdfs_cmd = f"{hadoop_cmd} fs -mkdir -p /user/{username}"
            exit_code = os.system(hdfs_cmd)
            if exit_code != 0:
                return False, f"创建用户目录失败: {exit_code}"
                
            # 设置目录权限
            chmod_cmd = f"{hadoop_cmd} fs -chmod 755 /user/{username}"
            exit_code = os.system(chmod_cmd)
            if exit_code != 0:
                return False, f"设置目录权限失败: {exit_code}"
                
            return True, None
        except Exception as e:
            self.logger.error(f"设置用户环境失败: {e}")
            return False, str(e)
            
    def cleanup_user_session(self, username: str):
        """
        清理用户会话
        
        Args:
            username: 用户名
        """
        try:
            # 清理服务票据
            for service in ['hdfs', 'yarn', 'hive']:
                ticket_key = f"{username}_{service}"
                if ticket_key in self.service_tickets:
                    del self.service_tickets[ticket_key]
                    
            # 清理环境变量
            if 'HADOOP_USER_NAME' in os.environ:
                del os.environ['HADOOP_USER_NAME']
        except Exception as e:
            self.logger.error(f"清理用户会话失败: {e}") 