<template>
  <div class="rail">
    <div
      v-for="(s, idx) in stages"
      :key="s.key"
      class="item"
      :class="{ active: s.key === stage, done: idx < activeIndex }"
    >
      <div class="track">
        <span class="dot">
          <span v-if="s.key === stage" class="pulse" />
          <template v-else>{{ idx < activeIndex ? "✓" : idx + 1 }}</template>
        </span>
        <span
          v-if="idx < stages.length - 1"
          class="connector"
          :class="{ lit: idx < activeIndex }"
        />
      </div>
      <span class="label">{{ s.title }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{ stage: string }>();

const stages = [
  { key: "parse", title: "解析" },
  { key: "plan", title: "规划" },
  { key: "generate", title: "生成" },
  { key: "build", title: "构建" },
  { key: "repair", title: "修复" },
  { key: "done", title: "完成" },
];

const activeIndex = computed(() => {
  const index = stages.findIndex((s) => s.key === props.stage);
  return index === -1 ? 0 : index;
});
</script>

<style scoped>
.rail {
  display: flex;
  align-items: flex-start;
}
.item {
  flex: 1;
  min-width: 0;
}
.track {
  display: flex;
  align-items: center;
}
.dot {
  position: relative;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: 1.5px solid var(--line-strong);
  background: var(--paper);
  color: var(--faint);
  font-family: var(--font-mono);
  font-size: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.item.done .dot {
  background: var(--green-soft);
  border-color: var(--green);
  color: var(--green);
}
.item.active .dot {
  border-color: var(--amber);
  background: var(--amber-soft);
  color: var(--amber);
}
.pulse {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--amber);
  animation: pulse 1.2s ease-in-out infinite;
}
@keyframes pulse {
  0%,
  100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.45;
    transform: scale(0.75);
  }
}
.connector {
  flex: 1;
  height: 1.5px;
  background: var(--line);
  margin: 0 8px;
}
.connector.lit {
  background: var(--green);
}
.label {
  display: block;
  margin-top: 6px;
  font-size: 12px;
  color: var(--muted);
  white-space: nowrap;
}
.item.active .label {
  color: var(--amber);
  font-weight: 600;
}
</style>
