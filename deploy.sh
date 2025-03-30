#!/bin/bash

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then 
    echo "请使用root权限运行此脚本"
    exit 1
fi

# 配置主机名
echo "配置主机名..."
hostnamectl set-hostname $1

# 配置hosts文件
echo "配置hosts文件..."
cat >> /etc/hosts << EOF
192.168.1.10 master.example.com master
192.168.1.11 slave1.example.com slave1
192.168.1.12 slave2.example.com slave2
192.168.1.13 kdc.example.com kdc
EOF

# 安装必要的软件包
echo "安装软件包..."
yum update -y
yum install -y epel-release
yum install -y java-1.8.0-openjdk-devel
yum install -y wget curl net-tools
yum install -y python3 python3-devel gcc postgresql-server postgresql-devel

# 安装Hadoop
echo "安装Hadoop..."
wget https://downloads.apache.org/hadoop/common/hadoop-3.3.1/hadoop-3.3.1.tar.gz
tar -xzf hadoop-3.3.1.tar.gz -C /opt/
mv /opt/hadoop-3.3.1 /opt/hadoop

# 配置环境变量
echo "配置环境变量..."
cat >> /etc/profile << EOF
export JAVA_HOME=/usr/lib/jvm/java-1.8.0-openjdk
export HADOOP_HOME=/opt/hadoop
export PATH=\$PATH:\$JAVA_HOME/bin:\$HADOOP_HOME/bin:\$HADOOP_HOME/sbin
EOF
source /etc/profile

# 安装Kerberos
echo "安装Kerberos..."
yum install -y krb5-server krb5-libs krb5-workstation

# 配置Kerberos
echo "配置Kerberos..."
cat > /etc/krb5.conf << EOF
[libdefaults]
    default_realm = EXAMPLE.COM
    dns_lookup_kdc = false
    dns_lookup_realm = false
    ticket_lifetime = 24h
    renew_lifetime = 7d
    forwardable = true
    rdns = false

[realms]
    EXAMPLE.COM = {
        kdc = kdc.example.com
        admin_server = kdc.example.com
    }

[domain_realm]
    .example.com = EXAMPLE.COM
    example.com = EXAMPLE.COM
EOF

# 如果是KDC服务器，初始化KDC数据库
if [ "$1" = "kdc.example.com" ]; then
    echo "初始化KDC数据库..."
    kdb5_util create -s
    systemctl start krb5kdc
    systemctl start kadmin
    systemctl enable krb5kdc
    systemctl enable kadmin

    # 创建管理员用户
    kadmin.local -q "addprinc admin/admin"
    kadmin.local -q "addprinc -randkey HTTP/kdc.example.com"
    kadmin.local -q "ktadd -k /etc/krb5.keytab HTTP/kdc.example.com"
fi

# 配置PostgreSQL
echo "配置PostgreSQL..."
postgresql-setup --initdb
systemctl start postgresql
systemctl enable postgresql

# 创建数据库和用户
echo "配置数据库..."
su - postgres -c "psql -c 'CREATE DATABASE kerberos_auth;'"
su - postgres -c "psql -c 'ALTER USER postgres WITH PASSWORD '\''postgres'\'';'"

# 创建项目目录
echo "创建项目目录..."
mkdir -p /opt/kerberos-auth
cp -r ./* /opt/kerberos-auth/
cd /opt/kerberos-auth

# 创建虚拟环境
echo "创建虚拟环境..."
python3 -m venv venv
source venv/bin/activate

# 安装Python依赖
echo "安装Python依赖..."
pip install --upgrade pip
pip install -r requirements.txt

# 配置Web应用
echo "配置Web应用..."
cp .env.example .env
sed -i 's/your-secret-key-here/$(openssl rand -hex 32)/' .env

# 初始化数据库
echo "初始化数据库..."
export PYTHONPATH=.
export FLASK_ENV=development
flask db init
flask db migrate
flask db upgrade

# 配置防火墙
echo "配置防火墙..."
firewall-cmd --permanent --add-port=5000/tcp
firewall-cmd --permanent --add-port=88/tcp
firewall-cmd --permanent --add-port=88/udp
firewall-cmd --permanent --add-port=749/tcp
firewall-cmd --reload

# 配置SELinux
echo "配置SELinux..."
setenforce 0
sed -i 's/SELINUX=enforcing/SELINUX=permissive/' /etc/selinux/config

# 安装systemd服务
echo "安装systemd服务..."
cp kerberos-auth.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable kerberos-auth
systemctl start kerberos-auth

echo "部署完成！" 