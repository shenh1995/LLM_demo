<script setup>
import { useRoute } from 'vue-router'
const route = useRoute()
// 移除不需要的组件导入
</script>

<template>
  <div id="app">
    <!-- 导航菜单 -->
    <nav v-if="route.path !== '/dashboard'">
      <router-link to="/">首页</router-link> |
      <router-link to="/login">登录</router-link> |
      <router-link to="/about">关于</router-link>
    </nav>

    <!-- 路由视图 -->
    <router-view />
  </div>
</template>

<style scoped>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
  margin-top: 60px;
}

nav {
  padding: 30px;
  display: flex;
  flex-direction: row;
  justify-content: center;
  align-items: center;
  gap: 20px;
}

nav a {
  font-weight: bold;
  color: #2c3e50;
  text-decoration: none;
  margin: 0 10px;
  writing-mode: unset;
}

nav a.router-link-exact-active {
  color: #42b983;
}
</style>
