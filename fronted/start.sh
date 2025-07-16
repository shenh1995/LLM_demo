#!/bin/bash

# 前端启动脚本
# 用于启动Vue.js开发服务器

echo "🎯 前端启动脚本"
echo "=" * 50

# 检查是否在正确的目录
if [ ! -f "vue-project/package.json" ]; then
    echo "❌ 错误: 请在fronted目录下运行此脚本"
    echo "   当前目录: $(pwd)"
    exit 1
fi

# 进入Vue项目目录
cd vue-project

echo "📁 进入Vue项目目录: $(pwd)"

# 检查Node.js是否安装
if ! command -v node &> /dev/null; then
    echo "❌ 错误: Node.js未安装"
    echo "   请先安装Node.js: https://nodejs.org/"
    exit 1
fi

echo "✅ Node.js版本: $(node --version)"

# 检查npm是否安装
if ! command -v npm &> /dev/null; then
    echo "❌ 错误: npm未安装"
    echo "   请先安装npm"
    exit 1
fi

echo "✅ npm版本: $(npm --version)"

# 检查是否已安装依赖
if [ ! -d "node_modules" ]; then
    echo "📦 正在安装项目依赖..."
    npm install
    if [ $? -ne 0 ]; then
        echo "❌ 依赖安装失败"
        exit 1
    fi
    echo "✅ 依赖安装完成"
else
    echo "✅ 依赖已安装"
fi

# 检查是否有新的依赖需要安装
echo "🔍 检查依赖更新..."
npm outdated --depth=0 > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "⚠️  发现过时的依赖，建议运行 'npm update' 更新"
fi

echo ""
echo "🌐 启动开发服务器..."
echo "   服务器将在 http://localhost:5173 启动"
echo "   按 Ctrl+C 停止服务器"
echo "-" * 50

# 启动开发服务器
npm run dev 