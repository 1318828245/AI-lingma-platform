<template>
  <div class="login-wrap">
    <div class="brand">
      <p class="eyebrow">AI · Lingma Studio</p>
      <h1 class="wordmark">灵码</h1>
      <p class="tagline">说需求，看它长出来</p>
    </div>
    <form class="panel login-card" @submit.prevent="submit">
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
    ElMessage.error(error.response?.data?.detail || "登录失败");
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
    radial-gradient(circle at 20% 20%, rgba(245, 158, 11, 0.12), transparent 34%),
    radial-gradient(circle at 80% 75%, rgba(37, 99, 235, 0.14), transparent 40%),
    var(--ink-950);
}
.brand {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 0 12%;
  color: #e7ecf5;
}
.brand .eyebrow {
  color: var(--amber);
  margin-bottom: 14px;
}
.brand h1 {
  font-size: 64px;
  letter-spacing: 0.04em;
}
.tagline {
  margin-top: 10px;
  color: #94a3b8;
  font-size: 15px;
}
.login-card {
  align-self: center;
  justify-self: center;
  width: min(400px, 84%);
  padding: 34px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  border-top: 3px solid var(--amber);
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
  height: 42px;
  border: 1px solid var(--line-strong);
  border-radius: var(--radius-md);
  padding: 0 14px;
  font-size: 14px;
  font-family: var(--font-body);
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.field input:focus {
  border-color: var(--ink-700);
  box-shadow: 0 0 0 3px rgba(14, 21, 38, 0.08);
}
.submit {
  height: 44px;
  border: none;
  border-radius: var(--radius-md);
  background: var(--ink-900);
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}
.submit:hover {
  background: var(--ink-800);
}
.submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
@media (max-width: 820px) {
  .login-wrap {
    grid-template-columns: 1fr;
  }
  .brand {
    padding: 40px 24px 0;
  }
  .login-card {
    grid-row: 2;
  }
}
</style>
