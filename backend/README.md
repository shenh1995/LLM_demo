# 后端服务

这是LLM Demo项目的后端服务，提供API接口和流式聊天功能。

## 快速开始

### 1. 环境准备

确保已安装Python 3.8+和必要的依赖：

```bash
# 创建虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows

# 安装依赖 - 方法一：使用安装脚本（推荐）
python install_dependencies.py

# 安装依赖 - 方法二：手动安装
pip install -r requirements.txt
# 或
pip3 install -r requirements.txt
```

### 2. 环境变量配置

运行环境变量设置脚本：

```bash
python setup_env.py
```

这将创建 `.env` 文件，请编辑该文件填入实际的配置值。

### 3. 启动服务

#### 方法一：使用启动脚本（推荐）

```bash
# Linux/macOS
./start.sh

# Windows
python start_server.py
```

#### 方法二：手动启动

```bash
# 先初始化
python init.py

# 再启动服务器
python -m uvicorn login_api:app --reload --host 0.0.0.0 --port 8000
```

## 依赖说明

### 核心依赖

- **FastAPI**: 现代、快速的Web框架
- **Uvicorn**: ASGI服务器
- **Pydantic**: 数据验证和序列化
- **python-dotenv**: 环境变量管理
- **LangChain**: AI应用开发框架
- **Requests**: HTTP客户端库

### 安装依赖

项目提供了多种安装依赖的方式：

1. **自动安装脚本**（推荐）：
   ```bash
   python install_dependencies.py
   ```

2. **手动安装**：
   ```bash
   pip install -r requirements.txt
   ```

3. **使用pip3**：
   ```bash
   pip3 install -r requirements.txt
   ```

4. **在虚拟环境中安装**：
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   pip install -r requirements.txt
   ```

## API接口

### 登录接口
- **POST** `/api/login`
- 请求体：`{"username": "user", "password": "pass"}`

### 聊天接口
- **POST** `/api/chat`
- 请求体：`{"message": "用户消息", "role": "user"}`
- 返回：`{"success": true, "message": "hello world"}`

### 流式聊天接口
- **POST** `/api/chat/stream`
- 请求体：`{"message": "用户消息", "role": "user"}`
- 返回：Server-Sent Events流式数据

## 项目结构

```
backend/
├── init.py                  # 初始化脚本
├── login_api.py             # API服务器
├── start_server.py          # 启动脚本
├── start.sh                # Shell启动脚本
├── setup_env.py            # 环境变量设置脚本
├── install_dependencies.py # 依赖安装脚本
├── requirements.txt        # 依赖列表
├── env.example             # 环境变量示例文件
├── models/
│   └── Factory.py          # 模型工厂
├── tools/                  # 工具目录
├── logs/                   # 日志目录
├── uploads/                # 上传文件目录
└── cache/                  # 缓存目录
```

## 配置说明

### 环境变量

主要的环境变量配置：

- `OPENAI_API_KEY`: OpenAI API密钥
- `SILICONFLOW_API_KEY`: SiliconFlow API密钥（用于开源模型）
- `DATABASE_URL`: 数据库连接URL
- `REDIS_URL`: Redis连接URL
- `DEBUG`: 调试模式
- `SECRET_KEY`: 应用密钥

### 模型配置

支持的模型类型：

- **OpenAI**: qianwen, gpt-4等
- **Azure OpenAI**: 通过Azure部署的OpenAI模型
- **DeepSeek**: 通过SiliconFlow平台调用
- **Qianwen**: 阿里云通义千问

## 开发说明

### 添加新的API接口

1. 在 `login_api.py` 中添加新的路由
2. 定义请求和响应模型
3. 实现业务逻辑

### 添加新的模型

1. 在 `models/Factory.py` 中添加新的模型类
2. 实现模型初始化逻辑
3. 在API中使用新模型

### 日志

日志文件保存在 `logs/` 目录下，可通过环境变量 `LOG_LEVEL` 控制日志级别。

## 故障排除

### 常见问题

1. **依赖安装失败**
   - 确保Python版本 >= 3.8
   - 尝试升级pip: `pip install --upgrade pip`
   - 使用虚拟环境避免权限问题

2. **端口被占用**
   - 修改 `.env` 文件中的 `PORT` 配置
   - 或使用 `lsof -i :8000` 查看占用进程

3. **API密钥错误**
   - 检查 `.env` 文件中的API密钥配置
   - 确保密钥有效且有足够的配额

4. **模型加载失败**
   - 检查网络连接
   - 确认API密钥和端点配置正确

### 调试模式

设置 `DEBUG=True` 启用调试模式，将显示详细的错误信息。

## 部署

### 生产环境

1. 设置 `DEBUG=False`
2. 使用强密码和安全的密钥
3. 配置HTTPS
4. 使用进程管理器（如PM2、Supervisor）

### Docker部署

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "start_server.py"]
```

## 许可证

本项目采用MIT许可证。 