<template>
  <section class="deployment-console" aria-label="项目发布中心">
    <header class="console-header"><div class="console-kicker"><span class="pulse" /> DELIVERY CONTROL</div><span class="console-caption">发布项目的静态交付版本</span></header>

    <div class="console-grid">
      <section class="launch-zone">
        <div class="launch-copy">
          <p class="section-label">发布状态</p>
          <h2>{{ activeDeployment ? '项目正在公开访问' : '准备发布这个项目' }}</h2>
          <p class="launch-description">{{ activeDeployment ? '稳定线上地址会始终指向当前版本。你可以从历史记录恢复旧版本，或立即下线当前站点。' : '发布会保存当前成功构建，并生成一个任何人都能打开的稳定线上地址。' }}</p>
        </div>
        <div class="launch-orbit" :class="{ live: activeDeployment }" aria-hidden="true"><span>↗</span></div>
        <button class="launch-button" type="button" :disabled="publishing || loading" @click="confirmPublish">
          <span class="launch-button-icon">{{ publishing ? '…' : '↗' }}</span>
          <span><b>{{ publishing ? '正在创建发布版本' : '发布当前构建' }}</b><small>{{ publishing ? '正在整理静态交付物' : '生成新的公开访问链接' }}</small></span>
        </button>
        <p class="launch-note">发布 Vue 项目的构建产物，或 HTML/multifile 项目的静态文件。</p>
      </section>

      <section class="access-zone">
        <div class="section-heading"><div><p class="section-label">当前线上版本</p><h3>{{ activeDeployment ? `版本 #${activeDeployment.version}` : '当前没有线上版本' }}</h3></div><span class="state-pill" :class="activeDeployment ? 'ready' : 'idle'"><i />{{ activeDeployment ? '在线' : '已下线' }}</span></div>
        <template v-if="activeDeployment?.site_url">
          <div class="url-card"><span class="url-label">STABLE PROJECT URL</span><code>{{ activeDeployment.site_url }}</code><div class="url-actions"><button type="button" @click="copyUrl(activeDeployment.site_url)">复制链接</button><a :href="activeDeployment.site_url" target="_blank" rel="noopener">打开站点 <span>↗</span></a></div></div>
          <dl class="release-meta"><div><dt>上线时间</dt><dd>{{ formatFullTime(activeDeployment.updated_at) }}</dd></div><div><dt>发布标识</dt><dd><code>{{ activeDeployment.slug }}</code></dd></div></dl>
          <button class="offline-button" type="button" @click="confirmOffline(activeDeployment)">下线当前站点</button>
        </template>
        <div v-else class="empty-access"><span>◎</span><p>完成构建后，点击左侧按钮即可创建公开链接。</p></div>
      </section>
    </div>

    <section class="history-zone">
      <div class="history-heading"><div><p class="section-label">发布时间线</p><h3>交付记录</h3></div><button class="refresh" type="button" :disabled="loading" @click="load"><span>⟳</span> 刷新</button></div>
      <div v-if="loading" class="history-loading"><i />正在读取发布记录…</div>
      <ol v-else-if="deployments.length" class="release-timeline">
        <li v-for="(deployment, index) in visibleDeployments" :key="deployment.id" :class="deployment.status">
          <span class="timeline-track"><i /><em v-if="index < visibleDeployments.length - 1" /></span>
          <article><div class="record-top"><span class="record-state">{{ deployment.is_active ? '当前线上' : statusLabel(deployment.status) }}</span><time>{{ formatTime(deployment.created_at) }}</time></div><strong>版本 #{{ deployment.version }}</strong><code>{{ deployment.slug }}</code><a v-if="deployment.url && deployment.status === 'ready'" :href="deployment.url" target="_blank" rel="noopener">访问此版本 ↗</a><button v-if="(deployment.status === 'ready' || deployment.status === 'offline') && !deployment.is_active" class="activate" type="button" @click="confirmActivate(deployment)">{{ deployment.status === 'offline' ? '恢复并设为线上' : '设为线上' }}</button><p v-if="deployment.status === 'offline'" class="offline-note">此版本已下线，恢复后将重新开放访问。</p><p v-else-if="deployment.status !== 'ready'" class="failure">{{ deployment.error || '发布未完成，请重新发布。' }}</p></article>
        </li>
      </ol>
      <div v-else class="history-empty">发布记录会保留每一份可访问的交付版本。</div>
      <button v-if="deployments.length > 4" class="more" type="button" @click="showAll = !showAll">{{ showAll ? '收起较早记录' : `查看其余 ${deployments.length - 4} 次发布` }}</button>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { activateDeployment, createDeployment, listDeployments, offlineDeployment, type Deployment } from "../api/deployments";

const props = defineProps<{ projectId: number }>();
const deployments = ref<Deployment[]>([]);
const loading = ref(false);
const publishing = ref(false);
const showAll = ref(false);
const activeDeployment = computed(() => deployments.value.find((item) => item.is_active && item.status === "ready") || null);
const visibleDeployments = computed(() => showAll.value ? deployments.value : deployments.value.slice(0, 4));

function statusLabel(status: Deployment["status"]) { return { publishing: "正在发布", ready: "可恢复", failed: "发布失败", offline: "已下线" }[status]; }
function formatTime(value: string) { return new Date(value).toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }); }
function formatFullTime(value: string) { return new Date(value).toLocaleString("zh-CN", { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }); }
async function load() { loading.value = true; try { deployments.value = await listDeployments(props.projectId); } catch { ElMessage.error("无法读取发布记录，请稍后刷新"); } finally { loading.value = false; } }
async function copyUrl(url: string) { try { await navigator.clipboard.writeText(url); ElMessage.success("公开链接已复制"); } catch { ElMessage.warning("复制失败，请手动复制链接"); } }
async function confirmPublish() {
  try {
    await ElMessageBox.confirm("将从当前成功构建创建一个新的公开发布版本。已有发布链接不会受到影响。", "确认发布当前构建", { confirmButtonText: "确认发布", cancelButtonText: "暂不发布", type: "info", closeOnClickModal: false });
  } catch { return; }
  publishing.value = true;
  try { const result = await createDeployment(props.projectId); await load(); if (result.status === "ready") ElMessage.success("发布成功，公开链接已生成"); else ElMessage.error(result.error || "发布失败，请查看记录"); } catch (error: any) { ElMessage.error(error.response?.data?.detail || "无法创建发布版本"); } finally { publishing.value = false; }
}
async function confirmActivate(deployment: Deployment) {
  try { await ElMessageBox.confirm(`将版本 #${deployment.version} 设为线上版本，稳定访问地址会立即切换。`, "确认恢复历史版本", { confirmButtonText: "设为线上", cancelButtonText: "取消", type: "warning", closeOnClickModal: false }); } catch { return; }
  try { await activateDeployment(props.projectId, deployment.id); await load(); ElMessage.success(`版本 #${deployment.version} 已设为线上版本`); } catch (error: any) { ElMessage.error(error.response?.data?.detail || "无法切换线上版本"); }
}
async function confirmOffline(deployment: Deployment) {
  try { await ElMessageBox.confirm("下线后，稳定地址和该版本的公开访问链接都会立即失效。", "确认下线当前站点", { confirmButtonText: "确认下线", cancelButtonText: "保留在线", type: "warning", closeOnClickModal: false }); } catch { return; }
  try { await offlineDeployment(props.projectId, deployment.id); await load(); ElMessage.success("当前站点已下线"); } catch (error: any) { ElMessage.error(error.response?.data?.detail || "无法下线当前站点"); }
}
onMounted(load);
</script>

<style scoped>
.deployment-console { box-sizing:border-box; height:100%; min-height:0; display:flex; flex-direction:column; overflow:auto; padding:26px; border:1px solid #dce3fa; border-radius:18px; background:linear-gradient(145deg,rgba(255,255,255,.985),rgba(246,248,255,.98)); box-shadow:0 16px 42px rgba(34,47,89,.12); color:#1f294b; }
.console-header,.section-heading,.history-heading,.record-top,.url-actions { display:flex; align-items:center; justify-content:space-between; } .console-kicker,.section-label,.url-label { margin:0; color:#7180a8; font:700 12px/1.2 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:.1em; } .pulse { display:inline-block; width:8px; height:8px; margin-right:8px; border-radius:50%; background:#5264d8; box-shadow:0 0 0 4px rgba(82,100,216,.12); } .console-caption { color:#65728f; font-size:13px; }
.console-grid { display:grid; grid-template-columns:1.15fr .85fr; gap:16px; margin-top:23px; } .launch-zone,.access-zone,.history-zone { border:1px solid #d8e0f3; border-radius:14px; background:#fff; } .launch-zone { position:relative; overflow:hidden; padding:24px; background:linear-gradient(135deg,#26366f,#5668dc 65%,#7786f2); color:#fff; isolation:isolate; } .launch-zone::after { content:""; position:absolute; z-index:-1; width:230px; height:230px; right:-86px; top:-108px; border:1px solid rgba(255,255,255,.26); border-radius:50%; box-shadow:0 0 0 25px rgba(255,255,255,.05),0 0 0 51px rgba(255,255,255,.04); } .launch-zone .section-label { color:rgba(255,255,255,.75); } h2,h3 { margin:5px 0 0; letter-spacing:-.035em; } h2 { max-width:310px; font-size:28px; line-height:1.15; } h3 { font-size:19px; } .launch-description { max-width:390px; margin:13px 0 23px; color:rgba(255,255,255,.87); font-size:14px; line-height:1.65; } .launch-orbit { position:absolute; right:26px; top:42px; display:grid; place-items:center; width:58px; height:58px; border:1px solid rgba(255,255,255,.42); border-radius:50%; color:#fff; font-size:27px; transform:rotate(-22deg); } .launch-orbit.live { box-shadow:0 0 0 7px rgba(200,255,202,.14); color:#d8ffa8; }
.launch-button { display:flex; align-items:center; gap:12px; width:100%; border:0; min-height:58px; padding:13px; border-radius:10px; background:#fff; color:#25366f; text-align:left; cursor:pointer; transition:transform .18s ease,box-shadow .18s ease; } .launch-button:hover:not(:disabled) { transform:translateY(-2px); box-shadow:0 8px 20px rgba(13,22,73,.25); } .launch-button:disabled { opacity:.72; cursor:wait; } .launch-button-icon { display:grid; place-items:center; width:32px; height:32px; border-radius:8px; background:#e6ebff; color:#4054c5; font-size:20px; } .launch-button b,.launch-button small { display:block; } .launch-button b { font-size:15px; } .launch-button small { margin-top:3px; color:#637092; font-size:12px; } .launch-note { margin:11px 0 0; color:rgba(255,255,255,.72); font-size:12px; }
.access-zone { padding:22px; } .state-pill { display:inline-flex; align-items:center; gap:6px; padding:6px 9px; border-radius:999px; background:#eff2f9; color:#7180a2; font-size:12px; font-weight:700; } .state-pill i { width:7px; height:7px; border-radius:50%; background:currentColor; } .state-pill.ready { background:#e5f8ec; color:#20875b; } .url-card { margin-top:20px; padding:15px; border:1px solid #cfd9fb; border-radius:10px; background:#f8f9ff; } .url-card code { display:block; overflow:hidden; margin:8px 0 14px; color:#394a9e; font-size:13px; text-overflow:ellipsis; white-space:nowrap; } .url-actions { gap:10px; justify-content:flex-start; } .url-actions button,.url-actions a { border:1px solid #c8d2fa; border-radius:8px; min-height:34px; padding:7px 11px; background:#e6ebff; color:#344bb7; font-size:13px; font-weight:700; text-decoration:none; cursor:pointer; transition:.15s ease; } .url-actions a { border-color:#5264d8; background:#5264d8; color:#fff; } .url-actions button:hover,.url-actions a:hover { transform:translateY(-1px); box-shadow:0 3px 9px rgba(65,83,186,.2); } .release-meta { display:grid; gap:10px; margin:17px 0 0; } .release-meta div { display:flex; justify-content:space-between; gap:10px; font-size:12px; } dt { color:#7783a1; } dd { max-width:65%; overflow:hidden; margin:0; color:#3f4c73; text-align:right; text-overflow:ellipsis; white-space:nowrap; } .offline-button { width:100%; min-height:38px; margin-top:18px; border:1px solid #e7adb8; border-radius:8px; padding:8px; background:#fff7f8; color:#aa3448; font-size:13px; font-weight:700; cursor:pointer; transition:.15s ease; } .offline-button:hover { background:#ffeef1; } .empty-access { display:grid; place-items:center; min-height:150px; padding:8px 18px; color:#66738f; text-align:center; } .empty-access span { color:#8291db; font-size:30px; } .empty-access p { margin:9px 0 0; font-size:14px; line-height:1.55; }
.history-zone { margin-top:16px; padding:21px 22px; } .refresh { display:inline-flex; align-items:center; gap:5px; min-height:34px; border:1px solid #cbd5fa; border-radius:8px; padding:6px 10px; background:#f5f7ff; color:#3b50b9; font-size:13px; font-weight:700; cursor:pointer; } .refresh span { font-size:16px; } .refresh:disabled { opacity:.45; cursor:wait; } .history-loading,.history-empty { padding:24px 0 7px; color:#65728e; font-size:14px; } .history-loading i { display:inline-block; width:10px; height:10px; margin-right:8px; border:2px solid #c3cbed; border-top-color:#5264d8; border-radius:50%; animation:spin .8s linear infinite; }
.release-timeline { display:grid; gap:0; margin:19px 0 0; padding:0; list-style:none; } .release-timeline li { display:grid; grid-template-columns:24px 1fr; } .timeline-track { display:flex; flex-direction:column; align-items:center; } .timeline-track i { width:11px; height:11px; margin-top:5px; border:3px solid #e3e8fa; border-radius:50%; background:#5264d8; box-sizing:border-box; } .timeline-track em { flex:1; width:1px; margin:3px 0 -3px; background:#e5e9f5; } li.failed .timeline-track i,li.offline .timeline-track i { background:#d35a70; } li.publishing .timeline-track i { background:#e6a93a; } .release-timeline article { min-width:0; padding:0 0 18px 11px; } .record-top { color:#65728e; font-size:12px; } .record-state { color:#3a4bb0; font-weight:700; } .failed .record-state,.offline .record-state { color:#c4475d; } article strong { display:inline-block; margin:6px 10px 0 0; font-size:15px; } article code { color:#65718f; font-size:12px; } article a,.activate { display:inline-flex; align-items:center; min-height:32px; margin:9px 7px 0 0; border:1px solid #cbd5fa; border-radius:7px; padding:5px 9px; background:#f4f6ff; color:#3d52bf; font-size:12px; font-weight:700; text-decoration:none; cursor:pointer; transition:.15s ease; } .activate { border-color:#a7ddc2; background:#ecfbf3; color:#187448; } article a:hover,.activate:hover { transform:translateY(-1px); box-shadow:0 3px 8px rgba(59,79,167,.15); } .failure,.offline-note { margin:7px 0 0; color:#bd4559; font-size:12px; line-height:1.5; } .offline-note { color:#756681; } .more { min-height:34px; border:1px solid #cbd5fa; border-radius:8px; padding:6px 10px; background:#f5f7ff; color:#3b50b9; font-size:13px; font-weight:700; cursor:pointer; }
@keyframes spin { to { transform:rotate(360deg); } } @media (max-width:760px) { .deployment-console { padding:18px; } .console-grid { grid-template-columns:1fr; } .launch-orbit { right:18px; } .access-zone { min-height:0; } } @media (prefers-reduced-motion:reduce) { .history-loading i { animation:none; } .launch-button { transition:none; } }
</style>
