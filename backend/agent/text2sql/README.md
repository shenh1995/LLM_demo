# Text2SQL Agent

Text2SQL Agent是一个智能代理，能够将自然语言查询转换为SQL语句。它基于大语言模型，提供流式和非流式的查询处理能力。

## 功能特性

- 🤖 **智能转换**: 将自然语言转换为准确的SQL语句
- 🌊 **流式处理**: 支持实时流式响应
- 📝 **对话历史**: 维护完整的对话上下文
- 🔧 **模型灵活**: 支持多种大语言模型
- 🛡️ **错误处理**: 完善的错误处理和恢复机制

## 快速开始

### 1. 基本使用

```python
from agent.text2sql import Text2SQLAgent

# 创建agent实例
agent = Text2SQLAgent(model_name="qianwen")

# 处理消息
response = await agent.process_message("查询所有用户信息")
print(response)
# 输出: SELECT * FROM users;
```

### 2. 流式处理

```python
from agent.text2sql import ChatHandler

# 创建chat handler
handler = ChatHandler(model_name="qianwen")

# 流式处理
async for chunk in handler.handle_chat_stream("统计员工数量"):
    print(chunk)
```

### 3. API集成

```python
# 在FastAPI中使用
from agent.text2sql import ChatHandler

chat_handler = ChatHandler()

@app.post("/api/chat")
async def chat(data: ChatMessage):
    result = await chat_handler.handle_chat(data.message, data.role)
    return result
```

## API接口

### 聊天接口

- **POST** `/api/chat`
  - 请求体: `{"message": "查询所有用户", "role": "user"}`
  - 返回: `{"success": true, "message": "SELECT * FROM users;", ...}`

### 流式聊天接口

- **POST** `/api/chat/stream`
  - 请求体: `{"message": "查询所有用户", "role": "user"}`
  - 返回: Server-Sent Events流式数据

### 管理接口

- **GET** `/api/agent/info` - 获取agent信息
- **GET** `/api/conversation/history` - 获取对话历史
- **DELETE** `/api/conversation/clear` - 清空对话历史

## 支持的模型

- **OpenAI**: qianwen, gpt-4等
- **Azure OpenAI**: 通过Azure部署的OpenAI模型
- **DeepSeek**: 通过SiliconFlow平台调用
- **Qianwen**: 阿里云通义千问

## 配置说明

### 环境变量

确保在 `.env` 文件中配置了相应的API密钥：

```env
# OpenAI
OPENAI_API_KEY=your_openai_api_key

# Azure OpenAI
AZURE_OPENAI_API_KEY=your_azure_key
AZURE_OPENAI_ENDPOINT=your_azure_endpoint

# SiliconFlow
SILICONFLOW_API_KEY=your_siliconflow_key
```

### 模型配置

```python
# 使用OpenAI
agent = Text2SQLAgent(model_name="qianwen", use_azure=False)

# 使用Azure OpenAI
agent = Text2SQLAgent(model_name="gpt-35-turbo", use_azure=True)

# 使用DeepSeek
agent = Text2SQLAgent(model_name="deepseek", use_azure=False)
```

## 测试

运行测试脚本验证功能：

```bash
cd backend/agent/text2sql
python test_agent.py
```

## 示例查询

### 基本查询
- "查询所有用户信息" → `SELECT * FROM users;`
- "查找年龄大于30岁的员工" → `SELECT * FROM employees WHERE age > 30;`

### 聚合查询
- "统计每个部门的员工数量" → `SELECT department, COUNT(*) as count FROM employees GROUP BY department;`
- "计算平均工资" → `SELECT AVG(salary) as avg_salary FROM employees;`

### 排序查询
- "按工资降序排列员工列表" → `SELECT * FROM employees ORDER BY salary DESC;`
- "按姓名升序排列用户" → `SELECT * FROM users ORDER BY name ASC;`

### 复杂查询
- "查找工资最高的前10名员工" → `SELECT * FROM employees ORDER BY salary DESC LIMIT 10;`
- "统计每个部门的平均工资" → `SELECT department, AVG(salary) as avg_salary FROM employees GROUP BY department;`

## 错误处理

Agent包含完善的错误处理机制：

1. **模型初始化失败**: 自动重试并报告错误
2. **API调用失败**: 返回友好的错误信息
3. **网络问题**: 自动重试机制
4. **输入验证**: 验证用户输入的有效性

## 性能优化

- **异步处理**: 使用async/await提高并发性能
- **流式响应**: 减少响应延迟
- **模型缓存**: 避免重复初始化
- **错误恢复**: 自动重试机制

## 扩展开发

### 添加新的模型支持

1. 在 `models/Factory.py` 中添加新模型
2. 在 `Text2SQLAgent` 中添加相应的处理逻辑
3. 更新配置和文档

### 自定义提示词

修改 `_build_system_prompt()` 方法来自定义系统提示词：

```python
def _build_system_prompt(self) -> str:
    return """你的自定义提示词"""
```

### 添加新的处理逻辑

在 `ChatHandler` 中添加新的处理方法：

```python
async def handle_special_query(self, message: str):
    # 特殊查询处理逻辑
    pass
```

## 故障排除

### 常见问题

1. **模型初始化失败**
   - 检查API密钥配置
   - 确认网络连接
   - 验证模型名称

2. **流式响应中断**
   - 检查网络稳定性
   - 确认模型支持流式输出
   - 查看错误日志

3. **SQL生成不准确**
   - 优化系统提示词
   - 提供更多上下文信息
   - 使用更强大的模型

### 调试模式

启用详细日志：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 许可证

本项目采用MIT许可证。 