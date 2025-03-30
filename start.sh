#!/bin/bash

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then 
    echo "请使用root权限运行此脚本"
    exit 1
fi

# 启动Kerberos服务
echo "启动Kerberos服务..."
systemctl start krb5kdc
systemctl start kadmin

# 启动PostgreSQL
echo "启动PostgreSQL..."
systemctl start postgresql

# 启动Hadoop服务
echo "启动Hadoop服务..."
if [ "$(hostname)" = "master.example.com" ]; then
    # 主节点
    hdfs namenode -format
    start-dfs.sh
    start-yarn.sh
else
    # 从节点
    hdfs datanode
    yarn nodemanager
fi

# 启动Web应用
echo "启动Web应用..."
cd /opt/kerberos-auth
source venv/bin/activate
export PYTHONPATH=.
export FLASK_ENV=development

# 使用gunicorn启动应用
gunicorn -w 4 -b 0.0.0.0:5000 web.app:app --daemon --pid /var/run/kerberos-auth.pid --log-file /var/log/kerberos-auth.log 