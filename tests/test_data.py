"""测试数据配置"""

# 测试用户数据
TEST_USERS = {
    'admin': {
        'username': 'admin',
        'password': 'admin_password',
        'roles': ['admin'],
        'is_active': True
    },
    'hdfs_user': {
        'username': 'hdfs_user',
        'password': 'hdfs_password',
        'roles': ['hdfs_user'],
        'is_active': True
    },
    'yarn_user': {
        'username': 'yarn_user',
        'password': 'yarn_password',
        'roles': ['yarn_user'],
        'is_active': True
    },
    'hive_user': {
        'username': 'hive_user',
        'password': 'hive_password',
        'roles': ['hive_user'],
        'is_active': True
    },
    'test_user': {
        'username': 'test_user',
        'password': 'test_password',
        'roles': ['user'],
        'is_active': True
    }
}

# 测试角色数据
TEST_ROLES = {
    'admin': {
        'name': 'admin',
        'description': '管理员角色',
        'permissions': ['manage_users', 'manage_hadoop']
    },
    'hdfs_user': {
        'name': 'hdfs_user',
        'description': 'HDFS用户角色',
        'permissions': ['use_hdfs']
    },
    'yarn_user': {
        'name': 'yarn_user',
        'description': 'YARN用户角色',
        'permissions': ['use_yarn']
    },
    'hive_user': {
        'name': 'hive_user',
        'description': 'Hive用户角色',
        'permissions': ['use_hive']
    },
    'user': {
        'name': 'user',
        'description': '普通用户角色',
        'permissions': ['use_hdfs', 'use_yarn', 'use_hive']
    }
}

# 测试权限数据
TEST_PERMISSIONS = {
    'manage_users': {
        'name': 'manage_users',
        'description': '管理用户权限'
    },
    'manage_hadoop': {
        'name': 'manage_hadoop',
        'description': '管理Hadoop集群权限'
    },
    'use_hdfs': {
        'name': 'use_hdfs',
        'description': '使用HDFS权限'
    },
    'use_yarn': {
        'name': 'use_yarn',
        'description': '使用YARN权限'
    },
    'use_hive': {
        'name': 'use_hive',
        'description': '使用Hive权限'
    }
}

# 测试集群配置数据
TEST_CLUSTER_CONFIG = {
    'namenode_host': 'namenode.example.com',
    'resourcemanager_host': 'resourcemanager.example.com',
    'metastore_host': 'metastore.example.com',
    'ssh_user': 'hadoop',
    'nodes': [
        {
            'hostname': 'namenode.example.com',
            'ip': '192.168.1.100',
            'roles': ['namenode', 'resourcemanager']
        },
        {
            'hostname': 'datanode1.example.com',
            'ip': '192.168.1.101',
            'roles': ['datanode', 'nodemanager']
        },
        {
            'hostname': 'datanode2.example.com',
            'ip': '192.168.1.102',
            'roles': ['datanode', 'nodemanager']
        },
        {
            'hostname': 'hive.example.com',
            'ip': '192.168.1.103',
            'roles': ['hiveserver']
        }
    ]
}

# 测试HDFS命令
TEST_HDFS_COMMANDS = {
    'list_root': '-ls /',
    'create_user_dir': '-mkdir -p /user/${user}',
    'set_permissions': '-chmod 755 /user/${user}',
    'create_test_file': '-touchz /user/${user}/test.txt',
    'cat_file': '-cat /user/${user}/test.txt'
}

# 测试YARN应用
TEST_YARN_APPLICATIONS = {
    'wordcount': {
        'path': '/path/to/wordcount.jar',
        'args': ['/input', '/output']
    },
    'pi': {
        'path': '/path/to/pi.jar',
        'args': ['10', '100']
    }
}

# 测试Hive查询
TEST_HIVE_QUERIES = {
    'create_table': '''
    CREATE TABLE IF NOT EXISTS test_table (
        id INT,
        name STRING,
        value DOUBLE
    )
    ''',
    'insert_data': '''
    INSERT INTO test_table
    VALUES (1, 'test1', 1.0),
           (2, 'test2', 2.0),
           (3, 'test3', 3.0)
    ''',
    'select_data': 'SELECT * FROM test_table',
    'drop_table': 'DROP TABLE IF EXISTS test_table'
}

# 测试环境变量
TEST_ENV = {
    'HADOOP_HOME': '/usr/local/hadoop',
    'HADOOP_CONF_DIR': '/etc/hadoop/conf',
    'YARN_CONF_DIR': '/etc/hadoop/conf',
    'HIVE_HOME': '/usr/local/hive',
    'JAVA_HOME': '/usr/java/default'
} 