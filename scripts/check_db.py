"""数据库检查脚本"""

import os
import sys
import sqlite3

def check_database():
    """检查数据库内容"""
    # 连接数据库
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'instance', 'test.db')
    print(f"数据库路径: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取所有表名
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print("\n=== 数据库表 ===")
        for table in tables:
            table_name = table[0]
            print(f"\n表名: {table_name}")
            
            # 获取表结构
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            print("列信息:")
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")
            
            # 获取表中的记录数
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            count = cursor.fetchone()[0]
            print(f"记录数: {count}")
            
            # 如果有记录，显示前5条
            if count > 0:
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 5;")
                rows = cursor.fetchall()
                print("前5条记录:")
                for row in rows:
                    print(f"  {row}")
            
            print("-" * 50)
        
    except sqlite3.Error as e:
        print(f"数据库错误: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    check_database() 