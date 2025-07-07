"""
Chat Handler

聊天处理器，用于处理API层的聊天请求并调用Text2SQL Agent
"""

import asyncio
import json
from typing import Dict, Any, Optional
from .agent import Text2SQLAgent


class ChatHandler:
    """聊天处理器"""
    
    def __init__(self, model_name: str = "qianwen", use_azure: bool = False):
        """
        初始化聊天处理器
        
        Args:
            model_name: 模型名称
            use_azure: 是否使用Azure OpenAI
        """
        self.agent = Text2SQLAgent(model_name, use_azure)
        self.conversation_history = []
    
    async def handle_chat(self, message: str, role: str = "user") -> Dict[str, Any]:
        """
        处理聊天消息
        
        Args:
            message: 用户消息
            role: 消息角色
            
        Returns:
            处理结果
        """
        try:
            # 记录用户消息
            self.conversation_history.append({
                "role": role,
                "content": message
            })
            
            # 调用agent处理消息
            response = await self.agent.process_message(message, role)
            
            # 记录AI回复
            self.conversation_history.append({
                "role": "assistant",
                "content": response
            })
            
            return {
                "success": True,
                "message": response,
                "received_message": message,
                "conversation_length": len(self.conversation_history)
            }
            
        except Exception as e:
            print(f"❌ 处理聊天消息失败: {e}")
            return {
                "success": False,
                "message": f"处理消息时发生错误: {str(e)}",
                "received_message": message
            }
    
    async def handle_chat_stream(self, message: str, role: str = "user"):
        """
        流式处理聊天消息
        
        Args:
            message: 用户消息
            role: 消息角色
            
        Yields:
            流式响应数据
        """
        try:
            # 记录用户消息
            self.conversation_history.append({
                "role": role,
                "content": message
            })
            
            # 流式调用agent处理消息
            full_response = ""
            async for chunk in self.agent.process_message_stream(message, role):
                if chunk["type"] == "content":
                    full_response += chunk["content"]
                    # 发送字符级别的流式数据
                    yield f"data: {json.dumps({'type': 'char', 'content': chunk['content']})}\n\n"
                elif chunk["type"] == "complete":
                    # 记录AI回复
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": full_response
                    })
                    # 发送完成信号
                    yield f"data: {json.dumps({'type': 'complete', 'message': full_response})}\n\n"
                elif chunk["type"] == "error":
                    yield f"data: {json.dumps({'type': 'error', 'content': chunk['content']})}\n\n"
                    
        except Exception as e:
            print(f"❌ 流式处理聊天消息失败: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': f'处理消息时发生错误: {str(e)}'})}\n\n"
    
    def get_conversation_history(self) -> list:
        """获取对话历史"""
        return self.conversation_history.copy()
    
    def clear_conversation_history(self):
        """清空对话历史"""
        self.conversation_history.clear()
    
    def get_agent_info(self) -> Dict[str, Any]:
        """获取agent信息"""
        return self.agent.get_model_info()
    
    def update_model(self, model_name: str, use_azure: bool = False):
        """更新模型"""
        try:
            self.agent = Text2SQLAgent(model_name, use_azure)
            return True
        except Exception as e:
            print(f"❌ 更新模型失败: {e}")
            return False 