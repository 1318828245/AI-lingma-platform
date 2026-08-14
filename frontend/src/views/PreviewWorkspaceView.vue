<template>
  <div class="full-preview">
    <header class="bar">
      <div class="left">
        <button class="back" @click="$router.push(`/projects/${projectId}`)">←</button>
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
  background: var(--ink-950);
}
.bar {
  height: 54px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  background: var(--ink-900);
  color: #e7ecf5;
  flex-shrink: 0;
}
.bar .eyebrow {
  color: #64748b;
}
.left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.back {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: 1px solid var(--ink-700);
  background: transparent;
  color: #cbd5e1;
  cursor: pointer;
}
.back:hover {
  background: var(--ink-800);
}
.name {
  font-size: 15px;
}
.ghost {
  border: 1px solid var(--ink-700);
  background: transparent;
  color: #cbd5e1;
  border-radius: 8px;
  padding: 6px 12px;
  font-size: 12px;
  cursor: pointer;
}
.ghost:hover {
  background: var(--ink-800);
  color: #fff;
}
.body {
  flex: 1;
  min-height: 0;
  padding: 14px;
}
</style>
