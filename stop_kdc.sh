#!/bin/bash

# 停止KDC服务
if [ -f kdc.pid ]; then
    KDC_PID=$(cat kdc.pid)
    if ps -p $KDC_PID > /dev/null; then
        kill $KDC_PID
        echo "KDC 服务已停止"
    else
        echo "KDC 服务未运行"
    fi
    rm kdc.pid
else
    echo "KDC PID文件不存在"
fi

# 停止管理服务器
if [ -f kadmin.pid ]; then
    KADMIN_PID=$(cat kadmin.pid)
    if ps -p $KADMIN_PID > /dev/null; then
        kill $KADMIN_PID
        echo "Kadmin 服务已停止"
    else
        echo "Kadmin 服务未运行"
    fi
    rm kadmin.pid
else
    echo "Kadmin PID文件不存在"
fi

echo "Kerberos 服务已停止" 