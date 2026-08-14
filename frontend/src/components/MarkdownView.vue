<template>
  <div class="md" v-html="html" />
</template>

<script setup lang="ts">
import { computed } from "vue";
import { Marked } from "marked";
import { markedHighlight } from "marked-highlight";
import DOMPurify from "dompurify";
import hljs from "highlight.js/lib/core";
import "highlight.js/styles/github-dark.css";
import javascript from "highlight.js/lib/languages/javascript";
import typescript from "highlight.js/lib/languages/typescript";
import xml from "highlight.js/lib/languages/xml";
import css from "highlight.js/lib/languages/css";
import json from "highlight.js/lib/languages/json";
import bash from "highlight.js/lib/languages/bash";
import python from "highlight.js/lib/languages/python";
import markdown from "highlight.js/lib/languages/markdown";

hljs.registerLanguage("javascript", javascript);
hljs.registerLanguage("typescript", typescript);
hljs.registerLanguage("xml", xml);
hljs.registerLanguage("css", css);
hljs.registerLanguage("json", json);
hljs.registerLanguage("bash", bash);
hljs.registerLanguage("python", python);
hljs.registerLanguage("markdown", markdown);

const marked = new Marked();
marked.use(
  markedHighlight({
    langPrefix: "hljs language-",
    highlight(code, lang) {
      const language = lang && hljs.getLanguage(lang) ? lang : "plaintext";
      return hljs.highlight(code, { language }).value;
    },
  })
);
marked.setOptions({ gfm: true, breaks: true });

const props = defineProps<{ content: string }>();
const html = computed(() =>
  DOMPurify.sanitize(marked.parse(props.content) as string)
);
</script>

<style scoped>
.md {
  font-size: 14px;
  line-height: 1.65;
  word-break: break-word;
}
.md :deep(p) {
  margin: 0 0 8px;
}
.md :deep(p:last-child) {
  margin-bottom: 0;
}
.md :deep(h1),
.md :deep(h2),
.md :deep(h3),
.md :deep(h4) {
  font-family: var(--font-display);
  margin: 12px 0 6px;
  line-height: 1.3;
}
.md :deep(h1) {
  font-size: 18px;
}
.md :deep(h2) {
  font-size: 16px;
}
.md :deep(h3),
.md :deep(h4) {
  font-size: 14px;
}
.md :deep(ul),
.md :deep(ol) {
  padding-left: 20px;
  margin: 0 0 8px;
}
.md :deep(li) {
  margin: 2px 0;
}
.md :deep(a) {
  color: var(--primary);
  text-decoration: underline;
}
.md :deep(blockquote) {
  border-left: 3px solid var(--primary);
  background: var(--primary-soft);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  margin: 8px 0;
  padding: 6px 12px;
  color: var(--muted);
}
.md :deep(code) {
  font-family: var(--font-mono);
  font-size: 12.5px;
  background: var(--canvas-deep);
  border: 1px solid var(--line);
  padding: 1px 5px;
  border-radius: 5px;
}
.md :deep(pre) {
  background: var(--warm-dark);
  border-radius: var(--radius-md);
  padding: 12px 14px;
  margin: 8px 0;
  overflow: auto;
  max-height: 340px;
}
.md :deep(pre code) {
  background: transparent;
  border: none;
  padding: 0;
  font-size: 12.5px;
  color: #e8e2d8;
  white-space: pre;
}
.md :deep(table) {
  border-collapse: collapse;
  margin: 8px 0;
  font-size: 13px;
}
.md :deep(th),
.md :deep(td) {
  border: 1px solid var(--line-strong);
  padding: 5px 10px;
  text-align: left;
}
.md :deep(th) {
  background: var(--canvas);
}
.md :deep(hr) {
  border: none;
  border-top: 1px solid var(--line);
  margin: 12px 0;
}
</style>
