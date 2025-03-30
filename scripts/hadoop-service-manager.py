#!/usr/bin/env python3
import os
import sys
import subprocess
from typing import Optional

class HadoopServiceManager:
    def __init__(self):
        self.services = {
            'namenode': {'user': 'hdfs_user', 'keytab': 'nn.service.keytab'},
            'datanode': {'user': 'hdfs_user', 'keytab': 'dn.service.keytab'},
            'resourcemanager': {'user': 'yarn_user', 'keytab': 'rm.service.keytab'},
            'nodemanager': {'user': 'yarn_user', 'keytab': 'nm.service.keytab'}
        }
        
    def start_service(self, service_name: str) -> None:
        """启动指定的Hadoop服务"""
        if service_name not in self.services:
            print(f"错误：未知服务 {service_name}")
            return
            
        service_info = self.services[service_name]
        cmd = [
            './scripts/start-service.sh',
            service_name,
            service_info['user']
        ]
        
        try:
            subprocess.run(cmd, check=True)
            print(f"{service_name} 服务启动成功")
        except subprocess.CalledProcessError as e:
            print(f"启动 {service_name} 失败: {str(e)}")
            
    def stop_service(self, service_name: str) -> None:
        """停止指定的Hadoop服务"""
        if service_name not in self.services:
            print(f"错误：未知服务 {service_name}")
            return
            
        cmd = f"hadoop-daemon.sh stop {service_name}"
        try:
            subprocess.run(cmd.split(), check=True)
            print(f"{service_name} 服务停止成功")
        except subprocess.CalledProcessError as e:
            print(f"停止 {service_name} 失败: {str(e)}")
            
    def start_all(self) -> None:
        """启动所有Hadoop服务"""
        services_order = ['namenode', 'datanode', 'resourcemanager', 'nodemanager']
        for service in services_order:
            self.start_service(service)
            
    def stop_all(self) -> None:
        """停止所有Hadoop服务"""
        services_order = ['nodemanager', 'resourcemanager', 'datanode', 'namenode']
        for service in services_order:
            self.stop_service(service)
            
    def check_status(self) -> None:
        """检查所有服务状态"""
        try:
            subprocess.run(['jps'], check=True)
        except subprocess.CalledProcessError as e:
            print(f"检查状态失败: {str(e)}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 hadoop-service-manager.py <command> [service_name]")
        print("Commands: start, stop, start-all, stop-all, status")
        sys.exit(1)
        
    manager = HadoopServiceManager()
    command = sys.argv[1]
    
    if command == "start" and len(sys.argv) == 3:
        manager.start_service(sys.argv[2])
    elif command == "stop" and len(sys.argv) == 3:
        manager.stop_service(sys.argv[2])
    elif command == "start-all":
        manager.start_all()
    elif command == "stop-all":
        manager.stop_all()
    elif command == "status":
        manager.check_status()
    else:
        print("Invalid command")
        sys.exit(1)

if __name__ == "__main__":
    main() 