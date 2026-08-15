<template>
  <div class="page projects-page">
    <header class="page-header">
      <div class="brand-line">
        <p class="eyebrow">AI · Lingma Studio</p>
        <h1 class="wordmark page-title">项目</h1>
      </div>
      <div class="head-actions">
        <span class="mono user-chip">{{ auth.user?.username }}</span>
        <button class="btn primary" @click="openCreate">新建项目</button>
        <button class="btn ghost" @click="logout">退出</button>
      </div>
    </header>

    <div v-if="projects.length" class="grid">
      <article v-for="p in projects" :key="p.id" class="panel project-card">
        <div class="thumb">
          <img
            v-if="thumbState[p.id] === 'ok'"
            :src="thumbSrc(p)"
            :alt="`${p.name} 截图`"
            loading="lazy"
            @error="thumbState[p.id] = 'error'"
          />
          <div v-else class="thumb-default">
            <span class="thumb-icon" aria-hidden="true">▧</span>
            <span class="thumb-text">
              {{
                thumbState[p.id] === "loading" ? "正在生成截图…" : "尚未生成"
              }}
            </span>
          </div>
        </div>
        <div class="card-body">
          <div class="card-top">
            <h3 class="wordmark card-name">{{ p.name }}</h3>
            <span class="mono tech">{{ p.tech_stack }}</span>
          </div>
          <p class="card-desc">{{ p.description || "暂无描述" }}</p>
          <p class="mono card-meta">
            {{ p.template }} · {{ p.status }}
          </p>
          <div class="card-actions">
            <button class="btn primary sm" @click="openGeneration(p)">生成对话</button>
            <button class="btn ghost sm" @click="openPreview(p)">预览</button>
            <button class="btn danger sm" @click="remove(p)">删除</button>
          </div>
        </div>
      </article>
    </div>
    <div v-else class="panel empty-state">
      <p class="empty-mark">▧</p>
      <p class="empty-title">还没有项目</p>
      <p class="muted">新建一个项目，用一句话描述你想要的页面</p>
      <button class="btn primary" @click="openCreate">新建项目</button>
    </div>

    <div v-if="dialogVisible" class="mask" @click.self="dialogVisible = false">
      <form class="panel dialog" @submit.prevent="create">
        <p class="panel-title">新建项目</p>
        <label class="field">
          <span class="mono label">项目名称</span>
          <input v-model="form.name" placeholder="例如：我的个人名片" autofocus />
        </label>
        <label class="field">
          <span class="mono label">起始模板</span>
          <select v-model="form.template">
            <option value="blank">空白项目</option>
            <option
              v-for="t in templates"
              :key="t.id"
              :value="t.name"
            >
              {{ t.name }}（{{ t.tech_stack }}）
            </option>
          </select>
        </label>
        <label class="field">
          <span class="mono label">技术栈</span>
          <select v-model="form.tech_stack">
            <option value="html">纯 HTML/CSS/JS</option>
            <option value="vue3">Vue 3 + Vite</option>
          </select>
        </label>
        <label class="field">
          <span class="mono label">描述（可选）</span>
          <textarea v-model="form.description" rows="2" />
        </label>
        <div class="dialog-actions">
          <button type="button" class="btn ghost" @click="dialogVisible = false">
            取消
          </button>
          <button type="submit" class="btn primary" :disabled="creating">
            {{ creating ? "创建中…" : "创建" }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  createProject,
  deleteProject,
  listProjects,
  listTemplates,
} from "../api/projects";
import { useAuthStore } from "../stores/auth";
import type { Project, Template } from "../types";

const router = useRouter();
const auth = useAuthStore();
const projects = ref<Project[]>([]);
const templates = ref<Template[]>([]);
const dialogVisible = ref(false);
const creating = ref(false);
const form = reactive({
  name: "",
  description: "",
  template: "blank",
  tech_stack: "html",
});
const thumbState = ref<Record<number, "loading" | "ok" | "error">>({});
const thumbNonce = ref(Date.now());

function thumbSrc(p: Project) {
  return `/api/projects/${p.id}/screenshot?token=${encodeURIComponent(
    auth.accessToken
  )}&t=${thumbNonce.value}`;
}

onMounted(async () => {
  projects.value = await listProjects();
  projects.value.forEach((p) => {
    thumbState.value[p.id] = "loading";
  });
  templates.value = await listTemplates();
});

function openCreate() {
  form.name = "";
  form.description = "";
  form.template = "blank";
  form.tech_stack = "html";
  dialogVisible.value = true;
}

async function create() {
  if (!form.name.trim()) {
    ElMessage.warning("先给项目起个名字");
    return;
  }
  creating.value = true;
  try {
    const project = await createProject({
      name: form.name.trim(),
      description: form.description,
      template: form.template,
      tech_stack: form.tech_stack,
    });
    ElMessage.success("项目创建成功");
    dialogVisible.value = false;
    projects.value.unshift(project);
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || "创建失败");
  } finally {
    creating.value = false;
  }
}

function openGeneration(project: Project) {
  router.push(`/projects/${project.id}`);
}

function openPreview(project: Project) {
  router.push(`/projects/${project.id}/preview`);
}

async function remove(project: Project) {
  await ElMessageBox.confirm(
    `确定删除项目「${project.name}」？工作区、版本与部署记录会一并清理。`,
    "删除确认",
    { type: "warning" }
  );
  await deleteProject(project.id);
  projects.value = projects.value.filter((p) => p.id !== project.id);
  ElMessage.success("已删除");
}

function logout() {
  auth.logout();
  router.push("/login");
}
</script>

<style scoped>
.projects-page {
  max-width: 1080px;
}
.brand-line .eyebrow {
  color: var(--amber);
  margin-bottom: 4px;
}
.head-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
.user-chip {
  font-size: 12px;
  color: var(--muted);
  border: 1px solid var(--line-strong);
  border-radius: 999px;
  padding: 5px 12px;
  background: var(--paper);
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}
.project-card {
  overflow: hidden;
  transition: transform 0.15s, box-shadow 0.15s, border-color 0.15s;
}
.project-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
  border-color: var(--line-strong);
}
.thumb {
  height: 150px;
  background:
    radial-gradient(circle at 20% 20%, rgba(91, 103, 241, 0.06), transparent 45%),
    var(--canvas-deep);
  border-bottom: 1px solid var(--line);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: top;
  display: block;
}
.thumb-default {
  text-align: center;
  color: var(--faint);
  padding: 16px;
}
.thumb-icon {
  display: block;
  font-size: 30px;
  color: var(--primary);
  opacity: 0.45;
  margin-bottom: 6px;
}
.thumb-text {
  font-size: 12px;
}
.card-body {
  padding: 14px 18px 18px;
}
.card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}
.card-name {
  font-size: 17px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tech {
  font-size: 11px;
  color: #9a6b16;
  background: var(--amber-soft);
  border-radius: var(--radius-sm);
  padding: 3px 8px;
  flex-shrink: 0;
}
.card-desc {
  font-size: 13px;
  color: var(--muted);
  min-height: 38px;
  line-height: 1.5;
}
.card-meta {
  font-size: 11px;
  color: var(--faint);
  margin: 10px 0 14px;
}
.card-actions {
  display: flex;
  gap: 8px;
}
.empty-state {
  padding: 64px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  text-align: center;
}
.empty-mark {
  font-size: 42px;
  color: var(--primary);
  opacity: 0.45;
}
.empty-title {
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 600;
}
.mask {
  position: fixed;
  inset: 0;
  background: rgba(46, 42, 38, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
  backdrop-filter: blur(2px);
}
.dialog {
  width: min(440px, 92%);
  padding: 26px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  border-top: 3px solid var(--amber);
  box-shadow: var(--shadow-md);
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.label {
  font-size: 11px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--muted);
}
.field input,
.field select,
.field textarea {
  border: 1px solid var(--line-strong);
  border-radius: var(--radius-md);
  padding: 9px 12px;
  font-size: 14px;
  font-family: var(--font-body);
  outline: none;
  background: var(--paper);
  color: var(--text);
}
.field input:focus,
.field select:focus,
.field textarea:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(91, 103, 241, 0.12);
}
.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 4px;
}
</style>
