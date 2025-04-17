#!/bin/bash

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then 
    log_error "请使用root用户运行此脚本"
    exit 1
fi

# 设置变量
KRB5_CONFIG="/etc/krb5.conf"
KDC_CONFIG="/var/kerberos/krb5kdc/kdc.conf"
KDC_DIR="/var/kerberos/krb5kdc"
REALM="HADOOP.COM"
ADMIN_PRINCIPAL="admin/admin"
ADMIN_PW="admin123"  # 在生产环境中应该使用更安全的密码

# 1. 创建并设置目录权限
log_info "创建并设置目录权限..."
mkdir -p "$KDC_DIR"
chown -R root:root "$KDC_DIR"
chmod 700 "$KDC_DIR"

# 2. 备份现有配置
if [ -f "$KRB5_CONFIG" ]; then
    log_info "备份krb5.conf..."
    cp "$KRB5_CONFIG" "${KRB5_CONFIG}.bak.$(date +%Y%m%d_%H%M%S)"
fi

if [ -f "$KDC_CONFIG" ]; then
    log_info "备份kdc.conf..."
    cp "$KDC_CONFIG" "${KDC_CONFIG}.bak.$(date +%Y%m%d_%H%M%S)"
fi

# 3. 创建krb5.conf
log_info "创建krb5.conf..."
cat > "$KRB5_CONFIG" << EOF
[libdefaults]
    default_realm = $REALM
    dns_lookup_realm = false
    dns_lookup_kdc = false
    ticket_lifetime = 24h
    renew_lifetime = 7d
    forwardable = true
    rdns = false
    default_keytab_name = FILE:$KDC_DIR/krb5.keytab
    master_key_type = aes256-cts

[realms]
    $REALM = {
        kdc = localhost:88
        admin_server = localhost:749
        default_domain = hadoop.com
    }

[domain_realm]
    .hadoop.com = $REALM
    hadoop.com = $REALM

[logging]
    kdc = FILE:/var/log/krb5kdc.log
    admin_server = FILE:/var/log/kadmin.log
    default = FILE:/var/log/krb5lib.log
EOF

# 4. 创建kdc.conf
log_info "创建kdc.conf..."
mkdir -p "$(dirname "$KDC_CONFIG")"
cat > "$KDC_CONFIG" << EOF
[kdcdefaults]
    kdc_ports = 88
    kdc_tcp_ports = 88

[realms]
    $REALM = {
        database_name = $KDC_DIR/principal
        admin_keytab = $KDC_DIR/kadm5.keytab
        acl_file = $KDC_DIR/kadm5.acl
        key_stash_file = $KDC_DIR/.k5.$REALM
        max_life = 24h 0m 0s
        max_renewable_life = 7d 0h 0m 0s
        master_key_type = aes256-cts
        supported_enctypes = aes256-cts:normal aes128-cts:normal
        default_principal_flags = +preauth
    }
EOF

# 5. 创建kadm5.acl
log_info "创建kadm5.acl..."
echo "*/admin@$REALM  *" > "$KDC_DIR/kadm5.acl"
chmod 600 "$KDC_DIR/kadm5.acl"

# 6. 停止Kerberos服务
log_info "停止Kerberos服务..."
systemctl stop krb5kdc kadmin || true

# 7. 删除现有数据库
log_info "删除现有数据库..."
rm -f $KDC_DIR/principal* $KDC_DIR/.k5.* $KDC_DIR/kadm5.keytab

# 8. 创建新的KDC数据库
log_info "创建新的KDC数据库..."
echo -e "$ADMIN_PW\n$ADMIN_PW" | kdb5_util create -s

# 9. 创建管理员主体
log_info "创建管理员主体..."
kadmin.local -q "addprinc -pw $ADMIN_PW $ADMIN_PRINCIPAL@$REALM"

# 10. 设置文件权限
log_info "设置文件权限..."
chown -R root:root "$KDC_DIR"
find "$KDC_DIR" -type f -exec chmod 600 {} \;
find "$KDC_DIR" -type d -exec chmod 700 {} \;

# 11. 启动Kerberos服务
log_info "启动Kerberos服务..."
systemctl start krb5kdc
systemctl start kadmin

# 12. 验证服务状态
log_info "验证服务状态..."
if systemctl is-active --quiet krb5kdc && systemctl is-active --quiet kadmin; then
    log_info "Kerberos服务已成功启动"
    
    # 测试管理员主体
    if kadmin.local -q "getprinc $ADMIN_PRINCIPAL@$REALM" > /dev/null 2>&1; then
        log_info "管理员主体验证成功"
        log_info "修复完成！"
        echo -e "\n${GREEN}Kerberos配置已修复。请使用以下信息访问：${NC}"
        echo -e "管理员主体: ${YELLOW}$ADMIN_PRINCIPAL@$REALM${NC}"
        echo -e "管理员密码: ${YELLOW}$ADMIN_PW${NC}"
    else
        log_error "管理员主体验证失败"
    fi
else
    log_error "Kerberos服务启动失败，请检查系统日志"
fi 