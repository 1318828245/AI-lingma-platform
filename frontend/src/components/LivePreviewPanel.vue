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
      <button
        class="picker-btn"
        :class="{ active: pickerEnabled }"
        :disabled="!ready"
        title="在预览中点选元素进行修改"
        @click="togglePicker"
      >
        {{ pickerEnabled ? "退出点选" : "点选修改" }}
      </button>
    </div>

    <div class="canvas">
      <iframe
        v-if="ready"
        :key="frameKey"
        ref="frameRef"
        :src="frameSrc"
        :style="{ width: frameWidth }"
        sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
        title="项目实时预览"
        @load="onFrameLoad"
      />
      <div v-if="running" class="preview-state generating" role="status">
        <span class="spinner" />
        <p class="empty-title">{{ runningTitle }}</p>
        <p class="muted">{{ runningHint }}</p>
      </div>
      <div v-else-if="ready && frameLoading" class="preview-state loading-frame" role="status">
        <span class="spinner" />
        <p class="empty-title">正在加载预览</p>
        <p class="muted">大型 Vue 工程首次加载需要下载和初始化脚本</p>
      </div>
      <div v-else-if="!ready && error" class="empty error-state">
        <p class="empty-icon" aria-hidden="true">!</p>
        <p class="empty-title">预览暂不可用</p>
        <p class="muted">{{ error }}</p>
      </div>
      <div v-else-if="!ready && loading" class="empty">
        <span class="spinner" />
        <p class="muted">正在查看预览状态…</p>
      </div>
      <div v-else-if="!ready" class="empty">
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
      <slot
        name="overlay"
        :style="selectionPopupStyle.style"
        :placement="selectionPopupStyle.placement"
      />
    </div>
    <div v-if="pickerEnabled" class="picker-tip">
      点选预览中的元素，左侧修改面板会显示元素信息和修改输入框。按按钮可退出点选。
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
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { getPreviewStatus } from "../api/projects";
import { useAuthStore } from "../stores/auth";
import type { ElementSnapshot, PreviewStatus } from "../types";

const emit = defineEmits<{
  (event: "element-selected", snapshot: ElementSnapshot): void;
  (event: "picker-toggled", enabled: boolean): void;
}>();

const props = withDefaults(
  defineProps<{
  projectId: number;
  stage?: string;
  running?: boolean;
  error?: string;
  buildAttempt?: number;
  refreshToken?: number;
  selectedElement?: ElementSnapshot | null;
}>(),
  {
    stage: "idle",
    running: false,
    error: "",
    buildAttempt: 0,
    refreshToken: 0,
    selectedElement: null,
  }
);

const auth = useAuthStore();
const previewStatus = ref<PreviewStatus | null>(null);
const loading = ref(true);
const viewport = ref<"desktop" | "tablet" | "mobile">("desktop");
const frameKey = ref(0);
const frameLoading = ref(false);
const frameRef = ref<HTMLIFrameElement | null>(null);
const pickerEnabled = ref(false);
let pickerCleanup: (() => void) | null = null;

const viewports = [
  { key: "desktop", label: "桌面", title: "桌面视口" },
  { key: "tablet", label: "平板", title: "平板视口" },
  { key: "mobile", label: "手机", title: "手机视口" },
] as const;

const ready = computed(() => previewStatus.value?.status === "ready");
const frameWidth = computed(() => {
  if (viewport.value === "mobile") return "min(100%, 420px)";
  if (viewport.value === "tablet") return "min(100%, 820px)";
  return "100%";
});
const frameSrc = computed(
  () =>
    `/preview/${props.projectId}/?t=${frameKey.value}`
);
const selectionPopupStyle = computed(() => {
  const selected = props.selectedElement;
  const frame = frameRef.value;
  const canvas = frame?.parentElement;
  if (!selected || !frame || !canvas) {
    return { style: { display: "none" }, placement: "right" as const };
  }
  const frameRect = frame.getBoundingClientRect();
  const canvasRect = canvas.getBoundingClientRect();
  const elementRect = selected.rect;
  const edge = 12;
  const gap = 14;
  const popupWidth = Math.min(350, Math.max(0, canvasRect.width - edge * 2));
  // The panel is content-sized, so use a conservative height for direction
  // selection and cap the actual panel height in GenerationChatView.
  const popupHeight = Math.min(320, Math.max(0, canvasRect.height - edge * 2));
  const anchor = {
    left: frameRect.left - canvasRect.left + elementRect.x,
    top: frameRect.top - canvasRect.top + elementRect.y,
  };
  anchor.left = Math.max(edge, Math.min(anchor.left, canvasRect.width - edge));
  anchor.top = Math.max(edge, Math.min(anchor.top, canvasRect.height - edge));
  const anchorRight = anchor.left + elementRect.width;
  const anchorBottom = anchor.top + elementRect.height;
  const spaces = {
    right: canvasRect.width - anchorRight - gap - edge,
    left: anchor.left - gap - edge,
    bottom: canvasRect.height - anchorBottom - gap - edge,
    top: anchor.top - gap - edge,
  };
  const preferred = ["right", "left", "bottom", "top"] as const;
  const placement = preferred.find((side) =>
    side === "right" || side === "left"
      ? spaces[side] >= popupWidth
      : spaces[side] >= popupHeight
  ) ?? preferred.reduce((best, side) =>
    spaces[side] > spaces[best] ? side : best
  );

  let left = anchor.left;
  let top = anchor.top;
  if (placement === "right") {
    left = anchorRight + gap;
    top = anchor.top + elementRect.height / 2 - popupHeight / 2;
  } else if (placement === "left") {
    left = anchor.left - popupWidth - gap;
    top = anchor.top + elementRect.height / 2 - popupHeight / 2;
  } else if (placement === "bottom") {
    left = anchor.left + elementRect.width / 2 - popupWidth / 2;
    top = anchorBottom + gap;
  } else {
    left = anchor.left + elementRect.width / 2 - popupWidth / 2;
    top = anchor.top - popupHeight - gap;
  }
  const maxLeft = Math.max(edge, canvasRect.width - popupWidth - edge);
  const maxTop = Math.max(edge, canvasRect.height - popupHeight - edge);
  left = Math.max(edge, Math.min(left, maxLeft));
  top = Math.max(edge, Math.min(top, maxTop));
  return {
    style: { left: `${left}px`, top: `${top}px`, width: `${popupWidth}px` },
    placement,
  };
});
const previewUrl = computed(
  () => `/preview/${props.projectId}/ · ${previewStatus.value?.mode ?? "…"}`
);

const statusLabel = computed(() => {
  if (props.error) return "预览失败";
  if (props.running) return "生成中";
  if (loading.value) return "检测中";
  if (previewStatus.value?.status === "ready") return "可预览";
  if (previewStatus.value?.status === "not_generated") return "未生成";
  return "空项目";
});
const statusClass = computed(() => {
  if (props.error) return "error";
  if (props.running) return "warn";
  if (previewStatus.value?.status === "ready") return "ok";
  if (previewStatus.value?.status === "not_generated") return "warn";
  return "";
});

const stageLabel = computed(() => props.stage || "idle");
const runningTitle = computed(() =>
  props.stage === "locate" || props.stage === "edit" ? "正在更新预览" : "正在生成预览"
);
const runningHint = computed(() =>
  props.stage === "locate" || props.stage === "edit"
    ? "修改完成并更新构建产物后会自动刷新"
    : "页面代码与构建产物完成后会自动刷新"
);

async function checkStatus() {
  loading.value = true;
  try {
    previewStatus.value = await getPreviewStatus(props.projectId);
    if (previewStatus.value?.status === "ready") {
      frameLoading.value = true;
      frameKey.value += 1;
    }
  } finally {
    loading.value = false;
  }
}

function ensurePreviewCookie() {
  if (!auth.accessToken) return;
  document.cookie =
    `preview_token=${encodeURIComponent(auth.accessToken)}; path=/preview; max-age=86400; samesite=lax`;
}

function reload() {
  pickerCleanup?.();
  pickerCleanup = null;
  frameLoading.value = true;
  frameKey.value += 1;
}

function selectorFor(element: Element): string {
  const htmlElement = element as HTMLElement;
  if (htmlElement.id) return `#${CSS.escape(htmlElement.id)}`;
  const parts: string[] = [];
  let current: Element | null = element;
  while (current && current.nodeType === 1 && parts.length < 6) {
    let part = current.tagName.toLowerCase();
    if (current.classList.length) {
      part += `.${Array.from(current.classList).slice(0, 2).map((name) => CSS.escape(name)).join(".")}`;
    }
    const parent: HTMLElement | null = current.parentElement;
    if (parent) {
      const same = Array.from(parent.children).filter((child) => child.tagName === current?.tagName);
      if (same.length > 1) part += `:nth-of-type(${same.indexOf(current) + 1})`;
    }
    parts.unshift(part);
    current = parent;
  }
  return parts.join(" > ");
}

function snapshotElement(element: Element): ElementSnapshot {
  const html = element.outerHTML.slice(0, 2000);
  const rect = element.getBoundingClientRect();
  const htmlElement = element as HTMLElement;
  return {
    tag: element.tagName.toLowerCase(),
    text: (element.textContent || "").trim().replace(/\s+/g, " ").slice(0, 500),
    id: htmlElement.id || "",
    className: typeof htmlElement.className === "string" ? htmlElement.className : "",
    selector: selectorFor(element),
    html,
    rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
  };
}

function installPicker() {
  pickerCleanup?.();
  const doc = frameRef.value?.contentDocument;
  if (!pickerEnabled.value || !doc?.body) return;
  let hovered: HTMLElement | null = null;
  let selected: HTMLElement | null = null;
  const clearOutline = (element: HTMLElement | null) => {
    if (!element) return;
    element.style.removeProperty("outline");
    element.style.removeProperty("outline-offset");
  };
  const outline = (element: HTMLElement | null, color: string) => {
    if (!element) return;
    element.style.setProperty("outline", `2px solid ${color}`, "important");
    element.style.setProperty("outline-offset", "2px", "important");
  };
  const onMove = (event: MouseEvent) => {
    const target = event.target;
    if (!target || (target as Node).nodeType !== 1 || target === doc.body || target === doc.documentElement) return;
    const element = target as HTMLElement;
    if (hovered !== element) {
      if (hovered !== selected) clearOutline(hovered);
      hovered = element;
      outline(hovered, "#5264d8");
    }
  };
  const onClick = (event: MouseEvent) => {
    const target = event.target;
    if (!target || (target as Node).nodeType !== 1 || target === doc.body || target === doc.documentElement) return;
    const element = target as HTMLElement;
    event.preventDefault();
    event.stopPropagation();
    if (selected && selected !== element) clearOutline(selected);
    selected = element;
    outline(selected, "#d89132");
    emit("element-selected", snapshotElement(element));
  };
  doc.addEventListener("mousemove", onMove, true);
  doc.addEventListener("click", onClick, true);
  pickerCleanup = () => {
    doc.removeEventListener("mousemove", onMove, true);
    doc.removeEventListener("click", onClick, true);
    clearOutline(hovered);
    clearOutline(selected);
  };
}

function togglePicker() {
  pickerEnabled.value = !pickerEnabled.value;
  installPicker();
  emit("picker-toggled", pickerEnabled.value);
}

function onFrameLoad() {
  frameLoading.value = false;
  if (pickerEnabled.value) installPicker();
}

onMounted(() => {
  ensurePreviewCookie();
  checkStatus();
});
onBeforeUnmount(() => pickerCleanup?.());
watch(
  () => auth.accessToken,
  () => ensurePreviewCookie()
);
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
.picker-btn {
  border: 1px solid rgba(82, 100, 216, 0.35);
  background: var(--primary-soft);
  color: var(--primary-dark);
  padding: 5px 10px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 12px;
}
.picker-btn:hover,
.picker-btn.active {
  background: var(--primary);
  color: #fff;
}
.picker-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.canvas {
  position: relative;
  flex: 1;
  min-height: 0;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  overflow: auto;
  background:
    radial-gradient(circle at 20% 20%, rgba(91, 103, 241, 0.05), transparent 45%),
    var(--canvas-deep);
  padding: 8px;
}
.picker-tip {
  padding: 7px 14px;
  background: var(--primary-soft);
  color: var(--primary-dark);
  border-top: 1px solid var(--line);
  font-size: 12px;
}
.canvas iframe {
  height: 100%;
  max-width: 100%;
  min-width: 0;
  border: none;
  border-radius: var(--radius-md);
  background: var(--paper);
  box-shadow: 0 8px 28px rgba(60, 52, 42, 0.18);
  transition: width 0.2s ease;
}
.preview-state {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 20px;
  text-align: center;
  background: color-mix(in srgb, var(--canvas-deep) 74%, transparent);
}
.preview-state.generating {
  backdrop-filter: blur(2px);
}
.preview-state.loading-frame {
  background: color-mix(in srgb, var(--canvas-deep) 64%, transparent);
}
.error-state {
  color: #a13a3a;
}
.error-state .empty-icon {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border: 1px solid rgba(224, 91, 91, .4);
  border-radius: 50%;
  background: var(--red-soft);
  color: var(--red);
  font-weight: 700;
}
.chip.error {
  color: var(--red);
  border-color: rgba(224, 91, 91, .35);
  background: var(--red-soft);
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
