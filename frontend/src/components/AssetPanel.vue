<template>
  <section class="asset-panel">
    <header>
      <span class="title">素材任务</span>
      <span class="hint">后台检索不阻塞生成</span>
      <button class="close" type="button" aria-label="关闭素材任务" @click="$emit('close')">×</button>
    </header>
    <p v-if="!jobs.length" class="empty">当前项目还没有素材任务</p>
    <article v-for="job in jobs" :key="job.id" class="job">
      <div class="row">
        <strong>{{ job.request.kind }} · {{ job.request.query }}</strong>
        <span class="status" :class="job.status">{{ statusLabel(job.status) }}</span>
      </div>
      <p v-if="job.error" class="error">{{ job.error }}</p>
      <div v-if="job.candidates.length" class="candidates">
        <button
          v-for="(candidate, index) in job.candidates"
          :key="`${job.id}-${index}`"
          type="button"
          :class="{ selected: job.request.selected_index === index }"
          @click="select(job.id, index)"
        >
          <span class="thumbnail">
            <img
              v-if="candidate.external_url"
              :src="candidate.external_url"
              :alt="candidate.title || '素材候选'"
              loading="lazy"
            >
            <span v-else class="thumbnail-empty">素材</span>
            <span v-if="job.request.selected_index === index" class="selected-mark">已选</span>
          </span>
          <span class="candidate-copy">
            <span>{{ candidate.title || '未命名素材' }}</span>
            <small>{{ candidate.source }} · {{ candidate.attribution || '来源署名见素材清单' }}</small>
          </span>
        </button>
      </div>
      <div class="actions">
        <button v-if="job.status === 'pending' || job.status === 'running'" type="button" @click="cancel(job.id)">取消</button>
        <button v-else-if="job.status !== 'succeeded'" type="button" @click="retry(job.id)">重试</button>
      </div>
    </article>
  </section>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue';
import { cancelAssetJob, listAssetJobs, retryAssetJob, selectAssetCandidate, type AssetJob } from '../api/projects';

const props = defineProps<{ projectId: number }>();
const emit = defineEmits<{ (event: 'asset-updated'): void; (event: 'close'): void }>();
const jobs = ref<AssetJob[]>([]);
let timer: ReturnType<typeof setInterval> | null = null;

const statusLabel = (status: string) => ({ pending: '排队中', running: '检索中', succeeded: '已完成', cancelled: '已取消', cancel_requested: '取消中' }[status] || '失败');
async function load() { jobs.value = await listAssetJobs(props.projectId); }
async function cancel(id: number) { await cancelAssetJob(props.projectId, id); await load(); }
async function retry(id: number) { await retryAssetJob(props.projectId, id); await load(); }
async function select(id: number, index: number) { await selectAssetCandidate(props.projectId, id, index); await load(); emit('asset-updated'); }
onMounted(() => { void load(); timer = setInterval(() => void load(), 2500); });
onBeforeUnmount(() => { if (timer) clearInterval(timer); });
</script>

<style scoped>
.asset-panel { width: min(390px, calc(100vw - 44px)); max-height: min(620px, calc(100vh - 140px)); overflow: auto; border: 1px solid var(--line-strong); padding: 12px 14px; background: var(--paper); border-radius: var(--radius-lg); box-shadow: var(--shadow-lg); }
header,.row,.actions { display:flex; align-items:center; gap:8px; }
.title { font-weight: 600; } .hint,.empty,small { color: var(--muted); font-size: 12px; }
.close { margin-left:auto; border:0; background:transparent; color:var(--muted); font-size:22px; line-height:1; cursor:pointer; }
.job { margin-top:10px; padding-top:10px; border-top:1px solid var(--line); }
.status { margin-left:auto; font-size:12px; color:var(--muted); }.status.running,.status.pending { color:var(--amber); }.status.succeeded { color:var(--green); }
.candidates { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:8px; margin-top:10px; }.candidates button { position:relative; min-width:0; text-align:left; padding:0; overflow:hidden; background:var(--paper); border:1px solid var(--line); border-radius:var(--radius-sm); cursor:pointer; transition:transform .16s,border-color .16s,box-shadow .16s; }.candidates button:hover { transform:translateY(-1px); border-color:var(--primary); box-shadow:0 7px 16px rgba(82,100,216,.14); }.candidates button.selected { border-color:var(--primary); box-shadow:0 0 0 2px var(--primary-soft); }.thumbnail { position:relative; display:block; aspect-ratio:4/3; overflow:hidden; background:var(--canvas-deep); }.thumbnail img { width:100%; height:100%; display:block; object-fit:cover; transition:transform .22s ease; }.candidates button:hover .thumbnail img { transform:scale(1.045); }.thumbnail-empty { display:grid; width:100%; height:100%; place-items:center; color:var(--muted); font-size:12px; }.selected-mark { position:absolute; top:7px; right:7px; padding:3px 6px; border-radius:999px; background:var(--primary); color:#fff; font-size:11px; }.candidate-copy { display:block; padding:7px 8px 8px; }.candidate-copy > span,.candidate-copy small { display:block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }.candidate-copy > span { color:var(--ink); font-size:12px; font-weight:600; }.actions { margin-top:8px; }.actions button { border:0; background:transparent; color:var(--primary); cursor:pointer; padding:0; }.error { color:var(--red); font-size:12px; }
@media (max-width: 480px) { .candidates { grid-template-columns:repeat(3,minmax(0,1fr)); }.candidate-copy { display:none; } }
</style>
