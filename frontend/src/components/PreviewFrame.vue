<template>
  <iframe
    :src="src"
    :style="{ width, height: '100%', border: 'none', background: '#fff' }"
    sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
    title="项目预览"
  />
</template>

<script setup lang="ts">
defineProps<{ src: string; width: string }>();
</script>
