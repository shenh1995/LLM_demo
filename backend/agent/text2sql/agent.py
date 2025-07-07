"""
Text2SQL Agent

核心代理类，负责处理聊天消息并调用chat_model获取结果
"""

import asyncio
import json
from typing import Dict, Any, Optional, AsyncGenerator
from models.Factory import ChatModelFactory


class Text2SQLAgent:
    """Text2SQL智能代理"""
    
    def __init__(self, model_name: str = "qianwen", use_azure: bool = False):
        """
        初始化Text2SQL代理
        
        Args:
            model_name: 模型名称
            use_azure: 是否使用Azure OpenAI
        """
        self.model_name = model_name
        self.use_azure = use_azure
        self.chat_model = None
        self._initialize_model()
    
    def _initialize_model(self):
        """初始化聊天模型"""
        print(self.model_name)
        try:
            self.chat_model = ChatModelFactory.get_model(self.model_name, self.use_azure)
            print(f"✅ Text2SQL Agent初始化成功，使用模型: {self.model_name}")
        except Exception as e:
            print(f"❌ 模型初始化失败: {e}")
            raise
    
    async def process_message(self, message: str, role: str = "user") -> str:
        """
        处理用户消息并返回AI回复
        
        Args:
            message: 用户消息
            role: 消息角色
            
        Returns:
            AI回复内容
        """
        if not self.chat_model:
            raise RuntimeError("聊天模型未初始化")
        
        try:
            # 构建系统提示词
            system_prompt = self._build_system_prompt()
            
            # 构建用户消息
            user_message = self._build_user_message(message)
            
            # 调用模型
            response = await self._call_model(system_prompt, user_message)
            
            return response
            
        except Exception as e:
            print(f"❌ 处理消息时发生错误: {e}")
            return f"抱歉，处理您的消息时出现了错误: {str(e)}"
    
    async def process_message_stream(self, message: str, role: str = "user") -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式处理用户消息
        
        Args:
            message: 用户消息
            role: 消息角色
            
        Yields:
            流式响应数据
        """
        if not self.chat_model:
            raise RuntimeError("聊天模型未初始化")
        
        try:
            # 构建系统提示词
            system_prompt = self._build_system_prompt()
            
            # 构建用户消息
            user_message = self._build_user_message(message)
            
            # 流式调用模型
            async for chunk in self._call_model_stream(system_prompt, user_message):
                yield chunk
                
        except Exception as e:
            print(f"❌ 流式处理消息时发生错误: {e}")
            yield {
                "type": "error",
                "content": f"抱歉，处理您的消息时出现了错误: {str(e)}"
            }
    
    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        return """你是一个专业的SQL查询助手。你的任务是将用户的自然语言查询转换为准确的SQL语句。

请遵循以下规则：
1. 只返回SQL语句，不要包含其他解释
2. 使用标准的SQL语法
3. 如果用户的问题不明确，请询问更多细节
4. 确保SQL语句的语法正确
5. 使用适当的表名和字段名

示例：
用户: "查询所有用户信息"
SQL: "SELECT * FROM users;"

用户: "统计每个部门的员工数量"
SQL: "SELECT department, COUNT(*) as employee_count FROM employees GROUP BY department;"
"""
    
    def _build_user_message(self, message: str) -> str:
        """构建用户消息"""
        return f"请将以下自然语言查询转换为SQL语句：\n\n{message}"
    
    async def _call_model(self, system_prompt: str, user_message: str) -> str:
        """调用聊天模型"""
        try:
            # 构建消息列表
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
            
            # 调用模型
            response = await self.chat_model.ainvoke(messages)
            
            return response.content
            
        except Exception as e:
            print(f"❌ 调用模型失败: {e}")
            raise
    
    async def _call_model_stream(self, system_prompt: str, user_message: str) -> AsyncGenerator[Dict[str, Any], None]:
        """流式调用聊天模型"""
        try:
            # 构建消息列表
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
            
            # 流式调用模型
            async for chunk in self.chat_model.astream(messages):
                if hasattr(chunk, 'content') and chunk.content:
                    yield {
                        "type": "content",
                        "content": chunk.content
                    }
            
            # 发送完成信号
            yield {"type": "complete"}
            
        except Exception as e:
            print(f"❌ 流式调用模型失败: {e}")
            yield {
                "type": "error",
                "content": f"模型调用失败: {str(e)}"
            }
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "model_name": self.model_name,
            "use_azure": self.use_azure,
            "is_initialized": self.chat_model is not None
        } 