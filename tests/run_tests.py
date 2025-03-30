"""测试运行器"""

import unittest
import sys
import os
from typing import List

def discover_tests() -> List[str]:
    """发现测试文件
    
    Returns:
        List[str]: 测试文件列表
    """
    test_files = []
    for file in os.listdir(os.path.dirname(__file__)):
        if file.startswith('test_') and file.endswith('.py') and file != 'test_config.py' and file != 'test_utils.py':
            test_files.append(file[:-3])  # 移除.py后缀
    return test_files

def run_tests():
    """运行所有测试"""
    # 获取测试文件列表
    test_files = discover_tests()
    
    # 创建测试加载器
    loader = unittest.TestLoader()
    
    # 创建测试套件
    suite = unittest.TestSuite()
    
    # 添加测试用例
    for test_file in test_files:
        try:
            # 动态导入测试模块
            module = __import__(test_file)
            # 添加测试用例到套件
            suite.addTests(loader.loadTestsFromModule(module))
        except ImportError as e:
            print(f"警告: 无法导入测试文件 {test_file}: {str(e)}")
    
    # 创建测试运行器
    runner = unittest.TextTestRunner(verbosity=2)
    
    # 运行测试
    result = runner.run(suite)
    
    # 返回测试结果
    return result.wasSuccessful()

if __name__ == '__main__':
    # 添加当前目录到Python路径
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    
    # 运行测试
    success = run_tests()
    
    # 设置退出码
    sys.exit(0 if success else 1) 