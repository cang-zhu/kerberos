import os
import logging
from typing import Dict, Optional
import xml.etree.ElementTree as ET

class HadoopConfigManager:
    def __init__(self, config_dir: str):
        self.config_dir = config_dir
        self.logger = logging.getLogger(__name__)
        self.config_files = {
            'core-site.xml': os.path.join(config_dir, 'core-site.xml'),
            'hdfs-site.xml': os.path.join(config_dir, 'hdfs-site.xml'),
            'yarn-site.xml': os.path.join(config_dir, 'yarn-site.xml'),
            'hive-site.xml': os.path.join(config_dir, 'hive-site.xml')
        }

    def read_xml_config(self, file_path: str) -> Dict[str, str]:
        """
        读取XML配置文件
        
        Args:
            file_path: 配置文件路径
            
        Returns:
            Dict[str, str]: 配置项字典
        """
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            config = {}
            
            for prop in root.findall('./property'):
                name = prop.find('name').text
                value = prop.find('value').text
                config[name] = value
                
            return config
        except Exception as e:
            self.logger.error(f"读取配置文件失败: {e}")
            return {}

    def write_xml_config(self, file_path: str, config: Dict[str, str]) -> bool:
        """
        写入XML配置文件
        
        Args:
            file_path: 配置文件路径
            config: 配置项字典
            
        Returns:
            bool: 是否成功写入
        """
        try:
            root = ET.Element('configuration')
            
            for name, value in config.items():
                prop = ET.SubElement(root, 'property')
                name_elem = ET.SubElement(prop, 'name')
                name_elem.text = name
                value_elem = ET.SubElement(prop, 'value')
                value_elem.text = value
            
            tree = ET.ElementTree(root)
            tree.write(file_path, encoding='utf-8', xml_declaration=True)
            return True
        except Exception as e:
            self.logger.error(f"写入配置文件失败: {e}")
            return False

    def update_hdfs_config(self, namenode_host: str, namenode_port: int = 9000) -> bool:
        """
        更新HDFS配置
        
        Args:
            namenode_host: NameNode主机名
            namenode_port: NameNode端口号
            
        Returns:
            bool: 是否成功更新
        """
        core_site = {
            'fs.defaultFS': f'hdfs://{namenode_host}:{namenode_port}',
            'hadoop.tmp.dir': '/tmp/hadoop-${user.name}'
        }
        
        hdfs_site = {
            'dfs.replication': '2',
            'dfs.namenode.name.dir': '/data/hadoop/namenode',
            'dfs.datanode.data.dir': '/data/hadoop/datanode'
        }
        
        return (
            self.write_xml_config(self.config_files['core-site.xml'], core_site) and
            self.write_xml_config(self.config_files['hdfs-site.xml'], hdfs_site)
        )

    def update_yarn_config(self, resourcemanager_host: str) -> bool:
        """
        更新YARN配置
        
        Args:
            resourcemanager_host: ResourceManager主机名
            
        Returns:
            bool: 是否成功更新
        """
        yarn_site = {
            'yarn.resourcemanager.hostname': resourcemanager_host,
            'yarn.nodemanager.aux-services': 'mapreduce_shuffle',
            'yarn.nodemanager.resource.memory-mb': '4096',
            'yarn.scheduler.maximum-allocation-mb': '4096',
            'yarn.scheduler.minimum-allocation-mb': '256'
        }
        
        return self.write_xml_config(self.config_files['yarn-site.xml'], yarn_site)

    def update_hive_config(self, metastore_host: str, metastore_port: int = 9083) -> bool:
        """
        更新Hive配置
        
        Args:
            metastore_host: Metastore主机名
            metastore_port: Metastore端口号
            
        Returns:
            bool: 是否成功更新
        """
        hive_site = {
            'hive.metastore.uris': f'thrift://{metastore_host}:{metastore_port}',
            'hive.metastore.warehouse.dir': '/user/hive/warehouse',
            'hive.exec.scratchdir': '/tmp/hive',
            'hive.metastore.schema.verification': 'false'
        }
        
        return self.write_xml_config(self.config_files['hive-site.xml'], hive_site)

    def sync_configs_to_nodes(self, nodes: list, user: str) -> bool:
        """
        同步配置到所有节点
        
        Args:
            nodes: 节点列表
            user: 执行命令的用户
            
        Returns:
            bool: 是否成功同步
        """
        try:
            for node in nodes:
                for config_file in self.config_files.values():
                    cmd = f'scp {config_file} {user}@{node}:{config_file}'
                    os.system(cmd)
            return True
        except Exception as e:
            self.logger.error(f"同步配置文件失败: {e}")
            return False 