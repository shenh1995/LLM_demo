#!/bin/bash

# 后端启动脚本
# 使用方法: ./start.sh

echo "🎯 后端启动脚本"
echo "=================="

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到python3，请确保已安装Python 3"
    exit 1
fi

# 检查是否在backend目录
if [ ! -f "init.py" ] || [ ! -f "api.py" ]; then
    echo "❌ 错误: 请在backend目录下运行此脚本"
    exit 1
fi

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "⚠️  警告: 未找到虚拟环境，建议创建虚拟环境"
    echo "   运行: python3 -m venv venv"
    echo "   然后: source venv/bin/activate"
fi

# 执行Python启动脚本
echo "🚀 启动后端服务..."
python3 start_server.py 