<template>
  <section class="asset-panel">
    <header>
      <div><span class="title">素材任务</span><span class="hint">后台检索，不打断创作</span></div>
      <button class="close" type="button" aria-label="关闭素材任务" @click="$emit('close')">×</button>
    </header>
    <p v-if="!jobs.length" class="empty">还没有素材任务</p>
    <article v-for="job in jobs" :key="job.id" class="job">
      <div class="row"><strong>{{ job.request.kind }} · {{ job.request.query }}</strong><span class="status" :class="job.status">{{ statusLabel(job.status) }}</span></div>
      <p v-if="job.error" class="error">{{ job.error }}</p>
      <div v-if="job.candidates.length" class="carousel">
        <button class="arrow" type="button" aria-label="上一个候选" @click="move(job, -1)">‹</button>
        <button class="stage" type="button" @click="select(job.id, currentIndex(job))">
          <img v-if="currentCandidate(job)?.external_url" :src="currentCandidate(job)?.external_url" :alt="currentCandidate(job)?.title || '素材候选'">
          <span v-else class="thumbnail-empty">素材预览不可用</span>
          <span v-if="job.request.selected_index === currentIndex(job)" class="selected-mark">当前选用</span>
        </button>
        <button class="arrow" type="button" aria-label="下一个候选" @click="move(job, 1)">›</button>
      </div>
      <div v-if="job.candidates.length" class="caption">
        <span>{{ currentCandidate(job)?.title || '未命名素材' }}</span>
        <small>{{ currentCandidate(job)?.source }} · {{ currentCandidate(job)?.attribution || '来源署名见素材清单' }}</small>
      </div>
      <div v-if="job.candidates.length > 1" class="dots" role="tablist">
        <button v-for="(_, index) in job.candidates" :key="index" type="button" :class="{ active: currentIndex(job) === index }" :aria-label="`查看候选 ${index + 1}`" @click="indexByJob[job.id] = index" />
      </div>
      <div class="actions"><button v-if="job.status === 'pending' || job.status === 'running'" type="button" @click="cancel(job.id)">取消任务</button><button v-else-if="job.status !== 'succeeded'" type="button" @click="retry(job.id)">重新检索</button></div>
    </article>
    <nav v-if="total > pageSize" class="pager" aria-label="素材任务分页">
      <button type="button" :disabled="page === 1" @click="goTo(page - 1)">上一页</button>
      <span>第 {{ page }} / {{ totalPages }} 页</span>
      <button type="button" :disabled="page === totalPages" @click="goTo(page + 1)">下一页</button>
    </nav>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue';
import { cancelAssetJob, listAssetJobs, retryAssetJob, selectAssetCandidate, type AssetJob } from '../api/projects';
const props = defineProps<{ projectId: number }>();
const emit = defineEmits<{ (event: 'asset-updated'): void; (event: 'close'): void }>();
const pageSize = 5; const jobs = ref<AssetJob[]>([]); const total = ref(0); const page = ref(1); const nextOffset = ref<number | null>(null); const indexByJob = reactive<Record<number, number>>({}); let timer: ReturnType<typeof setInterval> | null = null;
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)));
const statusLabel = (status: string) => ({ pending: '排队中', running: '检索中', succeeded: '已完成', cancelled: '已取消', cancel_requested: '取消中' }[status] || '失败');
const currentIndex = (job: AssetJob) => Math.min(indexByJob[job.id] ?? job.request.selected_index ?? 0, Math.max(0, job.candidates.length - 1));
const currentCandidate = (job: AssetJob) => job.candidates[currentIndex(job)];
function move(job: AssetJob, delta: number) { indexByJob[job.id] = (currentIndex(job) + delta + job.candidates.length) % job.candidates.length; }
async function load() { const result = await listAssetJobs(props.projectId, (page.value - 1) * pageSize, pageSize); jobs.value = result.jobs; total.value = result.total; nextOffset.value = result.next_offset; if (page.value > totalPages.value) { page.value = totalPages.value; await load(); } }
async function goTo(target: number) { page.value = Math.min(totalPages.value, Math.max(1, target)); await load(); }
async function cancel(id: number) { await cancelAssetJob(props.projectId, id); await load(); }
async function retry(id: number) { await retryAssetJob(props.projectId, id); await load(); }
async function select(id: number, index: number) { await selectAssetCandidate(props.projectId, id, index); await load(); emit('asset-updated'); }
onMounted(() => { void load(); timer = setInterval(() => void load(), 2500); }); onBeforeUnmount(() => { if (timer) clearInterval(timer); });
</script>

<style scoped>
.asset-panel{width:min(560px,calc(100vw - 42px));max-height:min(700px,calc(100vh - 128px));overflow:auto;border:1px solid var(--line-strong);padding:14px;background:var(--paper);border-radius:var(--radius-lg);box-shadow:var(--shadow-lg)}header,.row,.actions,.pager{display:flex;align-items:center;gap:8px}.title{font-weight:600}.hint,.empty,small{color:var(--muted);font-size:12px;margin-left:8px}.close{margin-left:auto;border:0;background:transparent;color:var(--muted);font-size:22px;cursor:pointer}.job{margin-top:12px;padding-top:12px;border-top:1px solid var(--line)}.status{margin-left:auto;font-size:12px}.status.running,.status.pending{color:var(--amber)}.status.succeeded{color:var(--green)}.carousel{display:grid;grid-template-columns:38px minmax(0,1fr) 38px;gap:8px;align-items:center;margin-top:10px}.stage{position:relative;display:block;padding:0;overflow:hidden;border:1px solid var(--line);border-radius:var(--radius-md);background:var(--canvas-deep);aspect-ratio:16/8;cursor:pointer}.stage img{width:100%;height:100%;display:block;object-fit:cover}.arrow{height:42px;border:1px solid var(--line-strong);border-radius:50%;background:var(--paper);color:var(--primary);font-size:28px;cursor:pointer}.thumbnail-empty{display:grid;height:100%;place-items:center;color:var(--muted)}.selected-mark{position:absolute;top:10px;right:10px;padding:4px 8px;border-radius:999px;background:var(--primary);color:#fff;font-size:11px}.caption{margin-top:8px}.caption span,.caption small{display:block;margin:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.caption span{font-size:13px;font-weight:600}.dots{display:flex;justify-content:center;gap:6px;margin-top:9px}.dots button{width:6px;height:6px;padding:0;border:0;border-radius:50%;background:var(--line-strong);cursor:pointer}.dots button.active{width:18px;border-radius:6px;background:var(--primary)}.actions{margin-top:8px}.actions button,.pager button{border:0;background:transparent;color:var(--primary);cursor:pointer;padding:0}.pager{justify-content:center;margin:15px 0 2px;font-size:12px}.pager button:disabled{color:var(--muted);cursor:default}.error{color:var(--red);font-size:12px}@media(max-width:520px){.asset-panel{width:calc(100vw - 24px)}.carousel{grid-template-columns:32px minmax(0,1fr) 32px}.hint{display:none}}
</style>
