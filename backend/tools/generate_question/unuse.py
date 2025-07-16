import os
import sys
import json
from typing import Dict, List, Any

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, backend_dir)

from database.connection_manager import get_db_manager, DatabaseConnectionManager

def create_database_configs() -> Dict[str, Dict[str, Any]]:
    """创建14个数据库的配置"""
    databases = [
        "astockbasicinfodb", "constantdb", "creditdb", "astockeventsdb", 
        "hkstockdb", "astockfinancedb", "indexdb", "astockindustrydb", 
        "institutiondb", "astockmarketquotesdb", "publicfunddb", 
        "astockoperationsdb", "usstockdb", "astockshareholderdb"
    ]
    
    configs = {}
    for db_name in databases:
        configs[db_name] = {
            "type": "mysql",
            "host": "120.76.202.209",
            "port": 3306,
            "user": "root",
            "password": "123456",
            "database": db_name,
            "pool_size": 3,
            "max_overflow": 5
        }
    
    return configs

def execute_sql_query(db_manager: DatabaseConnectionManager, db_name: str, sql: str) -> str:
    """执行SQL查询并返回结果字符串"""
    try:
        result = db_manager.execute_query(db_name, sql)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        print(f"❌ 执行查询失败 {db_name}: {sql}")
        print(f"错误: {e}")
        return "[]"

def __main__():
    """主函数"""
    print("🚀 开始初始化数据库连接管理器...")
    
    # 创建数据库配置
    configs = create_database_configs()
    print(f"📊 配置了 {len(configs)} 个数据库")
    
    # 获取数据库连接管理器
    db_manager = get_db_manager()
    
    # 添加所有数据库连接
    print("🔗 添加数据库连接...")
    for name, config in configs.items():
        success = db_manager.add_connection(name, config)
        if success:
            print(f"✅ 添加数据库连接: {name}")
        else:
            print(f"❌ 添加数据库连接失败: {name}")
    
    # 连接所有数据库
    print("\n🔗 连接所有数据库...")
    if db_manager.connect_all():
        print("✅ 所有数据库连接成功")
    else:
        print("❌ 部分数据库连接失败")
        return
    
    # 获取连接状态
    print("\n📊 连接状态:")
    status = db_manager.get_connection_status()
    connected_dbs = []
    for db_name, is_connected in status.items():
        status_icon = "✅" if is_connected else "❌"
        print(f"{status_icon} {db_name}: {'已连接' if is_connected else '未连接'}")
        if is_connected:
            connected_dbs.append(db_name)
    
    print(f"\n📈 成功连接 {len(connected_dbs)}/{len(configs)} 个数据库")
    
    # 获取数据库连接映射
    connection_map = db_manager.get_connection_map()
    print(f"\n🗂️  数据库连接映射:")
    for db_name, connection in connection_map.items():
        print(f"📁 {db_name}: {connection.config['database']}")
    
    # 原有的unuse逻辑
    CACHE_DIR = '../cache'
    schema = json.load(open(CACHE_DIR + '/schema.json', 'r', encoding='utf-8'))
    unuse_columns = []
    
    if not os.path.exists(CACHE_DIR + '/unuse_columns.json'):
        print("\n🔍 开始检查无用字段...")
        for t in schema:
            print(f"check table: {t['table_name']}")
            
            # 从表名中提取数据库名
            table_name = t['table_name']
            if '.' in table_name:
                db_name = table_name.split('.')[0]
                table_short_name = table_name.split('.')[1]
            else:
                # 如果没有数据库前缀，尝试从表名推断
                db_name = None
                table_short_name = table_name
                
                # 根据表名推断数据库
                if 'lc_' in table_short_name or 'secumain' in table_short_name:
                    if 'hk_' in table_short_name:
                        db_name = 'hkstockdb'
                    elif 'us_' in table_short_name:
                        db_name = 'usstockdb'
                    else:
                        db_name = 'constantdb'
                elif 'qt_' in table_short_name:
                    db_name = 'astockmarketquotesdb'
                elif 'cs_' in table_short_name:
                    db_name = 'csdb'
                else:
                    # 默认使用第一个连接的数据库
                    db_name = list(connection_map.keys())[0] if connection_map else None
            
            if db_name and db_name in connection_map:
                for c in t['columns']:
                    # 找出值全是null的字段
                    sql = f"SELECT DISTINCT {c['name']} FROM {table_short_name} WHERE {c['name']} IS NOT NULL LIMIT 1"
                    res = execute_sql_query(db_manager, db_name, sql)
                    if res == "[]":
                        col_mark = f"{t['table_name']}|{c['name']}"
                        unuse_columns.append(col_mark)
                        print(f"字段[{col_mark}]，值全是null")
            else:
                print(f"⚠️  无法确定数据库: {table_name}")
        
        print(f"\n📊 找到 {len(unuse_columns)} 个无用字段")
        
        # 保存无用字段列表
        with open(CACHE_DIR + '/unuse_columns.json', 'w', encoding='utf-8') as json_file:
            json.dump(unuse_columns, json_file, ensure_ascii=False, indent=2)
        
        # 创建截断的schema
        truncated_schema = []
        for t in schema:
            t_copy = t.copy()
            t_copy['columns'] = [c for c in t['columns'] if f"{t['table_name']}|{c['name']}" not in unuse_columns]
            t_copy['all_cols'] = ",".join([f"{c['desc']}({c['name']})" for c in t_copy['columns']])
            truncated_schema.append(t_copy)
        
        # 保存更新后的schema
        with open(CACHE_DIR + '/schema.json', 'w', encoding='utf-8') as json_file:
            json.dump(truncated_schema, json_file, ensure_ascii=False, indent=2)
        
        print("✅ 无用字段检查和清理完成")
    else:
        print("✅ 无用字段文件已存在，跳过检查")
    
    # 关闭所有数据库连接
    print("\n🔒 关闭所有数据库连接...")
    db_manager.close_all()
    print("✅ 所有数据库连接已关闭")

if __name__ == "__main__":
    __main__()