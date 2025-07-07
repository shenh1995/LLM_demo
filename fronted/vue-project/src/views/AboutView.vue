<template>
  <div class="about">
    <h1>关于页面</h1>
    <p>这是一个使用 Vue 3 和 Vue Router 构建的示例项目。</p>
    
    <div class="info">
      <h3>技术栈</h3>
      <ul>
        <li>Vue 3 - 渐进式 JavaScript 框架</li>
        <li>Vue Router - 官方路由管理器</li>
        <li>Vite - 下一代前端构建工具</li>
        <li>Composition API - Vue 3 的组合式 API</li>
      </ul>
    </div>

    <div class="info">
      <h3>功能特性</h3>
      <ul>
        <li>单页面应用 (SPA)</li>
        <li>路由导航</li>
        <li>用户登录界面</li>
        <li>响应式设计</li>
      </ul>
    </div>
  </div>
</template>

<script setup>
// 关于页面组件逻辑
</script>

<style scoped>
.about {
  max-width: 600px;
  margin: 0 auto;
  padding: 20px;
}

.info {
  margin: 30px 0;
  padding: 20px;
  border: 1px solid #ddd;
  border-radius: 8px;
  background: #f9f9f9;
}

.info h3 {
  color: #42b983;
  margin-bottom: 15px;
}

.info ul {
  list-style-type: none;
  padding: 0;
}

.info li {
  padding: 8px 0;
  border-bottom: 1px solid #eee;
}

.info li:last-child {
  border-bottom: none;
}
</style> 