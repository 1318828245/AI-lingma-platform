<template>
  <aside class="deployment-panel">
    <header>
      <div><p class="eyebrow">M4 / DELIVERY</p><h2>发布中心</h2></div>
      <button class="close" type="button" title="收起发布中心" @click="$emit('close')">×</button>
    </header>
    <section class="publish-callout">
      <span class="launch-mark" aria-hidden="true">↗</span>
      <div><strong>发布当前构建</strong><p>从最新版本快照创建独立、可公开访问的静态站点。</p></div>
      <button type="button" :disabled="publishing" @click="publish">{{ publishing ? '正在发布…' : '发布' }}</button>
    </section>
    <div class="history-head"><span>发布记录</span><button type="button" :disabled="loading" @click="load">刷新</button></div>
    <div v-if="loading" class="empty">正在读取发布记录…</div>
    <div v-else-if="!deployments.length" class="empty">还没有发布。完成构建后，可在这里生成公开访问链接。</div>
    <ol v-else class="deployments">
      <li v-for="deployment in deployments" :key="deployment.id" :class="deployment.status">
        <div class="deploy-top"><span class="status-dot" /><strong>{{ statusLabel(deployment.status) }}</strong><time>{{ formatTime(deployment.created_at) }}</time></div>
        <p>版本 #{{ deployment.version }} · <code>{{ deployment.slug }}</code></p>
        <a v-if="deployment.url" :href="deployment.url" target="_blank" rel="noopener">打开已发布站点 <span>↗</span></a>
        <div v-else-if="deployment.error" class="error">{{ deployment.error }}</div>
      </li>
    </ol>
  </aside>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { createDeployment, listDeployments, type Deployment } from "../api/deployments";

const props = defineProps<{ projectId: number }>();
defineEmits<{ (event: "close"): void }>();
const deployments = ref<Deployment[]>([]);
const loading = ref(false);
const publishing = ref(false);

function statusLabel(status: Deployment["status"]) { return { publishing: "正在发布", ready: "已发布", failed: "发布失败" }[status]; }
function formatTime(value: string) { return new Date(value).toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }); }
async function load() { loading.value = true; try { deployments.value = await listDeployments(props.projectId); } catch { ElMessage.error("无法读取发布记录"); } finally { loading.value = false; } }
async function publish() { publishing.value = true; try { const result = await createDeployment(props.projectId); await load(); if (result.status === "ready") ElMessage.success("项目已发布"); else ElMessage.error(result.error || "发布失败，请查看记录"); } catch (error: any) { ElMessage.error(error.response?.data?.detail || "无法创建发布任务"); } finally { publishing.value = false; } }
onMounted(load);
</script>

<style scoped>
.deployment-panel { position:absolute; z-index:8; top:62px; right:16px; width:min(440px,calc(100% - 32px)); max-height:calc(100% - 78px); overflow:auto; padding:18px; border:1px solid #dbe1f4; border-radius:16px; background:rgba(252,253,255,.98); box-shadow:0 20px 50px rgba(35,48,90,.18); color:#20294b; }
header { display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:14px; } .eyebrow { margin:0 0 4px; color:#7180aa; font:600 10px/1.2 ui-monospace,monospace; letter-spacing:.12em; } h2 { margin:0; font-size:18px; } .close { border:0; background:transparent; color:#687397; font-size:25px; cursor:pointer; line-height:1; }
.publish-callout { display:flex; align-items:center; gap:11px; padding:13px; border:1px solid #d9e2ff; border-radius:12px; background:linear-gradient(120deg,#f0f4ff,#fbfcff); } .launch-mark { display:grid; place-items:center; width:32px; height:32px; border-radius:10px; background:#5264d8; color:#fff; font-size:20px; } .publish-callout div { flex:1; } .publish-callout strong { font-size:13px; } .publish-callout p { margin:3px 0 0; color:#697493; font-size:11px; line-height:1.45; } .publish-callout button { border:0; border-radius:8px; padding:7px 11px; background:#273774; color:#fff; font-weight:650; cursor:pointer; } button:disabled { opacity:.55; cursor:wait; }
.history-head { display:flex; justify-content:space-between; margin:18px 1px 8px; color:#536084; font-size:12px; font-weight:700; } .history-head button { border:0; background:transparent; color:#5264d8; cursor:pointer; font-size:12px; } .empty { padding:18px 4px; color:#7c86a4; font-size:12px; line-height:1.6; }
.deployments { display:grid; gap:8px; margin:0; padding:0; list-style:none; } .deployments li { padding:11px; border:1px solid #e3e7f1; border-left:3px solid #8691b4; border-radius:10px; background:#fff; } .deployments li.ready { border-left-color:#32a875; } .deployments li.failed { border-left-color:#d15b6c; } .deploy-top { display:flex; align-items:center; gap:6px; font-size:12px; } .status-dot { width:7px; height:7px; border-radius:50%; background:#8691b4; } .ready .status-dot { background:#32a875; box-shadow:0 0 0 3px #e5f8ef; } .failed .status-dot { background:#d15b6c; } time { margin-left:auto; color:#8992ab; font-size:10px; } li p { margin:6px 0; color:#687397; font-size:11px; } code { color:#55618b; } a { color:#3d52bf; font-size:12px; font-weight:650; text-decoration:none; } a span { font-size:15px; } .error { color:#b34556; font-size:11px; line-height:1.45; }
</style>
