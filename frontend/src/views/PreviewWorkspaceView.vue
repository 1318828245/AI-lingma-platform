<template>
  <div class="preview-page">
    <header class="toolbar">
      <div class="left">
        <el-button link @click="$router.push(`/projects/${projectId}`)">
          ← 生成对话
        </el-button>
        <span class="title">{{ project?.name || "实时预览" }}</span>
        <el-tag size="small" :type="statusTagType">
          {{ statusText }}
        </el-tag>
      </div>
      <div class="right">
        <el-radio-group v-model="viewport" size="small">
          <el-radio-button value="desktop">桌面</el-radio-button>
          <el-radio-button value="tablet">平板</el-radio-button>
          <el-radio-button value="mobile">手机</el-radio-button>
        </el-radio-group>
        <el-button size="small" :disabled="!ready" @click="refresh">
          刷新预览
        </el-button>
      </div>
    </header>

    <div v-if="ready" class="frame-wrap" :class="viewport">
      <PreviewFrame :src="frameSrc" :width="frameWidth" />
    </div>
    <el-empty v-else-if="status?.status === 'not_generated'" description="项目尚未生成/构建">
      <el-button type="primary" @click="$router.push(`/projects/${projectId}`)">
        回到生成页完成生成
      </el-button>
    </el-empty>
    <el-empty v-else description="项目为空，请先创建内容" />

    <div class="hint muted">
      说明：预览为服务端代理 + iframe 沙箱隔离；点选元素修改（ElementPicker）将在 M2 里程碑实现。
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import PreviewFrame from "../components/PreviewFrame.vue";
import { getPreviewStatus, getProject } from "../api/projects";
import { useAuthStore } from "../stores/auth";
import type { PreviewStatus, Project } from "../types";

const route = useRoute();
const auth = useAuthStore();
const projectId = Number(route.params.id);

const project = ref<Project | null>(null);
const status = ref<PreviewStatus | null>(null);
const viewport = ref<"desktop" | "tablet" | "mobile">("desktop");
const refreshKey = ref(0);

const ready = computed(() => status.value?.status === "ready");
const frameWidth = computed(() => {
  if (viewport.value === "mobile") return "375px";
  if (viewport.value === "tablet") return "768px";
  return "100%";
});
const frameSrc = computed(
  () =>
    `/preview/${projectId}/?token=${encodeURIComponent(auth.accessToken)}&t=${refreshKey.value}`
);
const statusText = computed(() => {
  if (status.value?.status === "ready") return "可预览";
  if (status.value?.status === "not_generated") return "未生成";
  return "空项目";
});
const statusTagType = computed(() =>
  status.value?.status === "ready" ? "success" : "info"
);

onMounted(async () => {
  project.value = await getProject(projectId);
  status.value = await getPreviewStatus(projectId);
});

function refresh() {
  refreshKey.value += 1;
}
</script>

<style scoped>
.preview-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #0f172a;
}
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
  z-index: 10;
}
.left,
.right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.title {
  font-weight: 600;
}
.frame-wrap {
  flex: 1;
  display: flex;
  justify-content: center;
  padding: 16px;
  overflow: auto;
  transition: width 0.2s;
}
.frame-wrap iframe {
  border-radius: 8px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4);
  height: 100%;
}
.hint {
  padding: 8px 16px;
  text-align: center;
  color: #64748b;
  background: #1e293b;
}
</style>
