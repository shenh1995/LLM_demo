#!/usr/bin/env python3
"""
unable.py - 找出可能存在NULL值的字段
与unuse.py类似，但检查所有字段是否包含NULL值，而不仅仅是全为NULL的字段
"""

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
    # databases = ["astockbasicinfodb"]
    
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

def check_nullable_columns(db_manager: DatabaseConnectionManager, schema: List[Dict[str, Any]]) -> List[str]:
    """检查可能存在NULL值的字段"""
    nullable_fields = []
    nullable_columns = {}
    
    # 加载unuse_columns文件（如果存在）
    unuse_columns = []
    try:
        if os.path.exists('../cache/unuse_columns.json'):
            with open('../cache/unuse_columns.json', 'r', encoding='utf-8') as f:
                unuse_columns = json.load(f)
            print(f"📋 加载了 {len(unuse_columns)} 个已知全为NULL的字段")
    except Exception as e:
        print(f"⚠️  加载unuse_columns.json失败: {e}")
    
    print("\n🔍 开始检查可能存在NULL值的字段...")
    
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
                connection_map = db_manager.get_connection_map()
                db_name = list(connection_map.keys())[0] if connection_map else None
        
        if db_name and db_name in db_manager.get_connection_map():
            for c in t['columns']:
                # 找出包含NULL值的字段(但不是全为NULL)
                col_mark = f"{t['table_name']}|{c['name']}"
                if col_mark in unuse_columns:
                    continue  # 跳过已知全为NULL的字段
                
                # 检查字段是否包含NULL值
                sql = f"SELECT COUNT(*) as total, COUNT({c['name']}) as not_null FROM {table_short_name} LIMIT 1"
                res = execute_sql_query(db_manager, db_name, sql)
                
                try:
                    result = json.loads(res)
                    if result and len(result) > 0:
                        total = result[0]['total']
                        not_null = result[0]['not_null']
                        null_percent = (total - not_null) / total * 100 if total > 0 else 0
                        
                        if total > not_null:  # 包含NULL值
                            nullable_columns[col_mark] = {
                                'null_percent': round(null_percent, 2),
                                'null_count': total - not_null,
                                'total': total
                            }
                            nullable_fields.append(col_mark)
                            print(f"字段[{col_mark}]，NULL值占比: {null_percent:.2f}%")
                except (json.JSONDecodeError, KeyError, IndexError):
                    # 如果解析失败，认为字段可能包含NULL值
                    nullable_fields.append(col_mark)
                    print(f"字段[{col_mark}]，解析失败，可能存在NULL值")
        else:
            print(f"⚠️  无法确定数据库: {table_name}")
    
    # 保存nullable_columns到文件
    try:
        with open('../cache/nullable_columns.json', 'w', encoding='utf-8') as json_file:
            json.dump(nullable_columns, json_file, ensure_ascii=False, indent=2)
        print(f"✅ 保存了 {len(nullable_columns)} 个包含NULL值的字段到 nullable_columns.json")
    except Exception as e:
        print(f"❌ 保存nullable_columns.json失败: {e}")
    
    print(f"\n📊 找到 {len(nullable_fields)} 个可能包含NULL值的字段")
    
    # 创建字段统计信息
    field_stats = {}
    for field in nullable_fields:
        table_name, column_name = field.split('|')
        if table_name not in field_stats:
            field_stats[table_name] = []
        field_stats[table_name].append(column_name)
    
    # 保存统计信息
    try:
        with open('../cache/nullable_fields_stats.json', 'w', encoding='utf-8') as json_file:
            json.dump(field_stats, json_file, ensure_ascii=False, indent=2)
        print("✅ 字段统计信息已保存到 nullable_fields_stats.json")
    except Exception as e:
        print(f"❌ 保存nullable_fields_stats.json失败: {e}")
    
    # 打印统计信息
    print(f"\n📈 字段统计信息:")
    for table_name, columns in field_stats.items():
        print(f"📋 {table_name}: {len(columns)} 个可能包含NULL值的字段")
        if len(columns) <= 10:  # 只显示前10个字段
            for col in columns:
                print(f"   - {col}")
        else:
            for col in columns[:5]:
                print(f"   - {col}")
            print(f"   ... 还有 {len(columns) - 5} 个字段")
    
    return nullable_fields

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
    
    # 加载schema
    CACHE_DIR = '../cache'
    schema = json.load(open(CACHE_DIR + '/schema.json', 'r', encoding='utf-8'))
    
    check_nullable_columns(db_manager, schema)
    # 关闭所有数据库连接
    print("\n🔒 关闭所有数据库连接...")
    db_manager.close_all()
    print("✅ 所有数据库连接已关闭")

if __name__ == "__main__":
    __main__()