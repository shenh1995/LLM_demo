#!/usr/bin/env python3
"""
Text2SQL Agent 测试脚本

用于测试Text2SQL Agent的功能
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agent.text2sql import Text2SQLAgent, ChatHandler


async def test_agent():
    """测试Text2SQL Agent"""
    print("🧪 开始测试Text2SQL Agent...")
    print("=" * 50)
    
    try:
        # 创建agent实例
        agent = Text2SQLAgent(model_name="qianwen", use_azure=False)
        print("✅ Agent创建成功")
        
        # 测试模型信息
        model_info = agent.get_model_info()
        print(f"📊 模型信息: {model_info}")
        
        # 测试消息处理
        test_messages = [
            "查询所有用户信息",
            "统计每个部门的员工数量",
            "查找年龄大于30岁的员工",
            "按工资降序排列员工列表"
        ]
        
        for i, message in enumerate(test_messages, 1):
            print(f"\n🔍 测试 {i}: {message}")
            try:
                response = await agent.process_message_stream(message)
                print(f"✅ 响应: {response}")
            except Exception as e:
                print(f"❌ 错误: {e}")
        
        print("\n" + "=" * 50)
        print("✅ Agent测试完成")
        
    except Exception as e:
        print(f"❌ Agent测试失败: {e}")


async def test_chat_handler():
    """测试ChatHandler"""
    print("\n🧪 开始测试ChatHandler...")
    print("=" * 50)
    
    try:
        # 创建chat handler实例
        handler = ChatHandler(model_name="qianwen", use_azure=False)
        print("✅ ChatHandler创建成功")
        
        # 测试聊天处理
        test_message = "查询所有用户信息"
        print(f"🔍 测试消息: {test_message}")
        
        result = await handler.handle_chat(test_message)
        print(f"✅ 处理结果: {result}")
        
        # 测试对话历史
        history = handler.get_conversation_history()
        print(f"📝 对话历史: {history}")
        
        # 测试流式处理
        print("\n🌊 测试流式处理...")
        async for chunk in handler.handle_chat_stream("统计员工数量"):
            print(f"📦 流式数据: {chunk}")
        
        print("\n" + "=" * 50)
        print("✅ ChatHandler测试完成")
        
    except Exception as e:
        print(f"❌ ChatHandler测试失败: {e}")


async def test_stream_processing():
    """测试流式处理"""
    print("\n🧪 开始测试流式处理...")
    print("=" * 50)
    
    try:
        handler = ChatHandler(model_name="qianwen", use_azure=False)
        
        test_message = "查询所有部门信息"
        print(f"🔍 测试消息: {test_message}")
        
        print("🌊 流式响应:")
        async for chunk in handler.handle_chat_stream(test_message):
            print(f"  {chunk.strip()}")
        
        print("\n" + "=" * 50)
        print("✅ 流式处理测试完成")
        
    except Exception as e:
        print(f"❌ 流式处理测试失败: {e}")


async def main():
    """主测试函数"""
    print("🚀 Text2SQL Agent 完整测试")
    print("=" * 60)
    
    # 测试Agent
    await test_agent()
    
    # 测试ChatHandler
    await test_chat_handler()
    
    # 测试流式处理
    await test_stream_processing()
    
    print("\n" + "=" * 60)
    print("🎉 所有测试完成！")


if __name__ == "__main__":
    asyncio.run(main()) 