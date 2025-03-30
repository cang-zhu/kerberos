#!/bin/bash

# 加载环境变量
source .env

# 设置环境变量
export KRB5_CONFIG=$(pwd)/config/krb5.conf
export KRB5_KDC_PROFILE=$(pwd)/config/kdc.conf

# 设置Kerberos路径
KRB5_PATH=${KERBEROS_PATH:-/usr/local/opt/krb5}

# 启动KDC服务
$KRB5_PATH/sbin/krb5kdc -n &
KDC_PID=$!
echo "KDC 服务已启动，PID: $KDC_PID"
echo $KDC_PID > kdc.pid

# 启动管理服务器
$KRB5_PATH/sbin/kadmind -nofork &
KADMIN_PID=$!
echo "Kadmin 服务已启动，PID: $KADMIN_PID"
echo $KADMIN_PID > kadmin.pid

echo "Kerberos 服务已启动!"
echo "使用 ./stop_kdc.sh 停止服务" 