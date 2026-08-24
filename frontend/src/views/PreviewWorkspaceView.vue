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
      <div class="actions"><button class="ghost" :disabled="rebuilding" @click="rebuild">{{ rebuilding ? "正在构建…" : "重新构建" }}</button><button class="ghost" @click="$router.push('/')">项目列表</button></div>
    </header>
    <div class="body">
      <LivePreviewPanel
        :project-id="projectId"
        stage="done"
        :refresh-token="refreshToken"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { useRoute } from "vue-router";
import LivePreviewPanel from "../components/LivePreviewPanel.vue";
import { getProject, rebuildProjectPreview } from "../api/projects";
import type { Project } from "../types";

const route = useRoute();
const projectId = Number(route.params.id);
const project = ref<Project | null>(null);
const rebuilding = ref(false);
const refreshToken = ref(0);

async function rebuild() {
  rebuilding.value = true;
  try {
    const result = await rebuildProjectPreview(projectId);
    if (!result.ok) {
      ElMessage.error(result.errors[0] || "构建失败，请查看项目源码后重试");
      return;
    }
    refreshToken.value += 1;
    ElMessage.success("构建完成，预览已刷新");
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || "重新构建失败");
  } finally {
    rebuilding.value = false;
  }
}

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
.actions { display: flex; gap: 8px; }
.ghost:disabled { opacity: .6; cursor: wait; }
.body {
  flex: 1;
  min-height: 0;
  padding: 14px;
}
</style>
