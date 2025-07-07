#!/usr/bin/env python3
"""
后端启动脚本
先执行初始化，然后启动API服务器
"""

import subprocess
import sys
import os

def run_init():
    """运行初始化脚本"""
    print("🚀 开始执行初始化...")
    
    try:
        # 运行初始化脚本
        result = subprocess.run([sys.executable, "init.py"], 
                              capture_output=True, 
                              text=True, 
                              cwd=os.path.dirname(os.path.abspath(__file__)))
        
        # 打印初始化输出
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("⚠️  初始化警告:", result.stderr)
        
        if result.returncode != 0:
            print(f"❌ 初始化失败，退出码: {result.returncode}")
            return False
            
        print("✅ 初始化完成")
        return True
        
    except Exception as e:
        print(f"❌ 执行初始化时发生错误: {e}")
        return False

def start_api_server():
    """启动API服务器"""
    print("\n🌐 启动API服务器...")
    print("   服务器将在 http://localhost:8000 启动")
    print("   按 Ctrl+C 停止服务器")
    print("-" * 50)
    
    try:
        # 启动uvicorn服务器
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "api:app", 
            "--reload", 
            "--host", "0.0.0.0", 
            "--port", "8000"
        ], cwd=os.path.dirname(os.path.abspath(__file__)))
        
    except KeyboardInterrupt:
        print("\n👋 服务器已停止")
    except Exception as e:
        print(f"❌ 启动服务器时发生错误: {e}")

def main():
    """主函数"""
    print("🎯 后端启动脚本")
    print("=" * 50)
    
    # 检查是否在正确的目录
    if not os.path.exists("init.py") or not os.path.exists("api.py"):
        print("❌ 错误: 请在backend目录下运行此脚本")
        sys.exit(1)
    
    # 执行初始化
    if not run_init():
        print("❌ 初始化失败，无法启动服务器")
        sys.exit(1)
    
    # 启动API服务器
    start_api_server()

if __name__ == "__main__":
    main() 