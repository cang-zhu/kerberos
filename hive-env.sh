#!/bin/bash

# 加载环境变量
source .env

# 设置默认路径
export JAVA_HOME=${JAVA_HOME:-/usr/lib/jvm/java-11-openjdk}
export HADOOP_HOME=${HADOOP_HOME:-/usr/local/hadoop}
export HADOOP_CONF_DIR=${HADOOP_CONF_DIR:-$HADOOP_HOME/etc/hadoop}
export HADOOP_CLASSPATH=${HADOOP_CLASSPATH:-$JAVA_HOME/lib/tools.jar}
export HIVE_HOME=${HIVE_HOME:-/usr/local/hive}
export HIVE_CONF_DIR=${HIVE_CONF_DIR:-$HIVE_HOME/conf}
export HIVE_CLASSPATH=${HIVE_CLASSPATH:-$HIVE_CONF_DIR}
export HADOOP_LOG_DIR=${HADOOP_LOG_DIR:-/var/log/hadoop}

export HADOOP_COMMON_HOME=$HADOOP_HOME
export HADOOP_HDFS_HOME=$HADOOP_HOME
export HADOOP_MAPRED_HOME=$HADOOP_HOME
export HADOOP_YARN_HOME=$HADOOP_HOME
export HADOOP_COMMON_LIB_NATIVE_DIR=$HADOOP_HOME/lib/native
export HADOOP_OPTS="-Djava.library.path=$HADOOP_HOME/lib/native"
export PATH=$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$HIVE_HOME/bin:$PATH

# 确保日志配置文件存在
mkdir -p $HADOOP_LOG_DIR
