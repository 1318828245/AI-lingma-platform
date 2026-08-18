<template>
  <section class="version-panel" :class="{ floating }">
    <div class="version-head">
      <div>
        <p class="eyebrow mono">M2 / VERSION CONTROL</p>
        <h2>版本历史</h2>
      </div>
      <span class="mono count">{{ versions.length }} 个版本</span>
    </div>
    <div v-if="loading" class="muted">正在读取版本…</div>
    <div v-else-if="!versions.length" class="muted">生成或修改完成后会自动保存版本。</div>
    <div v-else class="version-list">
      <article v-for="version in versions" :key="version.id" class="version-row">
        <div class="version-main">
          <div class="version-title">
            <strong>v{{ version.version_no }}</strong>
            <span class="source">{{ sourceLabel(version.source_type) }}</span>
            <span class="mono files">{{ version.file_count }} 文件</span>
          </div>
          <p>{{ version.summary || "无版本说明" }}</p>
          <time class="mono">{{ formatTime(version.created_at) }}</time>
        </div>
        <div class="version-actions">
          <button class="text-btn" @click="toggleDiff(version.id)">
            {{ openVersion === version.id ? "收起 diff" : "查看 diff" }}
          </button>
          <button class="text-btn rollback" :disabled="busy" @click="rollback(version)">回滚</button>
        </div>
        <div v-if="openVersion === version.id" class="diff-box">
          <p v-if="diffLoading" class="muted">正在计算 diff…</p>
          <template v-else-if="activeDiff?.files.length">
            <div v-for="file in activeDiff.files" :key="file.path" class="diff-file">
              <div class="diff-file-head"><span class="mono">{{ file.path }}</span><span>{{ file.status }}</span></div>
              <pre>{{ file.diff }}</pre>
            </div>
          </template>
          <p v-else class="muted">当前工作区与该版本没有差异。</p>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { getProjectVersionDiff, listProjectVersions, rollbackProjectVersion } from "../api/versions";
import type { ProjectVersion, VersionDiff } from "../types";

const props = withDefaults(defineProps<{ projectId: number; refreshToken?: number; floating?: boolean }>(), { refreshToken: 0, floating: false });
const emit = defineEmits<{ (event: "rollback"): void }>();
const versions = ref<ProjectVersion[]>([]);
const loading = ref(false);
const diffLoading = ref(false);
const busy = ref(false);
const openVersion = ref<number | null>(null);
const activeDiff = ref<VersionDiff | null>(null);

async function loadVersions() {
  loading.value = true;
  try { versions.value = await listProjectVersions(props.projectId); }
  finally { loading.value = false; }
}

function sourceLabel(source: string) {
  return source === "modification" ? "局部修改" : source === "generation" ? "生成" : source;
}

function formatTime(value: string) {
  return new Date(value).toLocaleString("zh-CN", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

async function toggleDiff(versionId: number) {
  if (openVersion.value === versionId) { openVersion.value = null; activeDiff.value = null; return; }
  openVersion.value = versionId;
  diffLoading.value = true;
  try { activeDiff.value = await getProjectVersionDiff(props.projectId, versionId); }
  finally { diffLoading.value = false; }
}

async function rollback(version: ProjectVersion) {
  try {
    await ElMessageBox.confirm(`确认将工作区回滚到 v${version.version_no} 吗？`, "回滚版本", { type: "warning" });
    busy.value = true;
    await rollbackProjectVersion(props.projectId, version.id);
    ElMessage.success(`已回滚到 v${version.version_no}`);
    emit("rollback");
    await loadVersions();
  } catch (error: any) {
    if (error !== "cancel" && error !== "close") ElMessage.error(error.response?.data?.detail || "回滚失败");
  } finally { busy.value = false; }
}

onMounted(loadVersions);
watch(() => props.refreshToken, loadVersions);
</script>

<style scoped>
.version-panel { margin-top: 12px; padding: 14px 16px; background: #fff; border: 1px solid var(--line); border-radius: 16px; box-shadow: var(--shadow-sm); }
.version-head { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 10px; }
.eyebrow { margin: 0 0 3px; color: var(--primary); font-size: 10px; letter-spacing: .12em; }
h2 { margin: 0; color: var(--ink); font-size: 15px; }
.count, .muted { color: var(--muted); font-size: 10px; }
.version-list { display: flex; flex-direction: column; gap: 7px; }
.version-row { padding: 9px 10px; border: 1px solid var(--line); border-radius: 9px; background: #f9faff; }
.version-main { min-width: 0; }
.version-title { display: flex; align-items: center; gap: 7px; color: var(--ink); font-size: 12px; }
.source { padding: 2px 5px; border-radius: 5px; background: var(--primary-soft); color: var(--primary-dark); font-size: 10px; }
.files, time { color: var(--muted); font-size: 10px; }
.version-main p { margin: 4px 0; overflow: hidden; color: var(--muted); font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }
.version-actions { display: flex; gap: 10px; margin-top: 6px; }
.text-btn { padding: 0; border: 0; background: none; color: var(--primary-dark); cursor: pointer; font-size: 10px; }
.text-btn:hover { text-decoration: underline; }
.text-btn.rollback { color: #b04b56; }
.text-btn:disabled { opacity: .45; cursor: not-allowed; }
.diff-box { margin-top: 8px; padding: 8px; border-top: 1px solid var(--line); }
.diff-file + .diff-file { margin-top: 8px; }
.diff-file-head { display: flex; justify-content: space-between; color: var(--muted); font-size: 10px; }
.diff-file pre { max-height: 180px; overflow: auto; margin: 5px 0 0; padding: 8px; background: #202633; color: #dbe5f4; border-radius: 6px; font: 10px/1.55 var(--font-mono); white-space: pre-wrap; }
</style>
