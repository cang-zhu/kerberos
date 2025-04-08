#!/bin/bash
# 自动查找Kerberos和Hadoop相关服务路径并生成.env文件
# 用法: bash find_paths.sh

echo "正在查找服务路径..."

# 查找Hadoop路径
if [ -n "$HADOOP_HOME" ]; then
    echo "已设置HADOOP_HOME: $HADOOP_HOME"
else
    HADOOP_CMD=$(which hadoop 2>/dev/null)
    if [ -n "$HADOOP_CMD" ]; then
        HADOOP_HOME=$(dirname $(dirname $HADOOP_CMD))
        echo "找到Hadoop路径: $HADOOP_HOME"
    else
        # 尝试查找常见位置
        for path in /usr/local/hadoop /opt/hadoop /home/hadoop/hadoop; do
            if [ -d "$path" ]; then
                HADOOP_HOME=$path
                echo "找到Hadoop路径: $HADOOP_HOME"
                break
            fi
        done
        if [ -z "$HADOOP_HOME" ]; then
            HADOOP_HOME="/usr/local/hadoop"
            echo "未找到Hadoop，设置默认路径: $HADOOP_HOME"
        fi
    fi
fi

# 查找Java路径
if [ -n "$JAVA_HOME" ]; then
    echo "已设置JAVA_HOME: $JAVA_HOME"
else
    JAVA_CMD=$(which java 2>/dev/null)
    if [ -n "$JAVA_CMD" ]; then
        REAL_JAVA_PATH=$(readlink -f $JAVA_CMD)
        JAVA_BIN_DIR=$(dirname $REAL_JAVA_PATH)
        JAVA_HOME=$(dirname $JAVA_BIN_DIR)
        echo "找到Java路径: $JAVA_HOME"
        
        # 如果路径包含jre，则尝试去掉jre部分
        if [[ $JAVA_HOME == */jre ]]; then
            JAVA_HOME=$(dirname $JAVA_HOME)
            echo "修正Java路径: $JAVA_HOME"
        fi
    else
        # 尝试查找常见位置
        for path in /usr/lib/jvm/* /usr/java/latest; do
            if [ -d "$path" ] && [ -x "$path/bin/java" ]; then
                JAVA_HOME=$path
                echo "找到Java路径: $JAVA_HOME"
                break
            fi
        done
        if [ -z "$JAVA_HOME" ]; then
            JAVA_HOME="/usr/lib/jvm/java-1.8.0"
            echo "未找到Java，设置默认路径: $JAVA_HOME"
        fi
    fi
fi

# 查找Kerberos配置文件
KRB5_CONFIG=$(find /etc -name "krb5.conf" 2>/dev/null | head -1)
if [ -z "$KRB5_CONFIG" ]; then
    KRB5_CONFIG="/etc/krb5.conf"
    echo "未找到krb5.conf，设置默认路径: $KRB5_CONFIG"
else
    echo "找到krb5.conf: $KRB5_CONFIG"
fi

# 查找KDC配置
KRB5_KDC_PROFILE=$(find /var -name "kdc.conf" 2>/dev/null | head -1)
if [ -z "$KRB5_KDC_PROFILE" ]; then
    KRB5_KDC_PROFILE="/var/kerberos/krb5kdc/kdc.conf"
    echo "未找到kdc.conf，设置默认路径: $KRB5_KDC_PROFILE"
else
    echo "找到kdc.conf: $KRB5_KDC_PROFILE"
fi

# 查找KDC数据库路径
KDC_DB_DIR=$(dirname $KRB5_KDC_PROFILE 2>/dev/null)
KDC_DB_PATH="$KDC_DB_DIR/principal"
echo "设置KDC数据库路径: $KDC_DB_PATH"

# 查找Kerberos工具
KRB5_UTIL_PATH=$(which kdb5_util 2>/dev/null)
if [ -z "$KRB5_UTIL_PATH" ]; then
    KRB5_UTIL_PATH="/usr/sbin/kdb5_util"
    echo "未找到kdb5_util，设置默认路径: $KRB5_UTIL_PATH"
else
    echo "找到kdb5_util: $KRB5_UTIL_PATH"
fi

KRB5KDC_PATH=$(which krb5kdc 2>/dev/null)
if [ -z "$KRB5KDC_PATH" ]; then
    KRB5KDC_PATH="/usr/sbin/krb5kdc"
    echo "未找到krb5kdc，设置默认路径: $KRB5KDC_PATH"
else
    echo "找到krb5kdc: $KRB5KDC_PATH"
fi

KADMIND_PATH=$(which kadmind 2>/dev/null)
if [ -z "$KADMIND_PATH" ]; then
    KADMIND_PATH="/usr/sbin/kadmind"
    echo "未找到kadmind，设置默认路径: $KADMIND_PATH"
else
    echo "找到kadmind: $KADMIND_PATH"
fi

# 生成.env文件
echo "正在生成.env文件..."
cat > .env << EOF
# Hadoop环境配置
HADOOP_HOME=$HADOOP_HOME
JAVA_HOME=$JAVA_HOME

# Kerberos配置文件路径
KRB5_CONFIG=$KRB5_CONFIG
KRB5_KDC_PROFILE=$KRB5_KDC_PROFILE
KDC_DB_PATH=$KDC_DB_PATH

# Kerberos工具路径
KRB5_UTIL_PATH=$KRB5_UTIL_PATH
KRB5KDC_PATH=$KRB5KDC_PATH
KADMIND_PATH=$KADMIND_PATH

# 应用配置
SECRET_KEY=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 32 | head -n 1)
DEBUG=True
PORT=5002
EOF

echo ".env文件已生成，路径为: $(pwd)/.env"
echo "您可以使用 'cat .env' 查看生成的环境变量配置" 