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
      <p class="panel-title">{{ registering ? '注册工作台账号' : '登录工作台' }}</p>
      <label class="field">
        <span class="mono label">用户名</span>
        <input v-model="form.username" autocomplete="username" :placeholder="registering ? '3–64 位字母、数字、下划线或连字符' : 'admin'" />
      </label>
      <label class="field">
        <span class="mono label">密码</span>
        <input
          v-model="form.password"
          type="password"
          :autocomplete="registering ? 'new-password' : 'current-password'"
          :placeholder="registering ? '至少 6 位密码' : '输入密码'"
        />
      </label>
      <label v-if="registering" class="field">
        <span class="mono label">邮箱（选填）</span>
        <input v-model="form.email" autocomplete="email" type="email" placeholder="name@example.com" />
      </label>
      <button class="submit" type="submit" :disabled="loading">
        {{ loading ? (registering ? '注册中…' : '登录中…') : (registering ? '创建账号' : '进入工作台') }}
      </button>
      <button v-if="registrationEnabled" class="switch-mode" type="button" :disabled="loading" @click="toggleMode">
        {{ registering ? '已有账号？返回登录' : '没有账号？立即注册' }}
      </button>
      <p class="muted hint">{{ registering ? '注册完成后以普通用户身份进入工作台。' : '默认账号 admin，密码 admin123' }}</p>
    </form>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api/client";
import { useAuthStore } from "../stores/auth";
import type { User } from "../types";

const router = useRouter();
const auth = useAuthStore();
const loading = ref(false);
const registering = ref(false);
const registrationEnabled = ref(false);
const form = reactive({ username: "admin", password: "", email: "" });

onMounted(async () => {
  try {
    const { data } = await api.get<{ enabled: boolean }>("/auth/registration-status");
    registrationEnabled.value = data.enabled;
  } catch {
    // Keep the login path usable if a deployment has not yet updated the API.
    registrationEnabled.value = false;
  }
});

function toggleMode() {
  registering.value = !registering.value;
  form.password = "";
  form.email = "";
  if (registering.value && form.username === "admin") form.username = "";
}

async function submit() {
  if (!form.username || !form.password) {
    ElMessage.warning("用户名和密码都要填");
    return;
  }
  loading.value = true;
  try {
    if (registering.value) {
      await api.post("/auth/register", form);
      ElMessage.success("注册成功，请登录");
      registering.value = false;
      form.password = "";
      form.email = "";
      return;
    }
    const { data } = await api.post("/auth/login", { username: form.username, password: form.password });
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
.switch-mode {
  align-self: center;
  border: 0;
  padding: 2px 4px;
  background: transparent;
  color: var(--primary-dark);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.switch-mode:hover:not(:disabled) {
  text-decoration: underline;
  text-underline-offset: 3px;
}
.switch-mode:disabled { cursor: wait; opacity: .6; }
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
