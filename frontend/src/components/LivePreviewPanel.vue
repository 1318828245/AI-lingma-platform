<template>
  <div class="preview-panel">
    <div class="head">
      <span class="panel-title">Live Preview</span>
      <span class="chip" :class="statusClass">{{ statusLabel }}</span>
      <span class="spacer" />
      <div class="seg mono">
        <button
          v-for="v in viewports"
          :key="v.key"
          class="seg-btn"
          :class="{ on: viewport === v.key }"
          :title="v.title"
          @click="viewport = v.key"
        >
          {{ v.label }}
        </button>
      </div>
      <button class="icon-btn" title="刷新预览" @click="reload">
        ⟳
      </button>
    </div>

    <div class="canvas">
      <iframe
        v-if="ready"
        :key="frameKey"
        :src="frameSrc"
        :style="{ width: frameWidth }"
        sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
        title="项目实时预览"
      />
      <div v-else-if="loading" class="empty">
        <span class="spinner" />
        <p class="eyebrow">正在检查预览状态</p>
      </div>
      <div v-else class="empty">
        <p class="empty-icon">▧</p>
        <p class="empty-title">
          {{ previewStatus?.status === "not_generated" ? "还没有可预览的构建产物" : "项目还是空的" }}
        </p>
        <p class="muted">完成一次生成后，这里会自动亮起来</p>
      </div>
    </div>

    <div class="foot mono">
      <span class="foot-stage">
        <span class="lamp" :class="{ on: running }" />
        {{ stageLabel }}
      </span>
      <span v-if="buildAttempt > 0">build #{{ buildAttempt }}</span>
      <span class="foot-url">{{ previewUrl }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { getPreviewStatus } from "../api/projects";
import { useAuthStore } from "../stores/auth";
import type { PreviewStatus } from "../types";

const props = defineProps<{
  projectId: number;
  stage?: string;
  running?: boolean;
  buildAttempt?: number;
  refreshToken?: number;
}>();

const auth = useAuthStore();
const previewStatus = ref<PreviewStatus | null>(null);
const loading = ref(true);
const viewport = ref<"desktop" | "tablet" | "mobile">("desktop");
const frameKey = ref(0);

const viewports = [
  { key: "desktop", label: "桌面", title: "桌面视口" },
  { key: "tablet", label: "平板", title: "平板视口" },
  { key: "mobile", label: "手机", title: "手机视口" },
] as const;

const ready = computed(() => previewStatus.value?.status === "ready");
const frameWidth = computed(() => {
  if (viewport.value === "mobile") return "375px";
  if (viewport.value === "tablet") return "768px";
  return "100%";
});
const frameSrc = computed(
  () =>
    `/preview/${props.projectId}/?token=${encodeURIComponent(auth.accessToken)}&t=${frameKey.value}`
);
const previewUrl = computed(
  () => `/preview/${props.projectId}/ — ${previewStatus.value?.mode ?? "…"}`
);

const statusLabel = computed(() => {
  if (loading.value) return "检测中";
  if (previewStatus.value?.status === "ready") return "可预览";
  if (previewStatus.value?.status === "not_generated") return "未生成";
  return "空项目";
});
const statusClass = computed(() => {
  if (previewStatus.value?.status === "ready") return "ok";
  if (previewStatus.value?.status === "not_generated") return "warn";
  return "";
});

const stageLabel = computed(() => props.stage || "idle");

async function checkStatus() {
  loading.value = true;
  try {
    previewStatus.value = await getPreviewStatus(props.projectId);
    if (previewStatus.value?.status === "ready") {
      frameKey.value += 1;
    }
  } finally {
    loading.value = false;
  }
}

function reload() {
  frameKey.value += 1;
}

onMounted(checkStatus);
watch(
  () => props.refreshToken,
  () => checkStatus()
);
</script>

<style scoped>
.preview-panel {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: var(--ink-900);
  border: 1px solid var(--ink-700);
  border-radius: var(--radius-lg);
  overflow: hidden;
}
.head {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  background: var(--ink-900);
  color: #cbd5e1;
}
.head .panel-title {
  color: #64748b;
}
.chip {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.08em;
  padding: 3px 10px;
  border-radius: 999px;
  border: 1px solid var(--ink-700);
  color: #94a3b8;
}
.chip.ok {
  color: #4ade80;
  border-color: rgba(74, 222, 128, 0.35);
  background: rgba(74, 222, 128, 0.08);
}
.chip.warn {
  color: var(--amber);
  border-color: rgba(245, 158, 11, 0.35);
  background: rgba(245, 158, 11, 0.08);
}
.spacer {
  flex: 1;
}
.seg {
  display: flex;
  border: 1px solid var(--ink-700);
  border-radius: 8px;
  overflow: hidden;
}
.seg-btn {
  border: none;
  background: transparent;
  color: #94a3b8;
  font-family: var(--font-mono);
  font-size: 11px;
  padding: 5px 12px;
  cursor: pointer;
}
.seg-btn + .seg-btn {
  border-left: 1px solid var(--ink-700);
}
.seg-btn.on {
  background: var(--ink-800);
  color: #f8fafc;
}
.icon-btn {
  border: 1px solid var(--ink-700);
  background: transparent;
  color: #94a3b8;
  width: 30px;
  height: 30px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 15px;
  line-height: 1;
}
.icon-btn:hover {
  color: #fff;
  background: var(--ink-800);
}
.canvas {
  flex: 1;
  min-height: 0;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  overflow: auto;
  background: #e8ebf2;
  padding: 14px;
}
.canvas iframe {
  height: 100%;
  border: none;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.35);
  transition: width 0.2s ease;
}
.empty {
  height: 100%;
  min-height: 260px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #94a3b8;
}
.empty-icon {
  font-size: 40px;
  color: var(--ink-700);
}
.empty-title {
  color: #cbd5e1;
  font-weight: 600;
}
.spinner {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 2px solid var(--ink-700);
  border-top-color: var(--amber);
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
.foot {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 8px 14px;
  background: var(--ink-950);
  color: #64748b;
  font-size: 11px;
}
.foot-stage {
  display: flex;
  align-items: center;
  gap: 7px;
  color: #cbd5e1;
}
.lamp {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--ink-700);
}
.lamp.on {
  background: var(--amber);
  box-shadow: 0 0 8px rgba(245, 158, 11, 0.8);
}
.foot-url {
  margin-left: auto;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
