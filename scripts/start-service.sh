#!/bin/bash

# 加载环境变量
source .env

# 检查参数
if [ $# -lt 2 ]; then
    echo "Usage: $0 <service_type> <user>"
    echo "Example: $0 namenode hdfs_user"
    exit 1
fi

SERVICE_TYPE=$1
USER=$2

# 设置环境变量
export JAVA_HOME=${JAVA_HOME:-/usr/lib/jvm/java-11-openjdk}
export HADOOP_HOME=${HADOOP_HOME:-/usr/local/hadoop}
export HADOOP_CONF_DIR=${HADOOP_CONF_DIR:-$HADOOP_HOME/etc/hadoop}
export PATH=$PATH:$HADOOP_HOME/bin:$HADOOP_HOME/sbin

# 设置Kerberos配置
export KRB5_CONFIG=${KRB5_CONFIG:-/usr/local/etc/krb5.conf}

# 设置keytab路径
KEYTAB_DIR=${KEYTAB_DIR:-/var/hadoop/kerberos/keytabs}

# 根据用户类型获取对应的keytab文件和principal
case $USER in
    "hdfs_user")
        KEYTAB="${KEYTAB_DIR}/nn.service.keytab"
        PRINCIPAL="nn/localhost@${KERBEROS_REALM:-EXAMPLE.COM}"
        ;;
    "yarn_user")
        KEYTAB="${KEYTAB_DIR}/rm.service.keytab"
        PRINCIPAL="rm/localhost@${KERBEROS_REALM:-EXAMPLE.COM}"
        ;;
    *)
        echo "Unknown user: $USER"
        exit 1
        ;;
esac

# 进行Kerberos认证
echo "Authenticating with Kerberos..."
kinit -kt $KEYTAB $PRINCIPAL

# 根据服务类型启动对应服务
case $SERVICE_TYPE in
    "namenode")
        if [ "$USER" != "hdfs_user" ]; then
            echo "Error: NameNode can only be started by hdfs_user"
            exit 1
        fi
        hadoop-daemon.sh start namenode
        ;;
    "datanode")
        if [ "$USER" != "hdfs_user" ]; then
            echo "Error: DataNode can only be started by hdfs_user"
            exit 1
        fi
        hadoop-daemon.sh start datanode
        ;;
    "resourcemanager")
        if [ "$USER" != "yarn_user" ]; then
            echo "Error: ResourceManager can only be started by yarn_user"
            exit 1
        fi
        yarn-daemon.sh start resourcemanager
        ;;
    "nodemanager")
        if [ "$USER" != "yarn_user" ]; then
            echo "Error: NodeManager can only be started by yarn_user"
            exit 1
        fi
        yarn-daemon.sh start nodemanager
        ;;
    *)
        echo "Unknown service type: $SERVICE_TYPE"
        exit 1
        ;;
esac

# 检查服务状态
jps 