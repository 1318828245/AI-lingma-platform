<template>
  <div class="login-wrap">
    <div class="brand">
      <p class="eyebrow">AI · Lingma Studio</p>
      <h1 class="wordmark">灵码</h1>
      <p class="tagline">说一句需求，看页面长出来</p>
      <ul class="points">
        <li>自然语言生成前端工程</li>
        <li>对话与实时预览同屏</li>
        <li>不满意就继续说，改到满意为止</li>
      </ul>
    </div>
    <form class="panel login-card" @submit.prevent="submit">
      <p class="panel-title">登录工作台</p>
      <label class="field">
        <span class="mono label">用户名</span>
        <input v-model="form.username" autocomplete="username" placeholder="admin" />
      </label>
      <label class="field">
        <span class="mono label">密码</span>
        <input
          v-model="form.password"
          type="password"
          autocomplete="current-password"
          placeholder="输入密码"
        />
      </label>
      <button class="submit" type="submit" :disabled="loading">
        {{ loading ? "登录中…" : "进入工作台" }}
      </button>
      <p class="muted hint">默认账号 admin，密码 admin123</p>
    </form>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api/client";
import { useAuthStore } from "../stores/auth";
import type { User } from "../types";

const router = useRouter();
const auth = useAuthStore();
const loading = ref(false);
const form = reactive({ username: "admin", password: "" });

async function submit() {
  if (!form.username || !form.password) {
    ElMessage.warning("用户名和密码都要填");
    return;
  }
  loading.value = true;
  try {
    const { data } = await api.post("/auth/login", form);
    const payload: {
      access_token: string;
      refresh_token: string;
      user: User;
    } = data;
    auth.setSession(payload.access_token, payload.refresh_token, payload.user);
    router.push("/");
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || "登录失败，请重试");
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.login-wrap {
  height: 100vh;
  display: grid;
  grid-template-columns: 1fr 1fr;
  background:
    radial-gradient(circle at 15% 20%, rgba(242, 169, 59, 0.16), transparent 38%),
    radial-gradient(circle at 85% 80%, rgba(91, 103, 241, 0.14), transparent 42%),
    var(--canvas);
}
.brand {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 0 12%;
}
.brand .eyebrow {
  color: #b97f1c;
  margin-bottom: 14px;
}
.brand h1 {
  font-size: 64px;
  letter-spacing: 0.04em;
  color: var(--ink);
}
.tagline {
  margin-top: 10px;
  color: var(--muted);
  font-size: 16px;
}
.points {
  list-style: none;
  margin-top: 28px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  color: var(--muted);
  font-size: 14px;
}
.points li::before {
  content: "✦";
  color: var(--primary);
  margin-right: 10px;
  font-size: 12px;
}
.login-card {
  align-self: center;
  justify-self: center;
  width: min(400px, 84%);
  padding: 34px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  border-top: 3px solid var(--amber);
  box-shadow: var(--shadow-md);
}
.field {
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.label {
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--muted);
}
.field input {
  height: 44px;
  border: 1px solid var(--line-strong);
  border-radius: var(--radius-md);
  padding: 0 14px;
  font-size: 14px;
  outline: none;
  background: var(--paper);
  transition: border-color 0.15s, box-shadow 0.15s;
}
.field input:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(91, 103, 241, 0.12);
}
.submit {
  height: 44px;
  border: none;
  border-radius: var(--radius-md);
  background: var(--primary);
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(91, 103, 241, 0.28);
  transition: background 0.15s, box-shadow 0.15s;
}
.submit:hover:not(:disabled) {
  background: var(--primary-dark);
  box-shadow: 0 4px 12px rgba(91, 103, 241, 0.34);
}
.submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.hint {
  text-align: center;
  font-size: 12px;
}
@media (max-width: 820px) {
  .login-wrap {
    grid-template-columns: 1fr;
    overflow-y: auto;
  }
  .brand {
    padding: 48px 24px 0;
  }
  .points {
    display: none;
  }
  .login-card {
    grid-row: 2;
    margin: 28px auto;
  }
}
</style>
