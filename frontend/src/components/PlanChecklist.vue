<template>
  <section class="plan-card" aria-label="实施计划">
    <button class="plan-heading" type="button" :aria-expanded="!collapsed" :aria-controls="`plan-${plan.generation_id}`" @click="$emit('toggle')">
      <span class="plan-icon" aria-hidden="true">☷</span>
      <span class="plan-heading-copy"><strong>实施计划</strong><span :title="subtitle">{{ subtitle }}</span></span>
      <span class="plan-count">{{ completed }}/{{ plan.tasks.length }}</span>
      <span class="plan-chevron">{{ collapsed ? '展开 ▴' : '收起 ▾' }}</span>
    </button>
    <div class="plan-progress" role="progressbar" aria-label="计划完成进度" :aria-valuenow="completed" :aria-valuemin="0" :aria-valuemax="plan.tasks.length || 1" :aria-valuetext="`已完成 ${completed} 项，共 ${plan.tasks.length} 项`">
      <span :style="{ width: `${percent}%` }" />
    </div>
    <Transition name="plan-rise">
    <div v-show="!collapsed" :id="`plan-${plan.generation_id}`" class="plan-popover">
    <ol class="plan-list">
      <li v-for="task in plan.tasks" :key="task.id" :class="taskState(task.status)">
        <span class="task-marker" aria-hidden="true">{{ task.status === 'succeeded' ? '✓' : taskState(task.status) === 'failed' ? '!' : task.sequence_no }}</span>
        <div class="task-copy">
          <div class="task-title"><span :title="task.title">{{ task.title }}</span><small>{{ taskLabel(task.status) }}</small></div>
        </div>
      </li>
    </ol>
    <p v-if="note" class="plan-note">{{ note }}</p>
    </div>
    </Transition>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { GenerationPlan } from "../types";

const props = defineProps<{ plan: GenerationPlan; collapsed?: boolean }>();
defineEmits<{ toggle: [] }>();
const completed = computed(() => props.plan.tasks.filter(task => task.status === "succeeded").length);
const percent = computed(() => props.plan.tasks.length ? Math.round(completed.value / props.plan.tasks.length * 100) : 0);
const active = computed(() => ["pending", "running"].includes(props.plan.status));
const subtitle = computed(() => {
  if (active.value) {
    const task = props.plan.tasks.find(task => task.status === "running");
    return task ? `正在执行 · ${task.title}` : completed.value === props.plan.tasks.length ? "计划项已完成，正在校验交付" : "计划已就绪，等待执行";
  }
  return ({ succeeded: "生成已完成", failed: "生成失败，已保留执行进度", cancelled: "已取消，已保留执行进度", timed_out: "执行超时，已保留执行进度", interrupted: "执行中断，已保留执行进度" } as Record<string, string>)[props.plan.status] || "实施计划";
});
const note = computed(() => props.plan.status === "succeeded" && completed.value < props.plan.tasks.length
  ? "本次生成未逐项执行此计划，未执行项不计入完成进度。" : "");
function taskState(status: string) {
  if (status === "running" && !active.value) return props.plan.status === "failed" ? "failed" : "interrupted";
  return status;
}
function taskLabel(status: string) {
  const state = taskState(status);
  if (state === "pending" && !active.value) return "未执行";
  return ({ pending: "待执行", running: "执行中", succeeded: "已完成", failed: "失败", skipped: "已跳过", interrupted: "已停止" } as Record<string, string>)[state] || state;
}
</script>

<style scoped>
.plan-card { position:relative; margin:0 14px; border:1px solid #d9e1f3; border-bottom:0; border-radius:12px 12px 0 0; background:#f9fbff; color:#2c3b59; }
.plan-popover { position:absolute; bottom:100%; left:-1px; right:-1px; max-height:min(208px, 28dvh); overflow-y:auto; overscroll-behavior:contain; scrollbar-width:thin; border:1px solid #d9e1f3; border-radius:10px 10px 0 0; background:#f9fbff; box-shadow:0 -6px 20px rgba(34,51,88,.09); transform-origin:bottom; }
.plan-rise-enter-active, .plan-rise-leave-active { transition:opacity .18s ease, transform .18s ease; }
.plan-rise-enter-from, .plan-rise-leave-to { opacity:0; transform:translateY(12px); }
.plan-heading { display:flex; align-items:center; gap:8px; width:100%; min-height:38px; padding:7px 12px; border:0; background:transparent; color:inherit; text-align:left; cursor:pointer; }
.plan-heading:focus-visible { outline:2px solid #6177cf; outline-offset:-3px; border-radius:12px; }
.plan-icon { display:grid; place-items:center; flex-shrink:0; width:20px; height:20px; color:#5064ac; font-size:18px; }
.plan-heading-copy { display:flex; align-items:center; gap:8px; min-width:0; flex:1; }
.plan-heading-copy strong { flex-shrink:0; font-size:12px; line-height:20px; font-weight:650; }
.plan-heading-copy > span { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:11px; color:#76839c; }
.plan-count { flex-shrink:0; padding:2px 6px; border-radius:4px; background:#eaf0fb; color:#5064ac; font-size:11px; line-height:16px; font-variant-numeric:tabular-nums; }
.plan-chevron { flex-shrink:0; color:#73819a; font-size:12px; }
.plan-progress { height:2px; background:#e6ecf6; }
.plan-progress > span { display:block; height:100%; background:#6b84d5; transition:width .25s ease; }
.plan-list { display:grid; gap:2px; list-style:none; margin:0; padding:6px; }
.plan-list li { display:flex; align-items:center; gap:8px; min-height:30px; box-sizing:border-box; padding:5px 7px; border-radius:5px; }
.plan-list li.running { background:#edf2ff; }
.task-marker { display:grid; place-items:center; flex-shrink:0; width:16px; height:16px; box-sizing:border-box; border:1px solid #ccd5e5; border-radius:50%; color:#8b97aa; font-size:10px; }
.task-copy { min-width:0; flex:1; }
.task-title { display:flex; align-items:center; justify-content:space-between; gap:8px; font-size:12px; line-height:20px; }
.task-title > span { min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.task-title small { flex-shrink:0; color:#8b97aa; font-size:11px; }
.running .task-marker { border-color:#7389d5; background:#e9efff; color:#5065b7; box-shadow:0 0 0 3px #edf1fc; }
.running .task-title { color:#4e65b7; font-weight:600; }
.running .task-title small { color:#5c74c4; }
.succeeded .task-marker { border-color:#b5dcc9; background:#eaf7f0; color:#398462; }
.succeeded .task-title small { color:#398462; }
.failed .task-marker { border-color:#e9bfc4; background:#fff0f0; color:#b45059; }
.failed .task-title small { color:#b45059; }
.plan-note { margin:0; padding:6px 12px; border-top:1px solid #e6ecf6; color:#7b879a; font-size:11px; line-height:16px; }
@media (prefers-reduced-motion: reduce) { .plan-progress > span, .plan-rise-enter-active, .plan-rise-leave-active { transition:none; } }
</style>
