<template>
  <el-steps :active="activeIndex" align-center finish-status="success">
    <el-step v-for="s in steps" :key="s.key" :title="s.title" />
  </el-steps>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{ stage: string }>();

const steps = [
  { key: "parse", title: "解析" },
  { key: "plan", title: "规划" },
  { key: "generate", title: "生成" },
  { key: "build", title: "构建" },
  { key: "repair", title: "修复" },
  { key: "done", title: "完成" },
];

const activeIndex = computed(() => {
  const index = steps.findIndex((s) => s.key === props.stage);
  return index === -1 ? 0 : index;
});
</script>
