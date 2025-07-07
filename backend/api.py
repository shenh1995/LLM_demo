from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio
import json
from agent.text2sql import ChatHandler

app = FastAPI()

# 允许跨域，方便前端本地开发调试
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化聊天处理器
chat_handler = ChatHandler(model_name="qianwen", use_azure=False)

class LoginRequest(BaseModel):
    username: str
    password: str

class ChatMessage(BaseModel):
    message: str
    role: str = "user"

@app.post("/api/login")
async def login(data: LoginRequest):
    # 这里只做演示，直接返回成功
    return {"success": True, "message": "登录成功"}

@app.post("/api/chat")
async def chat(data: ChatMessage):
    # 打印接收到的消息
    print(f"收到用户消息: {data.message}")
    print(f"消息角色: {data.role}")
    
    # 使用Text2SQL Agent处理消息
    result = await chat_handler.handle_chat(data.message, data.role)
    
    return result

@app.post("/api/chat/stream")
async def chat_stream(data: ChatMessage):
    # 打印接收到的消息
    print(f"收到用户消息: {data.message}")
    print(f"消息角色: {data.role}")
    
    async def generate_stream():
        # 使用Text2SQL Agent流式处理消息
        async for chunk in chat_handler.handle_chat_stream(data.message, data.role):
            yield chunk
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        }
    )

@app.get("/api/agent/info")
async def get_agent_info():
    """获取agent信息"""
    return chat_handler.get_agent_info()

@app.get("/api/conversation/history")
async def get_conversation_history():
    """获取对话历史"""
    return {
        "success": True,
        "history": chat_handler.get_conversation_history()
    }

@app.delete("/api/conversation/clear")
async def clear_conversation_history():
    """清空对话历史"""
    chat_handler.clear_conversation_history()
    return {"success": True, "message": "对话历史已清空"}
