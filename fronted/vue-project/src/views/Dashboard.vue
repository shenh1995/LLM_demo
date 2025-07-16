<script setup>
import { ref, nextTick, watch, onMounted } from 'vue'

const messages = ref([
  { role: 'ai', text: '你好，我是你的AI助手' }
])
const inputValue = ref('')
const hasUserInteracted = ref(false) // 添加用户交互状态
const isWaiting = ref(false) // 添加等待状态

function handleSend() {
  const text = inputValue.value.trim()
  if (!text) return
  
  hasUserInteracted.value = true // 标记用户已经交互过
  messages.value.push({ role: 'user', text })
  inputValue.value = ''
  isUserScrolling.value = false // 重置用户滚动状态
  scrollToBottom() // 立即滚动到底部
  
  // 发送消息到后端
  sendMessageToBackend(text)
}

// 发送消息到后端的函数
async function sendMessageToBackend(message) {
  try {
    // 设置等待状态
    isWaiting.value = true
    
    // 创建一个AbortController用于超时控制
    const controller = new AbortController()
    const timeoutId = setTimeout(() => {
      controller.abort()
    }, 600000) // 10分钟超时 (600000毫秒)
    
    const response = await fetch('http://localhost:8000/api/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: message,
        role: 'user'
      }),
      signal: controller.signal // 添加超时控制
    })
    
    // 清除超时定时器
    clearTimeout(timeoutId)
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    // 获取响应流
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let aiMessageIndex = -1 // 初始化为-1，表示还没有创建AI消息
    
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() // 保留不完整的行
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            
            if (data.type === 'status') {
              // 处理状态更新
              console.log('状态更新:', data.content)
              // 可以在这里更新UI状态，比如显示处理进度
            } else if (data.type === 'complete') {
              // 处理完成，创建AI消息并更新内容
              if (aiMessageIndex === -1) {
                // 如果还没有创建AI消息，现在创建
                aiMessageIndex = messages.value.length
                messages.value.push({ role: 'ai', text: data.content })
              } else {
                // 如果已经有AI消息，更新内容
                messages.value[aiMessageIndex].text = data.content
              }
              scrollToBottom()
              // 清除等待状态
              isWaiting.value = false
            } else if (data.type === 'error') {
              // 处理错误
              console.error('处理错误:', data.content)
              if (aiMessageIndex === -1) {
                aiMessageIndex = messages.value.length
                messages.value.push({ role: 'ai', text: data.content })
              } else {
                messages.value[aiMessageIndex].text = data.content
              }
              scrollToBottom()
              // 清除等待状态
              isWaiting.value = false
            } else if (data.type === 'char') {
              // 流式添加字符（兼容旧格式）
              if (aiMessageIndex === -1) {
                aiMessageIndex = messages.value.length
                messages.value.push({ role: 'ai', text: data.content })
              } else {
                messages.value[aiMessageIndex].text += data.content
              }
              scrollToBottom()
            }
          } catch (e) {
            console.error('解析流式数据失败:', e)
          }
        }
      }
    }
    
  } catch (error) {
    console.error('发送消息到后端失败:', error)
    // 如果发送失败，显示错误消息
    let errorMessage = '抱歉，连接后端失败，请稍后重试。'
    if (error.name === 'AbortError') {
      errorMessage = '请求超时，请稍后重试。'
    }
    messages.value.push({ role: 'ai', text: errorMessage })
    isUserScrolling.value = false
    scrollToBottom()
    // 清除等待状态
    isWaiting.value = false
  }
}

const chatAreaRef = ref(null)
const isUserScrolling = ref(false)
const lastScrollTop = ref(0)

watch(messages, async () => {
  await nextTick()
  if (chatAreaRef.value && !isUserScrolling.value) {
    chatAreaRef.value.scrollTop = chatAreaRef.value.scrollHeight
  }
}, { immediate: true })

// 添加一个方法来确保滚动到底部
function scrollToBottom() {
  nextTick(() => {
    if (chatAreaRef.value) {
      chatAreaRef.value.scrollTop = chatAreaRef.value.scrollHeight
      isUserScrolling.value = false
    }
  })
}

// 监听用户滚动行为
function handleScroll() {
  if (chatAreaRef.value) {
    const currentScrollTop = chatAreaRef.value.scrollTop
    const scrollHeight = chatAreaRef.value.scrollHeight
    const clientHeight = chatAreaRef.value.clientHeight
    
    // 如果用户向上滚动，标记为用户正在滚动
    if (currentScrollTop < lastScrollTop.value) {
      isUserScrolling.value = true
    }
    
    // 如果滚动到底部，重置用户滚动标记
    if (currentScrollTop + clientHeight >= scrollHeight - 10) {
      isUserScrolling.value = false
    }
    
    lastScrollTop.value = currentScrollTop
  }
}

// 在组件挂载时也滚动到底部
onMounted(() => {
  scrollToBottom()
})
</script>

<template>
    <div class="dashboard-root">
      <!-- 侧边栏 -->
      <aside class="sidebar">
        <div class="logo-area">
          <img src="/logo.svg" alt="logo" class="logo" />
          <span class="title">AI数据助手</span>
        </div>
        <nav class="menu">
          <div class="menu-group">
            <div class="menu-title">通问</div>
            <ul>
              <li class="menu-item active">大模型测试</li>
              <!-- <li class="menu-item">什么是大模型</li>
              <li class="menu-item">统计案件数量按分局分组柱状图</li>
              <li class="menu-item">统计案件数量按分局分组饼图</li>
              <li class="menu-item">统计商品价格按月份分组折线图</li> -->
            </ul>
          </div>
        </nav>
        <div class="sidebar-footer">
          <img src="https://cdn-icons-png.flaticon.com/512/616/616408.png" alt="avatar" class="avatar" />
          <span>用户中心</span>
        </div>
      </aside>
      <!-- 内容区 -->
      <main class="main-content">
        <div class="header">
          <span class="header-title">你的全能AI数据助手</span>
          <span class="header-desc">基于大模型的数据问答小助手</span>
        </div>
        <div v-if="!hasUserInteracted" class="card-list">
          <!-- 原有卡片内容 ... -->
          <div class="card">
            <div class="card-title">通用问答</div>
            <ul>
              <li>RAG模型优化问答系统流程</li>
              <li>向量技术提高数据检索效率</li>
              <li>整合公网数据提升回答质量</li>
              <li>RAG框架实现精准通用问答</li>
              <li>扩展方便对接三方开源系统</li>
            </ul>
          </div>
          <div class="card">
            <div class="card-title">数据问答</div>
            <ul>
              <li>Text2SQL 文本转SQL 数据库查询</li>
              <li>Echart图表增强且数据问答可视化</li>
              <li>Text2SQL与Echarts提供数据分析</li>
              <li>结合Echarts和Text2SQL提升解读</li>
              <li>基于大数据底座提升数据问答速度</li>
            </ul>
          </div>
          <div class="card">
            <div class="card-title">表格问答</div>
            <ul>
              <li>大模型解析文件实现智能问答</li>
              <li>统计学方法深入分析表格数据</li>
              <li>表格数据结合大模型精准解读</li>
              <li>支持更复杂表统计计算增强统计</li>
              <li>表格问答数据图表可视化展示</li>
            </ul>
          </div>
        </div>
        <div v-else class="chat-area" ref="chatAreaRef" @scroll="handleScroll">
          <div v-for="(msg, idx) in messages" :key="idx" :class="['msg', msg.role]">
            <span>{{ msg.role === 'user' ? '我：' : 'AI：' }}</span>
            <div class="bubble">{{ msg.text }}</div>
          </div>
          <!-- 等待状态显示 -->
          <div v-if="isWaiting" class="msg ai">
            <span>AI：</span>
            <div class="bubble waiting">
              <div class="waiting-text">等待结果中...</div>
              <div class="loading-dots">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        </div>
        <div class="footer-bar">
          <input class="input-bar" v-model="inputValue" @keyup.enter="handleSend" placeholder="输入任意问题，按 Enter 键快捷开始..." />
          <button class="send-btn" @click="handleSend">发送</button>
        </div>
      </main>
    </div>
  </template>
  
  <style scoped>
  * {
    box-sizing: border-box;
  }
  .dashboard-root {
    display: flex;
    height: 100vh;
    width: 100vw;
    position: fixed;

    /* background:  */
    max-width: none;
    margin: 0;
    box-shadow: none;
    border-radius: 0;
    background:#f7faff;
    top: 0;
    left: 0;
    right: 0;
  }
  body, html, #app {
    margin: 0;
    padding: 0;
    width: 100vw;
    height: 100vh;
    background: #f7faff;
  }
  .sidebar {
    width: 220px;
    background: linear-gradient(180deg, #6a7cf6 0%, #7ad1e6 100%);
    color: #fff;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    box-shadow: 2px 0 8px #e0e7ef33;
    padding-bottom: calc(100vh / 7 + 32px);
  }
  .logo-area {
    display: flex;
    align-items: center;
    padding: 24px 16px 12px 16px;
  }
  .logo {
    width: 36px;
    height: 36px;
    margin-right: 8px;
  }
  .title {
    font-size: 18px;
    font-weight: bold;
    letter-spacing: 1px;
  }
  .menu {
    flex: 1;
    padding: 0 0 0 16px;
  }
  .menu-group {
    margin-bottom: 18px;
  }
  .menu-title {
    font-size: 14px;
    color: #e0e7ef;
    margin-bottom: 6px;
  }
  .menu-item {
    font-size: 14px;
    padding: 6px 0;
    cursor: pointer;
    color: #e0e7ef;
    border-radius: 4px;
    transition: background 0.2s;
  }
  .menu-item.active, .menu-item:hover {
    background: #fff2;
    color: #fff;
  }
  .sidebar-footer {
  display: flex;
  align-items: center;
  padding: 16px;
  border-top: 1px solid #e0e7ef33;
  background: none;
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  width: 100%;
  }
  .avatar {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    margin-right: 8px;
  }
  .main-content {
    flex: 1;
    padding: 0;
    overflow-y: auto;
    padding-bottom: calc(100vh / 7 + 32px);
    max-width: 1200px;      /* 最大宽度 */
    margin: 0 auto;         /* 水平居中 */
    display: flex;
    flex-direction: column;
    /* align-items: center;  不再需要 */
  }
  .header {
    text-align: center;
    margin-bottom: 32px;
  }
  .header-title {
    font-size: 28px;
    font-weight: bold;
    color: #4a4a6a;
    display: block;
  }
  .header-desc {
    font-size: 16px;
    color: #8a8fa3;
    margin-top: 8px;
    display: block;
  }
  .card-list {
    display: flex;
    gap: 24px;
    justify-content: center;
    margin-bottom: 32px;
  }
  .card {
    background: #fff;
    border-radius: 16px;
    box-shadow: 0 2px 12px #e0e7ef33;
    padding: 24px 32px;
    min-width: 180px;
    max-width: 300px;
    flex: 1;
  }
  .card-title {
    font-size: 16px;
    font-weight: bold;
    color: #6a7cf6;
    margin-bottom: 16px;
  }
  .card ul {
    padding: 0;
    margin: 0;
    list-style: none;
  }
  .card li {
    font-size: 14px;
    color: #4a4a6a;
    margin-bottom: 10px;
    line-height: 1.6;
    padding-left: 16px;
    position: relative;
  }
  .card li:before {
    content: '•';
    color: #6a7cf6;
    position: absolute;
    left: 0;
  }
  .footer-bar {
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 24px 0 0 0;
    position: fixed;
    left: 220px;
    right: 200px;
    bottom: 50px;
    width: calc(100vw - 100px);
    background: #f7faff;
    z-index: 100;
    box-shadow: 0 -2px 8px #e0e7ef22;
  }
  .input-bar {
    width: 60%;
    max-width: 600px;
    min-width: 200px;
    padding: 12px 18px;
    border-radius: 24px;
    border: 1px solid #e0e7ef;
    font-size: 15px;
    outline: none;
    background: #f7faff;
    color: #4a4a6a;
    box-shadow: 0 2px 8px #e0e7ef22;
  }
  .send-btn {
    margin-left: 12px;
    padding: 0 22px;
    height: 44px;
    border: none;
    border-radius: 22px;
    background: linear-gradient(90deg, #6a7cf6 0%, #7ad1e6 100%);
    color: #fff;
    font-size: 16px;
    font-weight: bold;
    cursor: pointer;
    box-shadow: 0 2px 8px #e0e7ef22;
    transition: background 0.2s, box-shadow 0.2s;
    outline: none;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .send-btn:hover, .send-btn:focus {
    background: linear-gradient(90deg, #7ad1e6 0%, #6a7cf6 100%);
    box-shadow: 0 4px 16px #6a7cf633;
  }
  .chat-area {
    width: 100%;
    min-height: 400px;
    max-height: calc(100vh - 300px);
    max-width: 100%;      /* 占满主内容区 */
    overflow-y: auto;
    overflow-x: hidden;   /* 防止水平滚动 */
    /* background: #fff; */
    border-radius: 12px;
    box-shadow: 0 2px 8px #e0e7ef22;
    font-size: 16px;
    color: #4a4a6a;
    padding: 24px;
    margin-bottom: 16px;  /* 可适当减小 */
    white-space: pre-wrap;
    word-break: break-all;
    transition: all 0.2s;
    display: flex;
    flex-direction: column;
    gap: 12px;
    /* 移除justify-content: flex-end，让内容自然排列，支持滚动查看 */
    
    /* 自定义滚动条样式 */
    scrollbar-width: thin; /* Firefox */
    scrollbar-color: #6a7cf6 #f0f0f0; /* Firefox */
  }
  
  /* Webkit浏览器的滚动条样式 */
  .chat-area::-webkit-scrollbar {
    width: 8px;
  }
  
  .chat-area::-webkit-scrollbar-track {
    background: #f0f0f0;
    border-radius: 4px;
  }
  
  .chat-area::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, #6a7cf6 0%, #7ad1e6 100%);
    border-radius: 4px;
    transition: background 0.2s;
  }
  
  .chat-area::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(180deg, #7ad1e6 0%, #6a7cf6 100%);
  }
  .msg {
    display: flex;
    max-width: 90%;       /* 让气泡更宽 */
  }
  .msg.user {
    align-self: flex-end;
    justify-content: flex-end;
  }
  .msg.ai {
    align-self: flex-start;
    justify-content: flex-start;
  }
  .msg span {
    font-weight: bold;
    margin-right: 6px;
  }
  .msg.user {
    color: #fff;
  }
  .msg.user .bubble {
    background: linear-gradient(90deg, #6a7cf6 0%, #7ad1e6 100%);
    color: #fff;
    border-radius: 18px 18px 4px 18px;
    padding: 10px 18px;
    margin-left: 40px;
    box-shadow: 0 2px 8px #e0e7ef22;
  }
  .msg.ai .bubble {
    background: #f2f3f7;
    color: #222;
    border-radius: 18px 18px 18px 4px;
    padding: 10px 18px;
    margin-right: 40px;
    box-shadow: 0 2px 8px #e0e7ef22;
  }
  
  /* 等待状态样式 */
  .msg.ai .bubble.waiting {
    background: #f8f9fa;
    border: 1px solid #e9ecef;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  
  .waiting-text {
    color: #6c757d;
    font-size: 14px;
  }
  
  .loading-dots {
    display: flex;
    gap: 4px;
  }
  
  .loading-dots span {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #6a7cf6;
    animation: loading-dots 1.4s infinite ease-in-out;
  }
  
  .loading-dots span:nth-child(1) {
    animation-delay: -0.32s;
  }
  
  .loading-dots span:nth-child(2) {
    animation-delay: -0.16s;
  }
  
  @keyframes loading-dots {
    0%, 80%, 100% {
      transform: scale(0.8);
      opacity: 0.5;
    }
    40% {
      transform: scale(1);
      opacity: 1;
    }
  }
  </style>
  
  <style scoped>
  @media (max-width: 13000px) {
    .dashboard-root {
      max-width: 100%;
      border-radius: 0;
      box-shadow: none;
    }
  }
  @media (max-width: 900px) {
    .dashboard-root {
      flex-direction: column;
      height: auto;
    }
    .sidebar {
      width: 100vw;
      flex-direction: row;
      height: 56px;
      min-width: 0;
      max-width: 100vw;
      align-items: center;
      justify-content: flex-start;
      box-shadow: 0 2px 8px #e0e7ef33;
      position: sticky;
      top: 0;
      z-index: 10;
    }
    .logo-area {
      padding: 8px 12px;
    }
    .menu {
      flex: 1;
      padding: 0 8px;
      display: flex;
      flex-direction: row;
      align-items: center;
      overflow-x: auto;
    }
    .menu-group {
      margin-bottom: 0;
      margin-right: 18px;
    }
    .sidebar-footer {
      display: none;
    }
  }
  @media (max-width: 900px) {
    .main-content {
      padding: 24px 8px 0 8px;
    }
    .card-list {
      flex-direction: column;
      gap: 16px;
      align-items: stretch;
    }
    .card {
      min-width: 0;
      max-width: 100%;
      padding: 18px 12px;
    }
    .header-title {
      font-size: 22px;
    }
    .header-desc {
      font-size: 13px;
    }
    .footer-bar {
      padding: 16px 0 0 0;
    }
    .input-bar {
      width: 100%;
      max-width: 100vw;
      min-width: 0;
      font-size: 14px;
      padding: 10px 12px;
    }
  }
  @media (max-width: 600px) {
    .header-title {
      font-size: 18px;
    }
    .header-desc {
      font-size: 12px;
    }
    .card-title {
      font-size: 15px;
    }
    .card li {
      font-size: 12px;
    }
  }
  </style>

<style>
html, body, #app {
  margin: 0 !important;
  padding: 0 !important;
  width: 100vw !important;
  height: 100vh !important;
  overflow-x: hidden !important;
  background: #f7faff;
}
</style>