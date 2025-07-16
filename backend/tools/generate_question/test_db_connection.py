#!/usr/bin/env python3
"""
数据库连接测试脚本
用于测试14个数据库的连接是否正常
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

def test_database_connections():
    """测试数据库连接"""
    print("🚀 开始测试数据库连接...")
    
    # 创建数据库配置
    configs = create_database_configs()
    print(f"📊 配置了 {len(configs)} 个数据库")
    
    # 获取数据库连接管理器
    db_manager = get_db_manager()
    
    # 添加所有数据库连接
    print("\n🔗 添加数据库连接...")
    success_count = 0
    for name, config in configs.items():
        success = db_manager.add_connection(name, config)
        if success:
            print(f"✅ 添加数据库连接: {name}")
            success_count += 1
        else:
            print(f"❌ 添加数据库连接失败: {name}")
    
    print(f"\n📈 成功添加 {success_count}/{len(configs)} 个数据库连接")
    
    # 连接所有数据库
    print("\n🔗 连接所有数据库...")
    if db_manager.connect_all():
        print("✅ 所有数据库连接成功")
    else:
        print("❌ 部分数据库连接失败")
    
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
    
    # 测试查询
    print("\n🔍 测试数据库查询...")
    for db_name in connected_dbs:
        try:
            # 测试简单查询
            result = db_manager.execute_query(db_name, "SELECT 1 as test")
            if result:
                print(f"✅ {db_name}: 查询测试成功")
            else:
                print(f"⚠️  {db_name}: 查询返回空结果")
        except Exception as e:
            print(f"❌ {db_name}: 查询测试失败 - {e}")
    
    # 获取数据库连接映射
    connection_map = db_manager.get_connection_map()
    print(f"\n🗂️  数据库连接映射:")
    for db_name, connection in connection_map.items():
        print(f"📁 {db_name}: {connection.config['database']}")
    
    # 关闭所有数据库连接
    print("\n🔒 关闭所有数据库连接...")
    db_manager.close_all()
    print("✅ 所有数据库连接已关闭")
    
    return len(connected_dbs) == len(configs)

if __name__ == "__main__":
    success = test_database_connections()
    if success:
        print("\n🎉 所有数据库连接测试成功！")
    else:
        print("\n⚠️  部分数据库连接测试失败，请检查配置和网络连接。") 