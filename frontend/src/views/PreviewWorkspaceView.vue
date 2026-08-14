<template>
  <div class="full-preview">
    <header class="bar">
      <div class="left">
        <button class="back" title="返回生成对话" @click="$router.push(`/projects/${projectId}`)">
          ←
        </button>
        <span class="eyebrow">AI · Lingma Studio</span>
        <span class="name wordmark">{{ project?.name || "实时预览" }}</span>
      </div>
      <button class="ghost" @click="$router.push('/')">项目列表</button>
    </header>
    <div class="body">
      <LivePreviewPanel
        :project-id="projectId"
        stage="done"
        :refresh-token="0"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import LivePreviewPanel from "../components/LivePreviewPanel.vue";
import { getProject } from "../api/projects";
import type { Project } from "../types";

const route = useRoute();
const projectId = Number(route.params.id);
const project = ref<Project | null>(null);

onMounted(async () => {
  project.value = await getProject(projectId);
});
</script>

<style scoped>
.full-preview {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--canvas);
}
.bar {
  height: 54px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  background: var(--paper);
  border-bottom: 1px solid var(--line);
  flex-shrink: 0;
}
.bar .eyebrow {
  color: var(--amber);
}
.left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.back {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--line-strong);
  background: var(--paper);
  color: var(--muted);
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s, background 0.15s;
}
.back:hover {
  color: var(--primary);
  border-color: var(--primary);
  background: var(--primary-soft);
}
.name {
  font-size: 15px;
}
.ghost {
  border: 1px solid var(--line-strong);
  background: var(--paper);
  color: var(--ink);
  border-radius: var(--radius-sm);
  padding: 6px 12px;
  font-size: 12px;
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s, background 0.15s;
}
.ghost:hover {
  color: var(--primary);
  border-color: var(--primary);
  background: var(--primary-soft);
}
.body {
  flex: 1;
  min-height: 0;
  padding: 14px;
}
</style>
