"""测试配置"""

import os
import tempfile
import json
from typing import Dict, Any

# 测试配置目录
TEST_CONFIG_DIR = tempfile.mkdtemp()

# 测试环境变量
TEST_ENV_VARS = {
    'FLASK_ENV': 'testing',
    'FLASK_DEBUG': '1',
    'FLASK_APP': 'web/app.py',
    'PYTHONPATH': os.getcwd(),
    'HADOOP_HOME': '/usr/local/hadoop',
    'HADOOP_CONF_DIR': os.path.join(TEST_CONFIG_DIR, 'hadoop/conf'),
    'YARN_CONF_DIR': os.path.join(TEST_CONFIG_DIR, 'hadoop/conf'),
    'HIVE_HOME': '/usr/local/hive',
    'JAVA_HOME': '/usr/java/default'
}

# 测试数据库配置
TEST_DB_CONFIG = {
    'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
    'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    'SECRET_KEY': 'test_secret_key',
    'WTF_CSRF_ENABLED': False
}

# 测试Hadoop配置
TEST_HADOOP_CONFIG = {
    'core-site.xml': '''<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>
<configuration>
    <property>
        <name>fs.defaultFS</name>
        <value>hdfs://namenode.example.com:8020</value>
    </property>
</configuration>''',
    
    'hdfs-site.xml': '''<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>
<configuration>
    <property>
        <name>dfs.replication</name>
        <value>1</value>
    </property>
    <property>
        <name>dfs.namenode.name.dir</name>
        <value>/tmp/hadoop/name</value>
    </property>
    <property>
        <name>dfs.datanode.data.dir</name>
        <value>/tmp/hadoop/data</value>
    </property>
</configuration>''',
    
    'yarn-site.xml': '''<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>
<configuration>
    <property>
        <name>yarn.resourcemanager.hostname</name>
        <value>resourcemanager.example.com</value>
    </property>
    <property>
        <name>yarn.nodemanager.aux-services</name>
        <value>mapreduce_shuffle</value>
    </property>
</configuration>''',
    
    'hive-site.xml': '''<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>
<configuration>
    <property>
        <name>javax.jdo.option.ConnectionURL</name>
        <value>jdbc:derby:memory:testdb;create=true</value>
    </property>
    <property>
        <name>hive.metastore.uris</name>
        <value>thrift://metastore.example.com:9083</value>
    </property>
</configuration>'''
}

def setup_test_env() -> str:
    """设置测试环境
    
    Returns:
        str: 测试配置目录路径
    """
    # 设置环境变量
    for key, value in TEST_ENV_VARS.items():
        os.environ[key] = value
    
    # 创建Hadoop配置目录
    hadoop_conf_dir = os.path.join(TEST_CONFIG_DIR, 'hadoop/conf')
    os.makedirs(hadoop_conf_dir, exist_ok=True)
    
    # 写入Hadoop配置文件
    for filename, content in TEST_HADOOP_CONFIG.items():
        with open(os.path.join(hadoop_conf_dir, filename), 'w') as f:
            f.write(content)
    
    return TEST_CONFIG_DIR

def cleanup_test_env(config_dir: str):
    """清理测试环境
    
    Args:
        config_dir: 测试配置目录路径
    """
    # 清理环境变量
    for key in TEST_ENV_VARS.keys():
        if key in os.environ:
            del os.environ[key]
    
    # 删除测试配置目录
    if os.path.exists(config_dir):
        import shutil
        shutil.rmtree(config_dir)

def get_test_config() -> Dict[str, Any]:
    """获取测试配置
    
    Returns:
        Dict[str, Any]: 测试配置字典
    """
    return {
        'env': TEST_ENV_VARS,
        'db': TEST_DB_CONFIG,
        'hadoop': TEST_HADOOP_CONFIG
    } 