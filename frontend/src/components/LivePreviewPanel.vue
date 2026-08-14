<template>
  <div class="preview-panel">
    <div class="head">
      <span class="panel-title">实时预览</span>
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
      <button class="icon-btn" title="重新加载预览" @click="reload">
        <span aria-hidden="true">⟳</span>
        刷新
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
        <p class="muted">正在查看预览状态…</p>
      </div>
      <div v-else class="empty">
        <p class="empty-icon" aria-hidden="true">✦</p>
        <p class="empty-title">
          {{
            previewStatus?.status === "not_generated"
              ? "这里会显示你生成的页面"
              : "项目还是空的"
          }}
        </p>
        <p class="muted">在左侧描述需求，完成后预览会自动亮起来</p>
      </div>
    </div>

    <div class="foot mono">
      <span class="foot-stage">
        <span class="lamp" :class="{ on: running }" />
        {{ stageLabel }}
      </span>
      <span v-if="buildAttempt > 0">构建 #{{ buildAttempt }}</span>
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
  () => `/preview/${props.projectId}/ · ${previewStatus.value?.mode ?? "…"}`
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
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  overflow: hidden;
}
.head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: var(--paper);
  border-bottom: 1px solid var(--line);
}
.head .panel-title {
  color: var(--muted);
}
.chip {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.06em;
  padding: 3px 10px;
  border-radius: 999px;
  border: 1px solid var(--line-strong);
  color: var(--muted);
  background: var(--canvas);
}
.chip.ok {
  color: var(--green);
  border-color: rgba(47, 158, 111, 0.35);
  background: var(--green-soft);
}
.chip.warn {
  color: #b97f1c;
  border-color: rgba(242, 169, 59, 0.4);
  background: var(--amber-soft);
}
.spacer {
  flex: 1;
}
.seg {
  display: flex;
  border: 1px solid var(--line-strong);
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: var(--canvas);
}
.seg-btn {
  border: none;
  background: transparent;
  color: var(--muted);
  font-family: var(--font-mono);
  font-size: 11px;
  padding: 5px 12px;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.seg-btn + .seg-btn {
  border-left: 1px solid var(--line-strong);
}
.seg-btn.on {
  background: var(--paper);
  color: var(--primary);
  font-weight: 500;
}
.icon-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  border: 1px solid var(--line-strong);
  background: var(--paper);
  color: var(--muted);
  padding: 5px 10px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 12px;
  transition: color 0.15s, border-color 0.15s, background 0.15s;
}
.icon-btn:hover {
  color: var(--primary);
  border-color: var(--primary);
  background: var(--primary-soft);
}
.canvas {
  flex: 1;
  min-height: 0;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  overflow: auto;
  background:
    radial-gradient(circle at 20% 20%, rgba(91, 103, 241, 0.05), transparent 45%),
    var(--canvas-deep);
  padding: 14px;
}
.canvas iframe {
  height: 100%;
  border: none;
  border-radius: var(--radius-md);
  background: var(--paper);
  box-shadow: 0 8px 28px rgba(60, 52, 42, 0.18);
  transition: width 0.2s ease;
}
.empty {
  height: 100%;
  min-height: 240px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  text-align: center;
  padding: 20px;
}
.empty-icon {
  font-size: 34px;
  color: var(--primary);
  opacity: 0.55;
}
.empty-title {
  color: var(--ink);
  font-weight: 600;
  font-size: 15px;
}
.spinner {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  border: 2px solid var(--line-strong);
  border-top-color: var(--primary);
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
  gap: 14px;
  padding: 8px 14px;
  background: var(--canvas);
  border-top: 1px solid var(--line);
  color: var(--muted);
  font-size: 11px;
}
.foot-stage {
  display: flex;
  align-items: center;
  gap: 7px;
  color: var(--ink);
}
.lamp {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--line-strong);
}
.lamp.on {
  background: var(--amber);
  box-shadow: 0 0 8px rgba(242, 169, 59, 0.85);
}
.foot-url {
  margin-left: auto;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
