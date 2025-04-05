#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import subprocess
import logging
import base64
import tempfile
from datetime import datetime, timedelta
from flask import session

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('kerberos_auth')

class KerberosAuth:
    """Kerberos认证管理类"""
    
    def __init__(self):
        """初始化Kerberos环境"""
        # 使用项目目录下的配置文件
        self.conf_file = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'config/krb5.conf')
        self.logger = logging.getLogger('kerberos_auth')
        
        # 开发模式标志
        self.dev_mode = True
        
        # 初始化环境变量
        self.env = os.environ.copy()
        self.env['KRB5_CONFIG'] = self.conf_file
    
    def set_mode(self, dev_mode=True):
        """设置认证模式
        
        Args:
            dev_mode (bool): 是否使用开发模式
        """
        self.dev_mode = dev_mode
        self.logger.info(f"设置认证模式: {'开发环境' if dev_mode else '生产环境'}")
        
        if not dev_mode:
            # 检查是否有必要的工具
            try:
                subprocess.run(['kinit', '--version'], 
                             stdout=subprocess.PIPE, 
                             stderr=subprocess.PIPE, 
                             env=self.env)
                self.logger.info("检测到Kerberos工具 (kinit)")
            except FileNotFoundError:
                self.logger.error("未找到Kerberos工具 (kinit)，切换回开发模式")
                self.dev_mode = True
    
    def initialize(self):
        """初始化Kerberos环境"""
        self.logger.info("初始化Kerberos环境")
        
        if not os.path.exists(self.conf_file):
            self.logger.error(f"Kerberos配置文件不存在: {self.conf_file}")
            
            # 创建示例配置文件
            if self.dev_mode:
                self.create_sample_config()
                self.logger.info(f"已创建示例配置文件: {self.conf_file}")
        else:
            self.logger.info(f"使用Kerberos配置: {self.conf_file}")
    
    def authenticate(self, principal, password, realm='HADOOP.COM'):
        """使用Kerberos认证用户
        
        Args:
            principal (str): 主体名称
            password (str): 密码
            realm (str): 领域
        
        Returns:
            bool: 认证是否成功
        """
        # 在开发模式下使用系统内置认证
        if self.dev_mode:
            return self.simulate_auth(principal, password, realm)
            
        # 从principal中提取领域信息
        if '@' in principal:
            parts = principal.split('@')
            principal_name = parts[0]
            # 如果在principal中指定了领域，则覆盖参数传入的领域
            if len(parts) > 1:
                realm = parts[1]
            full_principal = principal
        else:
            principal_name = principal
            full_principal = f"{principal}@{realm}"
        
        # 使用真实的Kerberos认证
        self.logger.info(f"尝试Kerberos认证: {full_principal}")
        
        try:
            # 设置特定领域的环境变量
            env = self.env.copy()
            env['KRB5CCNAME'] = f"FILE:/tmp/krb5cc_{os.getuid()}_{realm.lower()}"
            
            # 使用kinit获取票据
            kinit_process = subprocess.Popen(
                ['kinit', full_principal],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env
            )
            
            # 输入密码
            kinit_process.stdin.write(f"{password}\n".encode())
            kinit_process.stdin.flush()
            
            # 获取输出
            stdout, stderr = kinit_process.communicate()
            
            # 检查结果
            if kinit_process.returncode == 0:
                self.logger.info(f"认证成功: {full_principal}")
                return True
            else:
                stderr_str = stderr.decode()
                self.logger.error(f"认证失败: {stderr_str}")
                return False
        
        except Exception as e:
            self.logger.error(f"认证过程出错: {str(e)}")
            return False
    
    def verify_ticket(self):
        """验证当前票据是否有效
        
        Returns:
            tuple: (是否有效, 主体名称, 到期时间)
        """
        try:
            # 执行klist命令检查票据
            klist_process = subprocess.Popen(
                ['klist'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=self.env
            )
            
            # 获取输出
            stdout, stderr = klist_process.communicate()
            output = stdout.decode()
            
            # 检查是否有票据
            if "No credentials cache found" in output or "票据缓存中没有凭据" in output:
                self.logger.warning("没有找到Kerberos票据")
                return (False, None, None)
            
            # 解析主体名称
            principal_line = [line for line in output.split('\n') if "Default principal:" in line or "默认主体:" in line]
            if not principal_line:
                self.logger.warning("无法解析主体名称")
                return (False, None, None)
            
            principal = principal_line[0].split(':')[1].strip()
            
            # 解析到期时间
            expiry_lines = [line for line in output.split('\n') if "valid until" in line or "有效期至" in line]
            if not expiry_lines:
                self.logger.warning("无法解析票据到期时间")
                return (False, principal, None)
            
            # 尝试解析日期时间
            try:
                expiry_text = expiry_lines[0].split('valid until')[1].strip()
                expiry_time = datetime.strptime(expiry_text, "%m/%d/%Y %H:%M:%S")
            except:
                try:
                    # 尝试其他日期格式
                    expiry_text = expiry_lines[0].split('有效期至')[1].strip()
                    expiry_time = datetime.strptime(expiry_text, "%Y-%m-%d %H:%M:%S")
                except:
                    self.logger.warning(f"无法解析到期时间: {expiry_lines[0]}")
                    expiry_time = datetime.now() + timedelta(hours=10)  # 默认10小时
            
            # 检查是否过期
            is_valid = expiry_time > datetime.now()
            
            return (is_valid, principal, expiry_time)
        
        except Exception as e:
            self.logger.error(f"验证票据出错: {str(e)}")
            return (False, None, None)
    
    def logout(self):
        """销毁Kerberos票据"""
        try:
            # 执行kdestroy命令销毁票据
            subprocess.run(['kdestroy'], env=self.env, check=True)
            self.logger.info("已销毁Kerberos票据")
            return True
        except Exception as e:
            self.logger.error(f"销毁票据出错: {str(e)}")
            return False
    
    def get_principal_info(self, principal):
        """获取主体信息
        
        Args:
            principal (str): 主体名称
        
        Returns:
            dict: 主体信息
        """
        try:
            # 执行kadmin.local命令获取主体信息
            cmd = ['kadmin.local', '-q', f'getprinc {principal}']
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=self.env
            )
            
            # 获取输出
            stdout, stderr = process.communicate()
            output = stdout.decode()
            
            # 解析输出
            info = {}
            lines = output.split('\n')
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    info[key.strip()] = value.strip()
            
            return info
        
        except Exception as e:
            self.logger.error(f"获取主体信息出错: {str(e)}")
            return {}
    
    def create_sample_config(self):
        """创建示例配置文件（用于开发环境）"""
        # 获取配置文件目录
        config_dir = os.path.dirname(self.conf_file)
        
        # 创建目录
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        
        # Krb5.conf 示例内容
        krb5_conf = """
[libdefaults]
    default_realm = HADOOP.COM
    dns_lookup_realm = false
    dns_lookup_kdc = false
    ticket_lifetime = 24h
    renew_lifetime = 7d
    forwardable = true

[realms]
    HADOOP.COM = {
        kdc = hadoop-master.example.com
        admin_server = hadoop-master.example.com
    }

[domain_realm]
    .example.com = HADOOP.COM
    example.com = HADOOP.COM
"""
        
        # 写入配置文件
        with open(self.conf_file, 'w') as f:
            f.write(krb5_conf)
    
    def simulate_auth(self, principal, password, realm='HADOOP.COM'):
        """Kerberos认证（开发环境）
        
        Args:
            principal (str): 主体名称
            password (str): 密码
            realm (str): 领域
        
        Returns:
            bool: 认证是否成功
        """
        self.logger.info(f"进行Kerberos认证: {principal}@{realm}")
        
        # 从principal@REALM格式中提取主体名称
        if '@' in principal:
            parts = principal.split('@')
            principal = parts[0]
            # 如果在principal中指定了领域，则覆盖参数传入的领域
            if len(parts) > 1:
                realm = parts[1]
        
        # 首先尝试使用KDC验证（如果KDC服务正在运行）
        try:
            # 构建完整的主体名称
            full_principal = f"{principal}@{realm}"
            
            # 设置环境变量
            env = self.env.copy()
            env['KRB5_CONFIG'] = self.conf_file
            
            # 使用kadmin.local检查主体是否存在
            cmd = f"kadmin.local -q \"getprinc {full_principal}\" | grep Principal"
            process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env
            )
            
            stdout, stderr = process.communicate()
            output = stdout.decode()
            
            # 如果主体存在，尝试使用kinit进行认证
            if full_principal in output:
                self.logger.info(f"发现KDC中的主体: {full_principal}，尝试认证")
                
                # 使用kinit尝试认证
                kinit_cmd = f"echo '{password}' | kinit {full_principal}"
                kinit_process = subprocess.Popen(
                    kinit_cmd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env
                )
                
                stdout, stderr = kinit_process.communicate()
                
                # 判断认证是否成功
                if kinit_process.returncode == 0:
                    self.logger.info(f"KDC认证成功: {full_principal}")
                    
                    # 清理票据缓存
                    subprocess.run(['kdestroy'], env=env)
                    
                    return True
                else:
                    self.logger.warning(f"KDC认证失败: {full_principal}, {stderr.decode()}")
            else:
                self.logger.warning(f"KDC中未找到主体: {full_principal}")
        
        except Exception as e:
            self.logger.warning(f"KDC认证过程出错，使用系统内置凭据: {str(e)}")
        
        # 如果KDC认证失败或出错，回退到内置的凭据验证
        # 不同领域的认证凭据
        realm_credentials = {
            'HADOOP.COM': {
                'admin': 'admin123',
                'user': 'user123',
                'hdfs': 'hdfs123',
                'yarn': 'yarn123',
                'hive': 'hive123'
            },
            'DEV.LOCAL': {
                'admin': 'admin123',
                'dev': 'dev123',
                'test': 'test123'
            },
            'TEST.COM': {
                'admin': 'admin123',
                'tester': 'tester123',
                'hdfs_admin': 'hdfs123',
                'yarn_admin': 'yarn123',
                'hive_admin': 'hive123'
            }
        }
        
        # 获取指定领域的凭据
        valid_credentials = realm_credentials.get(realm, {})
        
        # 检查主体名称和密码
        if principal in valid_credentials and valid_credentials[principal] == password:
            self.logger.info(f"系统认证成功: {principal}@{realm}")
            return True
        else:
            self.logger.warning(f"认证失败: {principal}@{realm}")
            return False
            
    def create_principal(self, principal, password, realm='HADOOP.COM'):
        """创建Kerberos主体
        
        Args:
            principal (str): 主体名称
            password (str): 密码
            realm (str): 领域
        
        Returns:
            bool: 是否创建成功
        """
        try:
            # 构建完整的主体名称
            if '@' not in principal:
                full_principal = f"{principal}@{realm}"
            else:
                full_principal = principal

            # 使用kadmin.local创建主体
            cmd = ['/Users/huaisang/Homebrew/opt/krb5/sbin/kadmin.local', '-q', f'addprinc -pw {password} {full_principal}']
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=self.env
            )
            
            # 获取输出
            stdout, stderr = process.communicate()
            output = stdout.decode()
            
            # 检查是否创建成功
            if "Principal" in output and "created" in output:
                self.logger.info(f"成功创建主体: {full_principal}")
                return True
            else:
                self.logger.error(f"创建主体失败: {output}")
                return False
                
        except Exception as e:
            self.logger.error(f"创建主体出错: {str(e)}")
            return False

# 创建一个模拟的krb5.conf配置文件
def create_sample_krb5_conf(conf_path='/etc/krb5/krb5.conf'):
    """
    创建一个示例的krb5.conf配置文件
    
    Args:
        conf_path: 配置文件路径
    """
    conf_dir = os.path.dirname(conf_path)
    if not os.path.exists(conf_dir):
        os.makedirs(conf_dir, exist_ok=True)
        
    config = """[libdefaults]
  default_realm = HADOOP.COM
  dns_lookup_realm = false
  dns_lookup_kdc = false
  ticket_lifetime = 24h
  renew_lifetime = 7d
  forwardable = true

[realms]
  HADOOP.COM = {
    kdc = kdc.hadoop.example.com:88
    admin_server = kdc.hadoop.example.com:749
  }

[domain_realm]
  .hadoop.example.com = HADOOP.COM
  hadoop.example.com = HADOOP.COM
"""
    try:
        with open(conf_path, 'w') as f:
            f.write(config)
        logger.info(f"创建示例krb5.conf配置文件: {conf_path}")
    except Exception as e:
        logger.error(f"创建示例krb5.conf配置文件失败: {str(e)}") 