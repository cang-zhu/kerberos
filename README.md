# Kerberos认证系统

这是一个基于Hadoop的Kerberos认证系统，实现了基于TOTP的双因素认证机制。

## 核心功能

- 用户认证
  - 用户名密码登录
  - TOTP双因素认证（系统自动生成）
  - 用户注册和密码管理

- Kerberos集成
  - KDC服务管理
  - 票据认证
  - 多领域支持

- Hadoop管理
  - HDFS服务控制
  - 集群配置管理
  - 权限控制

- 系统管理
  - 用户和角色管理
  - 系统配置
  - 日志监控

## 环境要求

- macOS（已在macOS 24.1.0上测试）
- Windows 10/11（需要额外配置）
- Python 3.8+
- OpenJDK 11
- Hadoop 3.4.1
- Kerberos (krb5 1.21.3)

## 安装步骤

### macOS/Linux环境

1. 克隆项目并创建虚拟环境：
```bash
git clone <repository-url>
cd kerberos
python3 -m venv venv
source venv/bin/activate
```

### Windows环境

1. 克隆项目并创建虚拟环境：
```powershell
git clone <repository-url>
cd kerberos
python -m venv venv
.\venv\Scripts\activate
```

2. 安装Python依赖：
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

注意：Windows 环境下会自动安装适配的依赖：
- 使用 `winkerberos` 替代 `python-kerberos`
- 使用 `psycopg2` 替代 `psycopg2-binary`
- 使用 `waitress` 替代 `gunicorn`

3. 配置环境变量：
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑.env文件，设置必要的环境变量
# 主要配置项：
# - JAVA_HOME：Java安装路径
# - HADOOP_HOME：Hadoop安装路径
# - HIVE_HOME：Hive安装路径
# - KRB5_CONFIG：Kerberos配置文件路径
# - KRB5_KDC_PROFILE：KDC配置文件路径
# - KERBEROS_PATH：Kerberos可执行文件路径
```

4. 创建必要的目录：
```bash
# 创建Hadoop数据目录
mkdir -p $HADOOP_HOME/var/hadoop/dfs/{name,data}
mkdir -p $HADOOP_HOME/var/hadoop/kerberos/keytabs
mkdir -p $HADOOP_HOME/var/hadoop/tmp

# 创建Kerberos日志目录
mkdir -p /var/log/krb5kdc
```

5. 初始化数据库：
```bash
flask db upgrade
```

## 配置说明

1. Hadoop配置：
   - `config/hadoop/core-site.xml`：Hadoop核心配置
   - `config/hadoop/hdfs-site.xml`：HDFS配置

2. Kerberos配置：
   - `config/krb5.conf`：Kerberos主配置
   - `config/kdc.conf`：KDC服务器配置

3. 数据库配置：
   - 使用`scripts/update_db.py`管理用户和TOTP密钥

## 启动服务

1. 启动Kerberos KDC服务：
```bash
krb5kdc -n
```

2. 启动HDFS服务：
```bash
start-dfs.sh
```

3. 启动Web应用：
```bash
FLASK_APP=app.py flask run --host=0.0.0.0 --port=5002
```

## 使用说明

1. 访问Web界面：`http://localhost:5002`
2. 使用用户名和密码登录
3. 首次登录后，系统会自动生成TOTP密钥并显示二维码
4. 使用系统提供的TOTP密钥进行二次验证
5. 登录成功后可以进行HDFS操作

## 安全特性

- 双因素认证（用户名密码 + TOTP动态密码）
- 系统内置TOTP生成和验证
- Kerberos票据认证
- 基于时间的一次性密码（TOTP）
- 安全的密钥管理

## 目录结构

```
.
├── app.py                 # Flask应用主文件
├── config/               # 配置文件目录
│   ├── hadoop/          # Hadoop配置
│   └── krb5.conf        # Kerberos配置
├── scripts/             # 脚本文件
│   └── update_db.py     # 数据库管理脚本
├── static/              # 静态文件
├── templates/           # HTML模板
└── venv/               # Python虚拟环境
```

## 注意事项

1. 确保所有必要的目录权限正确
2. 首次运行需要初始化数据库和用户
3. 请妥善保管TOTP密钥
4. 定期更新TOTP密钥以提高安全性
5. 生产环境部署时请使用HTTPS 

### Windows环境

1. 克隆项目并创建虚拟环境：
```powershell
git clone <repository-url>
cd kerberos
python -m venv venv
.\venv\Scripts\activate
```

2. 安装Python依赖：
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

注意：Windows 环境下会自动安装适配的依赖：
- 使用 `winkerberos` 替代 `python-kerberos`
- 使用 `psycopg2` 替代 `psycopg2-binary`
- 使用 `waitress` 替代 `gunicorn`

3. 启动服务器：
```bash
# Windows环境
python run.py
# 或者使用 waitress
waitress-serve --port=5000 run:app

# Unix环境
gunicorn -w 4 -b 0.0.0.0:5000 run:app
```

## 配置说明

1. Hadoop配置：
   - `config/hadoop/core-site.xml`：Hadoop核心配置
   - `config/hadoop/hdfs-site.xml`：HDFS配置

2. Kerberos配置：
   - `config/krb5.conf`：Kerberos主配置
   - `config/kdc.conf`：KDC服务器配置

3. 数据库配置：
   - 使用`scripts/update_db.py`管理用户和TOTP密钥

## 启动服务

1. 启动Kerberos KDC服务：
```bash
krb5kdc -n
```

2. 启动HDFS服务：
```bash
start-dfs.sh
```

3. 启动Web应用：
```bash
FLASK_APP=app.py flask run --host=0.0.0.0 --port=5002
```

## 使用说明

1. 访问Web界面：`http://localhost:5002`
2. 使用用户名和密码登录
3. 首次登录后，系统会自动生成TOTP密钥并显示二维码
4. 使用系统提供的TOTP密钥进行二次验证
5. 登录成功后可以进行HDFS操作

## 安全特性

- 双因素认证（用户名密码 + TOTP动态密码）
- 系统内置TOTP生成和验证
- Kerberos票据认证
- 基于时间的一次性密码（TOTP）
- 安全的密钥管理

## 目录结构

```
.
├── app.py                 # Flask应用主文件
├── config/               # 配置文件目录
│   ├── hadoop/          # Hadoop配置
│   └── krb5.conf        # Kerberos配置
├── scripts/             # 脚本文件
│   └── update_db.py     # 数据库管理脚本
├── static/              # 静态文件
├── templates/           # HTML模板
└── venv/               # Python虚拟环境
```

## 注意事项

1. 确保所有必要的目录权限正确
2. 首次运行需要初始化数据库和用户
3. 请妥善保管TOTP密钥
4. 定期更新TOTP密钥以提高安全性
5. 生产环境部署时请使用HTTPS 