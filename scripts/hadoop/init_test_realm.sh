#!/bin/bash

# 加载环境变量
source .env

# 设置日志函数
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# 检查是否以root权限运行
if [ "$EUID" -ne 0 ]; then 
    log "请使用root权限运行此脚本"
    exit 1
fi

# 设置变量
REALM=${KERBEROS_REALM:-EXAMPLE.COM}
ADMIN_USER=${KERBEROS_ADMIN_USER:-admin}
ADMIN_PASSWORD=${KERBEROS_ADMIN_PASSWORD:-admin123}
MASTER_KEY=${KERBEROS_MASTER_KEY:-kerberosGO}
HDFS_ADMIN_PASSWORD=${HDFS_ADMIN_PASSWORD:-hdfs123}
YARN_ADMIN_PASSWORD=${YARN_ADMIN_PASSWORD:-yarn123}
HIVE_ADMIN_PASSWORD=${HIVE_ADMIN_PASSWORD:-hive123}
KADMIN_PATH=${KERBEROS_PATH:-/usr/local/opt/krb5/sbin}/kadmin.local
KRB5_CONFIG=${KRB5_CONFIG:-/usr/local/etc/krb5.conf}
KEYTAB_DIR=${KEYTAB_DIR:-/var/hadoop/kerberos/keytabs}

# 导出环境变量
export KRB5_CONFIG

# 创建keytab目录
log "创建keytab目录..."
mkdir -p $KEYTAB_DIR

# 创建expect脚本
EXPECT_SCRIPT=$(mktemp)
cat > $EXPECT_SCRIPT << EOF
#!/usr/bin/expect -f

set timeout -1

proc handle_prompts {} {
    expect {
        "Max ticket life*" { send "\r"; exp_continue }
        "Max renewable life*" { send "\r"; exp_continue }
        "Principal expiration time*" { send "\r"; exp_continue }
        "Password expiration time*" { send "\r"; exp_continue }
        "Attributes*" { send "\r"; exp_continue }
        "Policy*" { send "\r"; exp_continue }
        "kadmin.local:" { return }
    }
}

# 启动kadmin
spawn ${KADMIN_PATH}

# 等待提示符
expect "kadmin.local:"

# 设置主密钥
send "change_password -pw ${MASTER_KEY} K/M@${REALM}\r"
handle_prompts

# 创建服务主体
send "addprinc -randkey nn/localhost@${REALM}\r"
handle_prompts

send "addprinc -randkey dn/localhost@${REALM}\r"
handle_prompts

send "addprinc -randkey rm/localhost@${REALM}\r"
handle_prompts

send "addprinc -randkey nm/localhost@${REALM}\r"
handle_prompts

# 创建管理员用户
send "addprinc -pw ${HDFS_ADMIN_PASSWORD} hdfs_admin@${REALM}\r"
handle_prompts

send "addprinc -pw ${YARN_ADMIN_PASSWORD} yarn_admin@${REALM}\r"
handle_prompts

send "addprinc -pw ${HIVE_ADMIN_PASSWORD} hive_admin@${REALM}\r"
handle_prompts

# 创建keytab文件
send "ktadd -k ${KEYTAB_DIR}/nn.service.keytab nn/localhost@${REALM}\r"
expect "kadmin.local:"
send "ktadd -k ${KEYTAB_DIR}/dn.service.keytab dn/localhost@${REALM}\r"
expect "kadmin.local:"
send "ktadd -k ${KEYTAB_DIR}/rm.service.keytab rm/localhost@${REALM}\r"
expect "kadmin.local:"
send "ktadd -k ${KEYTAB_DIR}/nm.service.keytab nm/localhost@${REALM}\r"
expect "kadmin.local:"

# 退出
send "quit\r"
expect eof
EOF

# 执行expect脚本
log "执行Kerberos管理命令..."
chmod +x $EXPECT_SCRIPT
$EXPECT_SCRIPT

# 清理临时文件
rm $EXPECT_SCRIPT

# 设置权限
chmod 600 $KEYTAB_DIR/*.keytab
chown -R $(whoami):admin $KEYTAB_DIR

log "TEST.COM域初始化完成！"
log "HDFS管理员密码: $HDFS_ADMIN_PASSWORD"
log "YARN管理员密码: $YARN_ADMIN_PASSWORD"
log "Hive管理员密码: $HIVE_ADMIN_PASSWORD" 