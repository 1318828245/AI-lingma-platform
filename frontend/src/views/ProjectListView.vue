<template>
  <div class="page home-page">
    <header class="home-header">
      <div class="brand">
        <p class="eyebrow">AI · Lingma Studio</p>
        <h1 class="wordmark brand-name">AI 灵码平台</h1>
        <p class="brand-slogan">说一句需求，看页面长出来</p>
      </div>
      <div class="head-actions">
        <span class="mono user-chip">{{ auth.user?.username }}</span>
        <button class="btn ghost" @click="logout">退出</button>
      </div>
    </header>

    <section class="panel quick-create">
      <p class="panel-title">快速创建项目</p>
      <div class="quick-row">
        <input
          v-model="quickName"
          placeholder="输入项目名称，例如：我的名片"
          @keyup.enter="quickCreate"
        />
        <select v-model="quickStack" title="技术栈">
          <option value="html">HTML</option>
          <option value="vue3">Vue 3</option>
        </select>
        <button class="btn primary" @click="quickCreate">创建项目</button>
      </div>
      <div class="templates">
        <button
          v-for="tpl in quickTemplates"
          :key="tpl"
          class="template"
          :title="`使用模板：${tpl}`"
          @click="quickName = tpl"
        >
          {{ tpl }}
        </button>
      </div>
    </section>

    <div v-if="projects.length" class="grid">
      <article
        v-for="p in projects"
        :key="p.id"
        class="panel project-card"
        role="button"
        tabindex="0"
        @click="openGeneration(p)"
        @keydown.enter="openGeneration(p)"
      >
        <div class="thumb">
          <img
            class="thumb-img"
            :class="{ visible: thumbState[p.id] === 'ok' }"
            :src="thumbSrc(p)"
            :alt="`${p.name} 截图`"
            loading="lazy"
            @load="thumbState[p.id] = 'ok'"
            @error="thumbState[p.id] = 'error'"
          />
          <div v-if="thumbState[p.id] !== 'ok'" class="thumb-default">
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
          <p class="card-desc">{{ p.description || "点击卡片进入，开始生成" }}</p>
          <p class="mono card-meta">
            {{ p.template }} · {{ p.status }}
          </p>
          <div class="card-actions" @click.stop>
            <button class="btn ghost sm" @click="openPreview(p)">预览</button>
            <button class="btn danger sm" @click="remove(p)">删除</button>
          </div>
        </div>
      </article>
    </div>
    <div v-else class="panel empty-state">
      <p class="empty-mark" aria-hidden="true">▧</p>
      <p class="empty-title">还没有项目</p>
      <p class="muted">在上方输入名称，或用下面的模板快速创建一个</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { createProject, deleteProject, listProjects } from "../api/projects";
import { useAuthStore } from "../stores/auth";
import type { Project } from "../types";

const router = useRouter();
const auth = useAuthStore();
const projects = ref<Project[]>([]);
const quickName = ref("");
const quickStack = ref<"html" | "vue3">("html");
const quickTemplates = [
  "做一个深色风格的个人名片页",
  "做一个三列任务看板，支持增删移",
  "做一个商品管理表格页，带搜索筛选",
];
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
});

async function quickCreate() {
  const name = quickName.value.trim();
  if (!name) {
    ElMessage.warning("先给项目起个名字");
    return;
  }
  try {
    const project = await createProject({
      name,
      template: "blank",
      tech_stack: quickStack.value,
    });
    ElMessage.success("项目创建成功");
    projects.value.unshift(project);
    quickName.value = "";
    router.push(`/projects/${project.id}`);
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || "创建失败");
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
.home-page {
  max-width: 1080px;
}
.home-header {
  position: relative;
  text-align: center;
  margin-bottom: 24px;
}
.brand .eyebrow {
  color: var(--amber);
  margin-bottom: 4px;
}
.brand-name {
  font-size: 38px;
  letter-spacing: 0.04em;
}
.brand-slogan {
  color: var(--muted);
  font-size: 14px;
  margin-top: 6px;
}
.head-actions {
  position: absolute;
  top: 0;
  right: 0;
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
.quick-create {
  max-width: 640px;
  margin: 0 auto 28px;
  padding: 18px 20px;
  border-top: 3px solid var(--amber);
  box-shadow: var(--shadow-md);
}
.quick-row {
  display: flex;
  gap: 10px;
  margin-top: 12px;
}
.quick-row input {
  flex: 1;
  height: 40px;
  border: 1px solid var(--line-strong);
  border-radius: var(--radius-md);
  padding: 0 12px;
  font-size: 14px;
  outline: none;
  background: var(--paper);
}
.quick-row input:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(91, 103, 241, 0.12);
}
.quick-row select {
  height: 40px;
  border: 1px solid var(--line-strong);
  border-radius: var(--radius-md);
  padding: 0 10px;
  font-size: 14px;
  background: var(--paper);
  color: var(--ink);
}
.templates {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 14px;
}
.template {
  text-align: left;
  border: 1px dashed var(--line-strong);
  border-radius: var(--radius-sm);
  background: var(--canvas);
  color: var(--muted);
  padding: 8px 12px;
  font-size: 13px;
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s, background 0.15s;
}
.template:hover {
  color: var(--primary-dark);
  border-color: var(--primary);
  background: var(--primary-soft);
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}
.project-card {
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.15s, border-color 0.15s;
}
.project-card:hover,
.project-card:focus-visible {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
  border-color: var(--line-strong);
}
.thumb {
  position: relative;
  height: 150px;
  background:
    radial-gradient(circle at 20% 20%, rgba(91, 103, 241, 0.06), transparent 45%),
    var(--canvas-deep);
  border-bottom: 1px solid var(--line);
  overflow: hidden;
}
.thumb-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: top;
  display: block;
  opacity: 0;
}
.thumb-img.visible {
  opacity: 1;
}
.thumb-default {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: var(--faint);
  padding: 16px;
  background:
    radial-gradient(circle at 20% 20%, rgba(91, 103, 241, 0.06), transparent 45%),
    var(--canvas-deep);
}
.thumb-icon {
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
</style>
