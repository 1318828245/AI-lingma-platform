<template>
  <div class="login-wrap">
    <el-card class="login-card">
      <h1 class="login-title">AI 灵码平台</h1>
      <p class="muted">自然语言生成可运行前端工程</p>
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent="submit"
      >
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="admin" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            placeholder="请输入密码"
            @keyup.enter="submit"
          />
        </el-form-item>
        <el-button
          type="primary"
          class="login-btn"
          :loading="loading"
          @click="submit"
        >
          登录
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, type FormInstance, type FormRules } from "element-plus";
import { api } from "../api/client";
import { useAuthStore } from "../stores/auth";
import type { User } from "../types";

const router = useRouter();
const auth = useAuthStore();
const formRef = ref<FormInstance>();
const loading = ref(false);

const form = reactive({ username: "admin", password: "" });
const rules: FormRules = {
  username: [{ required: true, message: "请输入用户名", trigger: "blur" }],
  password: [{ required: true, message: "请输入密码", trigger: "blur" }],
};

async function submit() {
  await formRef.value?.validate();
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
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #0f172a, #1e293b);
}
.login-card {
  width: 380px;
  padding: 12px 8px;
}
.login-title {
  font-size: 24px;
  text-align: center;
  margin-bottom: 4px;
}
.login-card p {
  text-align: center;
  margin-bottom: 20px;
}
.login-btn {
  width: 100%;
  margin-top: 8px;
}
</style>
