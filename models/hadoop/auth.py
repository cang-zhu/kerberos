"""Hadoop权限模型定义"""

class HadoopGroups:
    """Hadoop用户组定义"""
    HDFS_ADMINS = "hdfs_admins"      # HDFS管理员组
    YARN_ADMINS = "yarn_admins"      # YARN管理员组
    HIVE_ADMINS = "hive_admins"      # Hive管理员组
    HADOOP_USERS = "hadoop_users"     # 普通Hadoop用户组

class HadoopPermissions:
    """Hadoop权限定义"""
    HDFS_MANAGE = "hdfs_manage"       # 管理HDFS服务
    YARN_MANAGE = "yarn_manage"       # 管理YARN服务
    HIVE_MANAGE = "hive_manage"       # 管理Hive服务
    HDFS_USE = "hdfs_use"            # 使用HDFS
    YARN_USE = "yarn_use"            # 使用YARN
    HIVE_USE = "hive_use"            # 使用Hive 