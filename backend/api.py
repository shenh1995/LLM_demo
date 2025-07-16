from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio
import json
from process import process_single_question
import copy
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

app = FastAPI()

# 允许跨域，方便前端本地开发调试
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 全局变量存储对话历史
conversation_history = {
    "team": []
}

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
    
    # 将消息封装成process_single_question所需的格式
    question_item = {
        "id": f"chat_{len(conversation_history['team']) + 1}",
        "question": data.message,
        "role": data.role
    }
    
    # 添加到对话历史
    conversation_history["team"].append(question_item)
    
    # 调用process_single_question处理问题
    q_idx = len(conversation_history["team"]) - 1
    process_single_question(conversation_history, q_idx)
    
    # 获取处理结果
    result = conversation_history["team"][q_idx]
    
    return {
        "success": True,
        "answer": result.get("answer", ""),
        "question": result.get("question", ""),
        "use_time": result.get("use_time", ""),
        "usage_tokens": result.get("usage_tokens", {})
    }

@app.post("/api/chat/stream")
async def chat_stream(data: ChatMessage):
    # 打印接收到的消息
    print(f"收到用户消息: {data.message}")
    print(f"消息角色: {data.role}")
    
    async def generate_stream():
        try:
            # 将消息封装成process_single_question所需的格式
            question_item = {
                "id": f"chat_{len(conversation_history['team']) + 1}",
                "question": data.message,
                "role": data.role
            }
            
            # 添加到对话历史
            conversation_history["team"].append(question_item)
            q_idx = len(conversation_history["team"]) - 1
            
            # 立即发送开始处理的消息
            yield f"data: {json.dumps({'type': 'status', 'content': '开始处理您的问题...'})}\n\n"
            
            # 创建一个流式处理函数
            async def process_with_streaming():
                try:
                    # 发送状态更新
                    yield f"data: {json.dumps({'type': 'status', 'content': '正在分析问题...'})}\n\n"
                    
                    # 调用process_single_question处理问题
                    process_single_question(conversation_history, q_idx)
                    
                    # 获取处理结果
                    result = conversation_history["team"][q_idx]
                    logger.info("\n>>>>> result:\n%s", result)
                    
                    # 发送完成状态
                    yield f"data: {json.dumps({'type': 'status', 'content': '处理完成'})}\n\n"
                    
                    # 返回最终结果
                    yield f"data: {json.dumps({'type': 'complete', 'content': result.get('answer', '')})}\n\n"
                    
                except Exception as e:
                    logger.error(f"处理过程中发生错误: {e}")
                    yield f"data: {json.dumps({'type': 'error', 'content': f'处理过程中发生错误: {str(e)}'})}\n\n"
            
            # 执行流式处理
            async for chunk in process_with_streaming():
                yield chunk
                
        except Exception as e:
            logger.error(f"流式处理过程中发生错误: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': f'流式处理过程中发生错误: {str(e)}'})}\n\n"
    
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
        "history": conversation_history["team"]
    }

@app.delete("/api/conversation/clear")
async def clear_conversation_history():
    """清空对话历史"""
    conversation_history["team"] = []
    return {"success": True, "message": "对话历史已清空"}
