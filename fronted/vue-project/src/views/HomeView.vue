<template>
  <div class="home">
    <h1>欢迎来到首页</h1>
    <p>这是一个 Vue 3 + Vue Router 的示例项目</p>
    <div class="features">
      <div class="feature">
        <h3>Vue 3</h3>
        <p>使用最新的 Vue 3 Composition API</p>
      </div>
      <div class="feature">
        <h3>Vue Router</h3>
        <p>单页面应用路由管理</p>
      </div>
      <div class="feature">
        <h3>用户登录</h3>
        <p>点击上方导航栏的"登录"体验登录功能</p>
      </div>
    </div>
  </div>
</template>

<script setup>
// 首页组件逻辑
</script>

<style scoped>
.home {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.features {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  margin-top: 40px;
}

.feature {
  padding: 20px;
  border: 1px solid #ddd;
  border-radius: 8px;
  background: #f9f9f9;
}

.feature h3 {
  color: #42b983;
  margin-bottom: 10px;
}
</style> 