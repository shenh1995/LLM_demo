#!/usr/bin/env python3
"""
Text2SQL Agent 集成测试脚本

测试API和Agent的集成功能
"""

import asyncio
import json
from agent.text2sql import ChatHandler


async def test_integration():
    """测试集成功能"""
    print("🧪 Text2SQL Agent 集成测试")
    print("=" * 50)
    
    try:
        # 创建chat handler
        handler = ChatHandler(model_name="qianwen", use_azure=False)
        print("✅ ChatHandler创建成功")
        
        # 测试基本聊天功能
        test_messages = [
            "查询所有用户信息",
            "统计每个部门的员工数量",
            "查找年龄大于30岁的员工"
        ]
        
        for i, message in enumerate(test_messages, 1):
            print(f"\n🔍 测试 {i}: {message}")
            
            # 测试非流式处理
            result = await handler.handle_chat(message)
            print(f"✅ 非流式响应: {result['message']}")
            
            # 测试流式处理
            print("🌊 流式响应:")
            async for chunk in handler.handle_chat_stream(message):
                print(f"  {chunk.strip()}")
        
        # 测试对话历史
        history = handler.get_conversation_history()
        print(f"\n📝 对话历史长度: {len(history)}")
        
        # 测试agent信息
        agent_info = handler.get_agent_info()
        print(f"🤖 Agent信息: {agent_info}")
        
        print("\n" + "=" * 50)
        print("✅ 集成测试完成")
        
    except Exception as e:
        print(f"❌ 集成测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_integration()) 