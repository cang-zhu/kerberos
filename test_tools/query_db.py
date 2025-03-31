import sqlite3
import sys

def query_users():
    try:
        # 使用上下文管理器确保连接正确关闭
        with sqlite3.connect("app.db") as conn:
            cursor = conn.cursor()
            
            # 查询表结构
            cursor.execute("SELECT * FROM users")
            print("用户信息表结构:")
            print([description[0] for description in cursor.description])
            
            # 查询数据
            rows = cursor.fetchall()
            print("\n用户数据:")
            for row in rows:
                print(row)
                
    except sqlite3.Error as e:
        print(f"数据库错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    query_users()
