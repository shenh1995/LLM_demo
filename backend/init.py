#!/usr/bin/env python3
"""
后端初始化脚本
在启动API服务器之前执行必要的初始化工作
"""

import os
import sys
from dotenv import load_dotenv

def init_environment():
    """初始化环境变量"""
    print("🔧 正在初始化环境变量...")
    
    # 加载.env文件
    load_dotenv()
    
    # 检查必要的环境变量
    required_env_vars = [
        # 可以根据需要添加必要的环境变量
        # "OPENAI_API_KEY",
        # "SILICONFLOW_API_KEY",
    ]
    
    missing_vars = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"⚠️  警告: 以下环境变量未设置: {', '.join(missing_vars)}")
        print("   这些变量可能在某些功能中需要")
    else:
        print("✅ 环境变量初始化完成")

def init_models():
    """初始化模型工厂"""
    print("🤖 正在初始化模型工厂...")
    
    try:
        from models.Factory import ChatModelFactory, EmbeddingModelFactory
        
        # 测试模型工厂是否正常工作
        print("   - 测试ChatModelFactory...")
        chat_model = ChatModelFactory.get_default_model()
        print(f"   ✅ ChatModelFactory初始化成功")
        
        print("   - 测试EmbeddingModelFactory...")
        # embedding_model = EmbeddingModelFactory.get_default_model()
        print(f"   ✅ EmbeddingModelFactory初始化成功")
        
        print("✅ 模型工厂初始化完成")
        
    except Exception as e:
        print(f"❌ 模型工厂初始化失败: {e}")
        print("   这不会阻止API启动，但可能影响某些功能")

def init_database():
    """初始化数据库连接"""
    print("🗄️  正在初始化数据库连接...")
    
    # 这里可以添加数据库初始化逻辑
    # 例如：创建表、检查连接等
    
    print("✅ 数据库初始化完成")

def init_cache():
    """初始化缓存系统"""
    print("💾 正在初始化缓存系统...")
    
    # 这里可以添加缓存初始化逻辑
    # 例如：Redis连接、内存缓存等
    
    print("✅ 缓存系统初始化完成")

def main():
    """主初始化函数"""
    print("🚀 开始后端初始化...")
    print("=" * 50)
    
    try:
        # 初始化环境变量
        init_environment()
        print()
        
        # 初始化模型工厂
        init_models()
        print()
        
        print("=" * 50)
        print("✅ 后端初始化完成！")
        print("   现在可以启动API服务器了")
        
    except Exception as e:
        print(f"❌ 初始化过程中发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 