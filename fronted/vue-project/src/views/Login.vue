<template>
  <div class="login-bg">
    <div class="login-wrapper">
      <div class="login-card">
        <!-- 头部 -->
        <div class="login-header">
          <div class="logo">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
            </svg>
          </div>
          <h1>欢迎回来</h1>
          <p>请登录您的账户</p>
        </div>
        <!-- 登录表单 -->
        <form @submit.prevent="handleLogin" class="login-form">
          <div class="form-group">
            <div class="input-wrapper">
              <div class="input-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                  <circle cx="12" cy="7" r="4"/>
                </svg>
              </div>
              <input 
                v-model="username" 
                type="text" 
                placeholder="请输入用户名"
                required 
                class="form-input"
                autocomplete="username"
              />
            </div>
          </div>
          <div class="form-group">
            <div class="input-wrapper">
              <div class="input-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                  <circle cx="12" cy="16" r="1"/>
                  <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                </svg>
              </div>
              <input 
                v-model="password" 
                :type="showPassword ? 'text' : 'password'" 
                placeholder="请输入密码"
                required 
                class="form-input"
                autocomplete="current-password"
              />
              <button 
                type="button" 
                @click="togglePassword" 
                class="password-toggle"
                aria-label="切换密码显示"
              >
                <svg v-if="showPassword" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                  <circle cx="12" cy="12" r="3"/>
                </svg>
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                  <line x1="1" y1="1" x2="23" y2="23"/>
                </svg>
              </button>
            </div>
          </div>
          <div class="form-options">
            <label class="checkbox-wrapper">
              <input type="checkbox" v-model="rememberMe" />
              <span class="checkmark"></span>
              记住我
            </label>
            <a href="#" class="forgot-password">忘记密码？</a>
          </div>
          <button type="submit" class="login-btn" :disabled="isLoading">
            <span v-if="isLoading" class="loading-spinner"></span>
            <span v-else>{{ isLoading ? '登录中...' : '登录' }}</span>
          </button>
        </form>
        <!-- 错误提示 -->
        <div v-if="error" class="error-message">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="15" y1="9" x2="9" y2="15"/>
            <line x1="9" y1="9" x2="15" y2="15"/>
          </svg>
          {{ error }}
        </div>
        <!-- 底部 -->
        <div class="login-footer">
          <p>还没有账户？ <a href="#" class="signup-link">立即注册</a></p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const username = ref('')
const password = ref('')
const error = ref('')
const showPassword = ref(false)
const rememberMe = ref(false)
const isLoading = ref(false)
function togglePassword() {
  showPassword.value = !showPassword.value
}
async function handleLogin() {
  if (!username.value || !password.value) {
    error.value = '请填写完整的登录信息'
    return
  }
  isLoading.value = true
  error.value = ''
  try {
    const res = await fetch('http://localhost:8000/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: username.value,
        password: password.value
      })
    })
    const data = await res.json()
    if (data.success) {
      error.value = ''
      router.push('/dashboard')
    } else {
      error.value = data.message || '用户名或密码错误，请重试'
    }
  } catch (e) {
    error.value = '网络错误，请稍后重试'
  }
  isLoading.value = false
}
</script>

<style scoped>
.login-bg {
  min-height: 100vh;
  width: 100vw;
  position: fixed;
  top: 0;
  left: 0;
  z-index: 0;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow-y: auto;
}

.login-wrapper {
  width: 100%;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1;
}

.login-card {
  background: rgba(255, 255, 255, 0.97);
  backdrop-filter: blur(10px);
  border-radius: 20px;
  padding: 48px 40px 32px 40px;
  box-shadow: 0 10px 32px rgba(102, 126, 234, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.2);
  width: 100%;
  max-width: 400px;
  min-width: 0;
  margin: 32px 16px;
  box-sizing: border-box;
}

@media (max-width: 600px) {
  .login-card {
    padding: 32px 8px 24px 8px;
    margin: 16px 4px;
    max-width: 98vw;
  }
}

@media (max-width: 400px) {
  .login-card {
    padding: 16px 2px 12px 2px;
    margin: 8px 2px;
  }
}

.login-header {
  text-align: center;
  margin-bottom: 30px;
}
.logo {
  width: 60px;
  height: 60px;
  margin: 0 auto 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}
.logo svg {
  width: 30px;
  height: 30px;
}
.login-header h1 {
  font-size: 28px;
  font-weight: 700;
  color: #2d3748;
  margin: 0 0 8px 0;
}
.login-header p {
  color: #718096;
  margin: 0;
  font-size: 16px;
}
.login-form {
  margin-bottom: 20px;
}
.form-group {
  margin-bottom: 20px;
}
.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}
.input-icon {
  position: absolute;
  left: 16px;
  color: #a0aec0;
  z-index: 1;
  pointer-events: none;
}
.input-icon svg {
  width: 20px;
  height: 20px;
}
.form-input {
  width: 100%;
  padding: 16px 16px 16px 48px;
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  font-size: 16px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  background: white;
  appearance: none;
  font-family: inherit;
}
.form-input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}
.form-input::placeholder {
  color: #a0aec0;
  opacity: 1;
}
.form-input:-webkit-autofill,
.form-input:-webkit-autofill:hover,
.form-input:-webkit-autofill:focus {
  -webkit-box-shadow: 0 0 0px 1000px white inset;
  -webkit-text-fill-color: #2d3748;
  transition: background-color 5000s ease-in-out 0s;
}
.password-toggle {
  position: absolute;
  right: 16px;
  background: none;
  border: none;
  color: #a0aec0;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: color 0.3s ease;
  appearance: none;
}
.password-toggle:hover {
  color: #667eea;
}
.password-toggle:focus {
  outline: none;
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
}
.password-toggle svg {
  width: 20px;
  height: 20px;
}
.form-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 8px;
}
.checkbox-wrapper {
  display: flex;
  align-items: center;
  cursor: pointer;
  font-size: 14px;
  color: #4a5568;
  user-select: none;
}
.checkbox-wrapper input[type="checkbox"] {
  display: none;
}
.checkmark {
  width: 18px;
  height: 18px;
  border: 2px solid #e2e8f0;
  border-radius: 4px;
  margin-right: 8px;
  position: relative;
  transition: all 0.3s ease;
  transform: translateZ(0);
}
.checkbox-wrapper input[type="checkbox"]:checked + .checkmark {
  background: #667eea;
  border-color: #667eea;
}
.checkbox-wrapper input[type="checkbox"]:checked + .checkmark::after {
  content: '✓';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: white;
  font-size: 12px;
  font-weight: bold;
}
.forgot-password {
  color: #667eea;
  text-decoration: none;
  font-size: 14px;
  transition: color 0.3s ease;
}
.forgot-password:hover {
  color: #5a67d8;
}
.forgot-password:focus {
  outline: none;
  text-decoration: underline;
}
.login-btn {
  width: 100%;
  padding: 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  appearance: none;
  font-family: inherit;
  will-change: transform;
}
.login-btn:hover:not(:disabled) {
  transform: translateY(-2px) translateZ(0);
  box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
}
.login-btn:active:not(:disabled) {
  transform: translateY(0) translateZ(0);
}
.login-btn:focus {
  outline: none;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.3);
}
.login-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
  transform: none;
}
.loading-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top: 2px solid white;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}
@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
.error-message {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background: #fed7d7;
  border: 1px solid #feb2b2;
  border-radius: 8px;
  color: #c53030;
  font-size: 14px;
  margin-bottom: 20px;
  animation: slideIn 0.3s ease;
}
@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
.error-message svg {
  width: 16px;
  height: 16px;
  margin-right: 8px;
  flex-shrink: 0;
}
.login-footer {
  text-align: center;
  padding-top: 20px;
  border-top: 1px solid #e2e8f0;
}
.login-footer p {
  margin: 0;
  color: #718096;
  font-size: 14px;
}
.signup-link {
  color: #667eea;
  text-decoration: none;
  font-weight: 600;
  transition: color 0.3s ease;
}
.signup-link:hover {
  color: #5a67d8;
}
.signup-link:focus {
  outline: none;
  text-decoration: underline;
}
</style>