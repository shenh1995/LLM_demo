#!/usr/bin/env python3
"""
环境变量设置脚本
帮助用户创建和配置 .env 文件
"""

import os
import shutil
from pathlib import Path

def create_env_file():
    """创建.env文件"""
    env_example = Path("env.example")
    env_file = Path(".env")
    
    if env_file.exists():
        print("⚠️  .env 文件已存在")
        response = input("是否要覆盖现有的 .env 文件? (y/N): ")
        if response.lower() != 'y':
            print("❌ 操作已取消")
            return False
    
    if not env_example.exists():
        print("❌ 错误: 未找到 env.example 文件")
        return False
    
    try:
        # 复制示例文件
        shutil.copy2(env_example, env_file)
        print("✅ .env 文件已创建")
        print("📝 请编辑 .env 文件，填入实际的配置值")
        return True
        
    except Exception as e:
        print(f"❌ 创建 .env 文件失败: {e}")
        return False

def create_directories():
    """创建必要的目录"""
    directories = [
        "logs",
        "uploads",
        "cache"
    ]
    
    print("📁 创建必要的目录...")
    for directory in directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"   ✅ 创建目录: {directory}")
        else:
            print(f"   ℹ️  目录已存在: {directory}")

def main():
    """主函数"""
    print("🔧 环境变量设置工具")
    print("=" * 40)
    
    # 检查是否在backend目录
    if not Path("env.example").exists():
        print("❌ 错误: 请在backend目录下运行此脚本")
        return
    
    # 创建必要的目录
    create_directories()
    print()
    
    # 创建.env文件
    if create_env_file():
        print()
        print("🎉 环境变量设置完成！")
        print()
        print("📋 下一步操作:")
        print("1. 编辑 .env 文件，填入实际的API密钥和配置")
        print("2. 运行 python start_server.py 启动服务器")
        print()
        print("💡 提示:")
        print("- 请确保 .env 文件不要提交到版本控制系统")
        print("- 生产环境中请使用强密码和安全的密钥")
    else:
        print("❌ 环境变量设置失败")

if __name__ == "__main__":
    main() 