<template>
  <section class="modify-panel" :class="{ empty: !element }">
    <div class="modify-head">
      <div>
        <p class="eyebrow mono">M2 / ELEMENT EDIT</p>
        <h2>点选修改</h2>
      </div>
      <span v-if="element" class="tag mono">{{ element.tag }}</span>
    </div>

    <template v-if="element">
      <div class="selected-element">
        <span class="selection-dot" />
        <div class="selection-copy">
          <strong>{{ element.text || "无文本元素" }}</strong>
          <span class="mono">{{ element.selector }}</span>
        </div>
      </div>
      <el-input
        v-model="instruction"
        type="textarea"
        :rows="2"
        :disabled="busy"
        placeholder="例如：把标题改成新品发布"
        @keydown.enter.exact.prevent="submit"
      />
      <div class="modify-actions">
        <span v-if="statusText" class="status mono">{{ statusText }}</span>
        <span v-else class="hint">当前版本支持明确的文本替换</span>
        <el-button type="primary" :loading="busy" :disabled="!instruction.trim()" @click="submit">
          应用修改
        </el-button>
      </div>
    </template>
    <p v-else class="empty-copy">点击右侧预览中的“点选修改”，再选择一个页面元素。</p>
  </section>
</template>

<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { createModification, getModification, modificationEventUrl } from "../api/modifications";
import type { ElementSnapshot, Modification } from "../types";

const props = defineProps<{
  projectId: number;
  generationId?: number;
  sessionId?: number;
  element: ElementSnapshot | null;
}>();
const emit = defineEmits<{ (event: "completed"): void }>();

const instruction = ref("");
const busy = ref(false);
const statusText = ref("");
let eventSource: EventSource | null = null;

watch(() => props.element, () => {
  instruction.value = "";
  statusText.value = "";
});

function closeStream() {
  eventSource?.close();
  eventSource = null;
}

function watchModification(modificationId: number) {
  closeStream();
  eventSource = new EventSource(modificationEventUrl(modificationId));
  eventSource.addEventListener("stage", (event) => {
    const data = JSON.parse((event as MessageEvent).data);
    statusText.value = data.stage === "locate" ? "正在定位源码…" : "正在应用局部修改…";
  });
  eventSource.addEventListener("completed", () => {
    statusText.value = "修改完成";
    busy.value = false;
    closeStream();
    emit("completed");
  });
  eventSource.addEventListener("error", async (event) => {
    const data = JSON.parse((event as MessageEvent).data || "{}");
    statusText.value = data.error || "修改失败";
    busy.value = false;
    closeStream();
    const latest: Modification = await getModification(modificationId);
    if (latest.status === "succeeded") emit("completed");
  });
  eventSource.addEventListener("cancelled", () => {
    statusText.value = "修改已取消";
    busy.value = false;
    closeStream();
  });
  eventSource.onerror = () => {
    // 任务完成事件优先关闭；网络错误时由状态查询兜底
    if (busy.value) statusText.value = "等待修改结果…";
  };
}

async function submit() {
  if (!props.element || !instruction.value.trim() || busy.value) return;
  busy.value = true;
  statusText.value = "排队中…";
  try {
    const modification = await createModification(props.projectId, {
      generation_id: props.generationId,
      session_id: props.sessionId,
      selector: { css: props.element.selector },
      element_snapshot: props.element,
      instruction: instruction.value.trim(),
    });
    watchModification(modification.id);
  } catch (error: any) {
    busy.value = false;
    statusText.value = error.response?.data?.detail || "提交修改失败";
    ElMessage.error(statusText.value);
  }
}

onBeforeUnmount(closeStream);
</script>

<style scoped>
.modify-panel {
  margin-top: 12px;
  padding: 14px 16px 16px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 16px;
  box-shadow: var(--shadow-sm);
}
.modify-panel.empty { min-height: 92px; }
.modify-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 10px; }
.eyebrow { margin: 0 0 3px; color: var(--primary); font-size: 10px; letter-spacing: .12em; }
h2 { margin: 0; color: var(--ink); font-size: 15px; }
.tag { padding: 3px 7px; border-radius: 6px; background: var(--primary-soft); color: var(--primary-dark); font-size: 10px; }
.selected-element { display: flex; align-items: center; gap: 9px; margin-bottom: 10px; padding: 8px 10px; background: #f8f9fc; border: 1px solid var(--line); border-radius: 9px; }
.selection-dot { width: 8px; height: 8px; flex: none; border-radius: 50%; background: var(--amber); box-shadow: 0 0 0 4px var(--amber-soft); }
.selection-copy { min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.selection-copy strong { overflow: hidden; color: var(--ink); font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.selection-copy span { overflow: hidden; color: var(--muted); font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }
.modify-actions { display: flex; align-items: center; gap: 10px; margin-top: 9px; }
.status { flex: 1; color: var(--primary-dark); font-size: 10px; }
.hint, .empty-copy { color: var(--muted); font-size: 11px; }
.hint { flex: 1; }
.empty-copy { margin: 4px 0 0; }
</style>
