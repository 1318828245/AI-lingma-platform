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
      <div class="qc-head">
        <span class="qc-icon" aria-hidden="true">✦</span>
        <div>
          <p class="panel-title">快速生成项目</p>
          <p class="qc-sub">输入提示词并选择技术栈，一键生成并进入</p>
        </div>
      </div>

      <div class="qc-form">
        <div class="qc-field qc-name">
          <span class="mono qc-label">生成提示词</span>
          <div class="qc-input-wrap">
            <textarea
              v-model="quickPrompt"
              rows="4"
              placeholder="例如：做一个深色风格的个人名片页，展示技能与作品"
              @keydown.enter.exact.prevent="quickCreate"
            />
          </div>
        </div>

        <div class="qc-field qc-stack">
          <span class="mono qc-label">技术栈</span>
          <div class="seg">
            <button
              v-for="s in stacks"
              :key="s.value"
              class="seg-btn"
              :class="{ on: quickStack === s.value }"
              @click="quickStack = s.value"
            >
              {{ s.label }}
            </button>
          </div>
        </div>

        <div class="qc-actions">
          <button class="btn primary qc-submit" @click="quickCreate">
            生成项目
          </button>
        </div>
      </div>

      <div class="qc-templates">
        <p class="mono qc-label">提示词模板</p>
        <button
          v-for="tpl in quickTemplates"
          :key="tpl"
          class="template"
          :title="`使用模板：${tpl}`"
          @click="quickPrompt = tpl"
        >
          <span class="tpl-mark" aria-hidden="true">✦</span>
          <span class="tpl-text">{{ tpl }}</span>
          <span class="tpl-arrow" aria-hidden="true">→</span>
        </button>
      </div>
    </section>

    <div v-if="projects.length" class="grid">
      <article
        v-for="p in projects"
        :key="p.id"
        class="panel project-card"
        :data-project-id="p.id"
        :ref="(element) => observeProjectCard(p.id, element as Element | null)"
        role="button"
        tabindex="0"
        @click="openGeneration(p)"
        @keydown.enter="openGeneration(p)"
      >
        <div class="thumb">
          <img
            v-if="thumbRequested[p.id]"
            class="thumb-img"
            :class="{ visible: thumbState[p.id] === 'ok' }"
            :src="thumbSrc(p)"
            :alt="`${p.name} 截图`"
            @load="thumbState[p.id] = 'ok'"
            @error="thumbError(p)"
          />
          <div v-if="thumbState[p.id] !== 'ok'" class="thumb-default">
            <span class="thumb-icon" aria-hidden="true">▧</span>
            <span v-if="thumbState[p.id] === 'error'" class="thumb-text">
              暂无截图
            </span>
            <span v-else class="thumb-text">
              {{ thumbState[p.id] === "loading" ? "正在生成截图…" : "尚未生成" }}
            </span>
            <button
              v-if="thumbState[p.id] === 'error'"
              class="btn ghost sm retry-btn"
              @click.stop="retryThumb(p)"
            >
              重试截图
            </button>
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
import { onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { createProject, deleteProject, listProjects } from "../api/projects";
import { useAuthStore } from "../stores/auth";
import type { Project } from "../types";

const router = useRouter();
const auth = useAuthStore();
const projects = ref<Project[]>([]);
const quickPrompt = ref("");
const quickStack = ref<"html" | "vue3">("html");
const stacks = [
  { value: "html", label: "HTML" },
  { value: "vue3", label: "Vue 3" },
] as const;
const quickTemplates = [
  "做一个深色风格的个人名片页",
  "做一个三列任务看板，支持增删移",
  "做一个商品管理表格页，带搜索筛选",
];
const thumbState = ref<Record<number, "loading" | "ok" | "error">>({});
const thumbRequested = ref<Record<number, boolean>>({});
const thumbVersions = ref<Record<number, number>>({});
const thumbForced = ref<Record<number, boolean>>({});
let thumbnailObserver: IntersectionObserver | undefined;

function thumbSrc(p: Project) {
  return `/api/projects/${p.id}/screenshot?token=${encodeURIComponent(
    auth.accessToken
  )}&t=${thumbVersions.value[p.id] || 0}${thumbForced.value[p.id] ? "&force=1" : ""}`;
}

function thumbError(p: Project) {
  thumbState.value[p.id] = "error";
}

function retryThumb(p: Project) {
  thumbForced.value[p.id] = true;
  thumbVersions.value[p.id] = (thumbVersions.value[p.id] || 0) + 1;
  thumbState.value[p.id] = "loading";
}

function requestThumb(projectId: number) {
  if (thumbRequested.value[projectId]) return;
  thumbRequested.value[projectId] = true;
  thumbState.value[projectId] = "loading";
}

function observeProjectCard(projectId: number, element: Element | null) {
  if (!element || thumbRequested.value[projectId]) return;
  if (!thumbnailObserver) {
    requestThumb(projectId);
    return;
  }
  thumbnailObserver.observe(element);
}

onMounted(async () => {
  if ("IntersectionObserver" in window) {
    thumbnailObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          const projectId = Number((entry.target as HTMLElement).dataset.projectId);
          if (Number.isFinite(projectId)) requestThumb(projectId);
          thumbnailObserver?.unobserve(entry.target);
        });
      },
      { rootMargin: "320px 0px" }
    );
  }
  projects.value = await listProjects();
});

onBeforeUnmount(() => thumbnailObserver?.disconnect());

async function quickCreate() {
  const prompt = quickPrompt.value.trim();
  if (!prompt) {
    ElMessage.warning("先输入你要生成的提示词");
    return;
  }
  try {
    const name = prompt.split(/\n/)[0].trim().slice(0, 24) || "未命名项目";
    const project = await createProject({
      name,
      template: "blank",
      tech_stack: quickStack.value,
    });
    ElMessage.success("项目创建成功");
    projects.value.unshift(project);
    quickPrompt.value = "";
    router.push({
      path: `/projects/${project.id}`,
      query: { requirement: prompt, auto: "1" },
    });
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
  max-width: 1440px;
  padding: 28px 40px 40px;
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
  width: 100%;
  margin: 0 auto 28px;
  padding: 28px 32px 24px;
  min-height: 320px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  border-top: 3px solid var(--amber);
  box-shadow: var(--shadow-md);
}
.qc-head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 18px;
}
.qc-icon {
  width: 38px;
  height: 38px;
  border-radius: 12px;
  background: var(--amber-soft);
  color: #b97f1c;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 17px;
  flex-shrink: 0;
}
.qc-sub {
  color: var(--muted);
  font-size: 12px;
  margin-top: 3px;
}
.qc-field {
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.qc-form {
  display: flex;
  align-items: flex-end;
  gap: 16px;
}
.qc-name {
  flex: 1;
  min-width: 0;
}
.qc-stack {
  flex-shrink: 0;
}
.qc-actions {
  flex-shrink: 0;
}
.qc-label {
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--muted);
}
.qc-input-wrap textarea {
  width: 100%;
  min-height: 120px;
  border: 1px solid var(--line-strong);
  border-radius: var(--radius-md);
  padding: 14px 16px;
  font-size: 15px;
  line-height: 1.6;
  background: var(--paper);
  color: var(--ink);
  outline: none;
  resize: none;
  overflow-y: auto;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.qc-input-wrap textarea:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(91, 103, 241, 0.12);
}
.seg {
  display: inline-flex;
  border: 1px solid var(--line-strong);
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: var(--canvas);
  align-self: flex-start;
}
.seg-btn {
  border: none;
  background: transparent;
  color: var(--muted);
  font-size: 13px;
  padding: 12px 24px;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.seg-btn + .seg-btn {
  border-left: 1px solid var(--line-strong);
}
.seg-btn.on {
  background: var(--paper);
  color: var(--primary);
  font-weight: 600;
}
.qc-submit {
  height: 48px;
  font-size: 14px;
  white-space: nowrap;
}
.qc-templates {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 18px;
}
.template {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  text-align: left;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  background: var(--paper);
  color: var(--muted);
  padding: 10px 12px;
  font-size: 13px;
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s, background 0.15s, transform 0.15s;
}
.template:hover {
  color: var(--primary-dark);
  border-color: var(--primary);
  background: var(--primary-soft);
  transform: translateX(2px);
}
.tpl-mark {
  color: var(--amber);
  font-size: 12px;
  flex-shrink: 0;
}
.tpl-text {
  flex: 1;
}
.tpl-arrow {
  color: var(--faint);
  font-size: 13px;
  flex-shrink: 0;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
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
.retry-btn {
  margin-top: 8px;
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

@media (max-width: 720px) {
  .qc-form {
    flex-direction: column;
    align-items: stretch;
  }
  .qc-submit {
    width: 100%;
  }
}
</style>
