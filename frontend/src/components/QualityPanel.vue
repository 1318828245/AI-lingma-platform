<template>
  <section class="quality-panel">
    <header><div><span class="eyebrow">DELIVERY CHECK</span><h2>交付检查</h2></div><div class="header-actions"><button class="refresh" type="button" :disabled="refreshing" @click="$emit('refresh')">{{ refreshing ? '检查中…' : '重新检查' }}</button><button type="button" aria-label="关闭交付检查" @click="$emit('close')">×</button></div></header>
    <div v-if="!evaluation" class="empty">完成一次生成或修改后，这里会显示四项交付检查。</div>
    <template v-else>
      <div class="score-line" :class="{ passed: evaluation.pass }"><strong>{{ Math.round(evaluation.score) }}</strong><span>/ 20<br>{{ evaluation.pass ? '可以交付' : '建议改进后再交付' }}</span></div>
      <div class="dimensions"><div v-for="(item, key) in evaluation.dimensions" :key="key" class="dimension"><div><span>{{ item.label }}</span><b>{{ Math.round(item.score) }} / 5</b></div><i><em :style="{ width: `${item.score * 20}%` }" /></i><small>{{ item.detail }}</small></div></div>
      <div v-if="evaluation.issues.length" class="issues"><p>建议改进</p><article v-for="issue in evaluation.issues" :key="`${issue.dimension}-${issue.message}`"><strong>{{ issue.label }}</strong><span class="issue-detail">{{ issue.message }}</span><span>{{ issue.recommendation }}</span><button type="button" @click="$emit('improve', issue.recommendation)">按此建议改进</button></article></div>
      <p v-else class="all-good">四项检查均通过，当前版本可以继续迭代或交付。</p>
    </template>
  </section>
</template>
<script setup lang="ts">
import type { QualityEvaluation } from '../api/projects';
defineProps<{ evaluation: QualityEvaluation | null; refreshing?: boolean }>();
defineEmits<{ (event: 'close'): void; (event: 'improve', recommendation: string): void; (event: 'refresh'): void }>();
</script>
<style scoped>
.quality-panel{width:min(390px,calc(100vw - 42px));max-height:min(650px,calc(100vh - 128px));overflow:auto;padding:18px;background:var(--paper);border:1px solid var(--line-strong);border-radius:16px;box-shadow:var(--shadow-lg)}header,.header-actions{display:flex;align-items:flex-start;justify-content:space-between;gap:8px}header button{border:0;background:transparent;color:var(--muted);font-size:24px;cursor:pointer}.header-actions .refresh{margin-top:2px;padding:4px 7px;border:1px solid var(--line-strong);border-radius:7px;color:var(--primary);font-size:11px}.header-actions .refresh:disabled{opacity:.5;cursor:wait}.eyebrow{font:10px var(--font-mono);letter-spacing:.14em;color:var(--primary)}h2{margin:3px 0 0;font-size:18px;color:var(--ink)}.score-line{display:flex;align-items:center;gap:10px;margin:16px 0;padding:14px;border-radius:13px;background:var(--red-soft);color:var(--red)}.score-line.passed{background:var(--green-soft);color:var(--green)}.score-line strong{font:600 34px var(--font-display)}.score-line span{font-size:12px;line-height:1.45}.dimensions{display:grid;gap:12px}.dimension>div{display:flex;justify-content:space-between;font-size:12px;color:var(--ink)}.dimension b{font-family:var(--font-mono);color:var(--primary)}.dimension i{display:block;height:5px;margin:6px 0;border-radius:9px;background:var(--canvas-deep);overflow:hidden}.dimension em{display:block;height:100%;border-radius:inherit;background:linear-gradient(90deg,#6b7df0,#a2afff)}small{color:var(--muted);font-size:11px}.issues{margin-top:16px;padding-top:13px;border-top:1px solid var(--line)}.issues p{margin:0 0 8px;font-size:12px;font-weight:650;color:var(--ink)}.issues article{padding:10px 0;border-top:1px solid var(--line);display:grid;gap:4px}.issues strong{font-size:12px}.issues span{font-size:12px;color:var(--muted);line-height:1.45}.issues .issue-detail{color:var(--ink)}.issues button{justify-self:start;border:0;padding:0;background:transparent;color:var(--primary);font-size:12px;cursor:pointer}.all-good,.empty{margin:18px 0 3px;color:var(--muted);font-size:13px;line-height:1.6}@media(max-width:520px){.quality-panel{width:calc(100vw - 24px)}}
</style>
