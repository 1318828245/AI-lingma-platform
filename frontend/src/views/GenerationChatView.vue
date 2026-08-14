<template>
  <div class="workspace">
    <header class="topbar">
      <div class="left">
        <button class="back" title="返回项目列表" @click="$router.push('/')">←</button>
        <div>
          <p class="eyebrow">AI · Lingma Studio</p>
          <h1 class="name">{{ project?.name || "生成对话" }}</h1>
        </div>
      </div>
      <div class="right">
        <span class="state" :class="genStateClass">{{ genStateLabel }}</span>
        <button
          class="ghost"
          title="在新页面单独查看预览"
          @click="$router.push(`/projects/${projectId}/preview`)"
        >
          全屏预览
        </button>
      </div>
    </header>

    <div class="split">
      <aside class="chat-pane">
        <section class="panel stage-card">
          <div class="stage-head">
            <span class="panel-title">构建流水线</span>
            <span v-if="runningGen" class="mono stage-meta">
              第 {{ runningGen.build_attempt }} 次构建
            </span>
          </div>
          <StageRail :stage="progressStage" />
          <el-alert
            v-if="runningGen?.error"
            :title="runningGen.error"
            type="error"
            :closable="false"
            class="error-line"
          />
        </section>

        <section class="panel chat-card">
          <div ref="chatListRef" class="chat-list">
            <div v-if="!entries.length" class="empty-tip">
              <p class="empty-mark" aria-hidden="true">✦</p>
              <p class="empty-title">从这里开始</p>
              <p>描述你想做的页面，比如：</p>
              <p class="mono example">“做一个深色风格的个人名片页，展示技能与作品”</p>
            </div>

            <template v-for="entry in entries" :key="entry.id">
              <!-- 用户消息 -->
              <div v-if="entry.kind === 'user'" class="chat-msg user">
                <div class="bubble">
                  <span class="who mono">你</span>
                  <p>{{ entry.content }}</p>
                </div>
              </div>

              <!-- AI 消息 -->
              <div v-else-if="entry.kind === 'assistant'" class="chat-msg">
                <div class="bubble" :class="{ streaming: entry.streaming }">
                  <span class="who mono">灵码</span>
                  <MarkdownView
                    v-if="!entry.streaming && entry.content"
                    :content="entry.content"
                  />
                  <p v-else>{{ entry.content }}</p>
                </div>
              </div>

              <!-- 阶段 -->
              <div v-else-if="entry.kind === 'stage'" class="entry stage-entry">
                <span class="stage-dot" />
                <span class="entry-title">
                  进入<b>「{{ entry.stageTitle }}」</b>阶段
                </span>
                <span class="entry-hint">{{ entry.stageHint }}</span>
              </div>

              <!-- 思考（可折叠） -->
              <div
                v-else-if="entry.kind === 'think'"
                class="entry collapsible"
                :class="{ open: !entry.collapsed, streaming: entry.streaming }"
                role="button"
                tabindex="0"
                @click="entry.collapsed = !entry.collapsed"
                @keydown.enter="entry.collapsed = !entry.collapsed"
              >
                <span class="entry-icon think">
                  <span v-if="entry.streaming" class="spinner-ring amber" />
                  <ToolIcon v-else name="think" />
                </span>
                <span class="entry-title">思考</span>
                <span v-if="entry.streaming" class="entry-hint streaming-hint">
                  思考中…
                </span>
                <span class="chevron" aria-hidden="true">
                  {{ entry.collapsed ? "▸" : "▾" }}
                </span>
                <p v-if="!entry.collapsed" class="entry-body think-body">
                  {{ entry.content }}
                </p>
              </div>

              <!-- 工具调用 -->
              <div
                v-else-if="entry.kind === 'tool'"
                class="entry tool-entry"
                :class="{ pending: entry.pending, fail: entry.ok === false }"
              >
                <span class="entry-icon">
                  <span v-if="entry.pending" class="spinner-ring" />
                  <ToolIcon
                    v-else
                    :name="entry.ok === false ? 'alert' : toolIcon(entry.tool)"
                  />
                </span>
                <span class="mono tool-name">{{ toolLabel(entry.tool) }}</span>
                <span v-if="entry.pending" class="entry-hint">调用中…</span>
                <span v-if="entry.detail" class="entry-detail mono">{{ entry.detail }}</span>
                <span v-if="entry.ok === false" class="entry-hint fail-hint">失败</span>
              </div>

              <!-- 写入文件 -->
              <div v-else-if="entry.kind === 'file'" class="entry file-entry">
                <span class="entry-icon ok"><ToolIcon name="check" /></span>
                <span class="entry-detail mono">{{ entry.detail }}</span>
              </div>

              <!-- 构建日志（可折叠） -->
              <div
                v-else-if="entry.kind === 'build'"
                class="entry collapsible build-entry"
                :class="{ open: !entry.collapsed }"
                role="button"
                tabindex="0"
                @click="entry.collapsed = !entry.collapsed"
                @keydown.enter="entry.collapsed = !entry.collapsed"
              >
                <span class="entry-icon"><ToolIcon name="terminal" /></span>
                <span class="entry-title">构建日志</span>
                <span class="entry-hint">（{{ entry.lines?.length }} 行）</span>
                <span class="chevron" aria-hidden="true">
                  {{ entry.collapsed ? "▸" : "▾" }}
                </span>
                <div v-if="!entry.collapsed" class="build-lines">
                  <p v-for="(line, idx) in entry.lines" :key="idx">{{ line }}</p>
                </div>
              </div>

              <!-- 错误 -->
              <div v-else-if="entry.kind === 'error'" class="entry error-entry">
                <span class="entry-icon bad"><ToolIcon name="alert" /></span>
                <span class="entry-title">出错了</span>
                <p class="entry-body">{{ entry.content }}</p>
              </div>

              <!-- 提示 -->
              <div v-else-if="entry.kind === 'info'" class="entry info-entry">
                <span class="entry-icon"><ToolIcon name="info" /></span>
                <span class="entry-title">{{ entry.content }}</span>
              </div>
            </template>
          </div>

          <div class="input-row">
            <el-input
              v-model="requirement"
              type="textarea"
              :rows="3"
              :disabled="!!runningGen"
              placeholder="描述需求，右侧预览会随生成实时更新…"
              @keydown.enter.exact.prevent="submitRequirement"
            />
            <div class="input-side">
              <el-button
                type="primary"
                :loading="submitting"
                :disabled="!!runningGen"
                @click="submitRequirement"
              >
                生成
              </el-button>
              <el-button
                v-if="runningGen?.status === 'running'"
                type="danger"
                plain
                @click="cancel"
              >
                取消
              </el-button>
              <span class="mono input-hint">Enter 发送 · Shift+Enter 换行</span>
            </div>
          </div>
        </section>
      </aside>

      <main class="preview-pane">
        <LivePreviewPanel
          :project-id="projectId"
          :stage="progressStage"
          :running="!!runningGen"
          :build-attempt="runningGen?.build_attempt || 0"
          :refresh-token="previewRefresh"
        />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import LivePreviewPanel from "../components/LivePreviewPanel.vue";
import MarkdownView from "../components/MarkdownView.vue";
import StageRail from "../components/StageRail.vue";
import ToolIcon from "../components/ToolIcon.vue";
import { stageInfo } from "../constants/stages";
import {
  cancelGeneration,
  createGeneration,
  generationEventUrl,
  getGeneration,
} from "../api/generations";
import { getProject, listMessages, listSessions } from "../api/projects";
import type {
  Generation,
  Message,
  Project,
  SseEvent,
} from "../types";

interface ChatEntry {
  id: number;
  kind:
    | "user"
    | "assistant"
    | "stage"
    | "think"
    | "tool"
    | "file"
    | "build"
    | "error"
    | "info";
  content?: string;
  stageTitle?: string;
  stageHint?: string;
  tool?: string;
  detail?: string;
  lines?: string[];
  collapsed?: boolean;
  streaming?: boolean;
  pending?: boolean;
  ok?: boolean;
}

const route = useRoute();
const router = useRouter();
const projectId = Number(route.params.id);

const project = ref<Project | null>(null);
const requirement = ref("");
const entries = ref<ChatEntry[]>([]);
const runningGen = ref<Generation | null>(null);
const progressStage = ref("parse");
const submitting = ref(false);
const previewRefresh = ref(0);
const streamTick = ref(0);
const chatListRef = ref<HTMLElement | null>(null);
let eventSource: EventSource | null = null;
let seq = 0;
let thinkBuffer = "";
let assistantBuffer = "";
let flushTimer: ReturnType<typeof setTimeout> | null = null;

function push(partial: Omit<ChatEntry, "id">) {
  const entry: ChatEntry = { id: ++seq, collapsed: true, ...partial };
  entries.value.push(entry);
  return entry;
}

async function scrollToBottom() {
  await nextTick();
  const el = chatListRef.value;
  if (!el) return;
  // 用户向上翻阅时不强行拉回底部
  if (el.scrollHeight - el.scrollTop - el.clientHeight > 140) return;
  el.scrollTop = el.scrollHeight;
}

watch(() => entries.value.length, scrollToBottom);
watch(streamTick, scrollToBottom);

function bumpStream() {
  streamTick.value += 1;
}

function lastEntry() {
  return entries.value[entries.value.length - 1];
}

function queueDelta(kind: "think" | "assistant", text: string) {
  if (kind === "think") thinkBuffer += text;
  else assistantBuffer += text;
  if (flushTimer === null) {
    flushTimer = setTimeout(flushBuffers, 40);
  }
}

function flushBuffers() {
  if (flushTimer !== null) {
    clearTimeout(flushTimer);
    flushTimer = null;
  }
  if (thinkBuffer) {
    let entry = lastEntry();
    if (entry?.kind !== "think" || !entry.streaming) {
      entry = push({
        kind: "think",
        content: "",
        streaming: true,
        collapsed: false,
      });
    }
    entry.content = (entry.content || "") + thinkBuffer;
    thinkBuffer = "";
  }
  if (assistantBuffer) {
    let entry = lastEntry();
    if (entry?.kind !== "assistant" || !entry.streaming) {
      entry = push({
        kind: "assistant",
        content: "",
        streaming: true,
        collapsed: false,
      });
    }
    entry.content = (entry.content || "") + assistantBuffer;
    assistantBuffer = "";
  }
  bumpStream();
}

const genStateLabel = computed(() => {
  if (!runningGen.value) return "待命";
  const status = runningGen.value.status;
  if (status === "succeeded") return "已完成";
  if (status === "failed") return "失败";
  if (status === "cancelled") return "已取消";
  if (status === "running") return "生成中";
  return status;
});
const genStateClass = computed(() => {
  const status = runningGen.value?.status;
  if (status === "succeeded") return "ok";
  if (status === "failed" || status === "cancelled") return "bad";
  if (status === "running") return "run";
  return "";
});

function toolLabel(tool?: string) {
  const map: Record<string, string> = {
    write_file: "写入文件",
    edit_file: "修改文件",
    run_command: "运行命令",
    read_file: "读取文件",
    list_files: "查看文件",
    finish: "完成",
  };
  return map[tool || ""] || tool || "工具";
}

function toolIcon(tool?: string) {
  if (tool === "write_file" || tool === "edit_file") return "pencil";
  if (tool === "run_command") return "terminal";
  if (tool === "read_file" || tool === "list_files") return "folder";
  if (tool === "finish") return "flag";
  return "info";
}

onMounted(async () => {
  project.value = await getProject(projectId);
  const sessions = await listSessions(projectId);
  if (sessions.length) {
    const history = (await listMessages(sessions[0].id)) as Message[];
    entries.value = historyToEntries(history);
  }
});

function historyToEntries(history: Message[]): ChatEntry[] {
  const list: ChatEntry[] = [];
  for (const m of history) {
    if (m.role === "user") {
      list.push({ id: ++seq, kind: "user", content: m.content, collapsed: false });
      continue;
    }
    if (m.msg_type === "summary") {
      list.push({ id: ++seq, kind: "assistant", content: m.content, collapsed: false });
      continue;
    }
    if (m.msg_type === "stage") {
      const info = stageInfo(m.content);
      list.push({
        id: ++seq,
        kind: "stage",
        stageTitle: info.title,
        stageHint: info.hint,
        collapsed: false,
      });
      continue;
    }
    if (m.msg_type === "think") {
      list.push({ id: ++seq, kind: "think", content: m.content, collapsed: false });
      continue;
    }
    if (m.msg_type === "tool_call") {
      const tj = (m.tool_call_json || {}) as {
        tool?: string;
        ok?: boolean;
        detail?: string;
      };
      list.push({
        id: ++seq,
        kind: "tool",
        tool: tj.tool || "",
        detail: m.content || tj.detail || "",
        pending: false,
        ok: tj.ok !== false,
        collapsed: false,
      });
      continue;
    }
    if (m.msg_type === "file_written") {
      const last = list[list.length - 1];
      if (last?.kind === "tool" && last.detail === m.content) continue;
      list.push({ id: ++seq, kind: "file", detail: m.content, collapsed: false });
      continue;
    }
    if (m.msg_type === "build_log") {
      const last = list[list.length - 1];
      if (last?.kind === "build") last.lines?.push(m.content);
      else list.push({ id: ++seq, kind: "build", lines: [m.content], collapsed: true });
      continue;
    }
    if (m.msg_type === "error") {
      list.push({ id: ++seq, kind: "error", content: m.content, collapsed: false });
      continue;
    }
    if (m.msg_type === "info") {
      list.push({ id: ++seq, kind: "info", content: m.content, collapsed: false });
      continue;
    }
    list.push({ id: ++seq, kind: "assistant", content: m.content, collapsed: false });
  }
  return list;
}

onBeforeUnmount(() => {
  if (flushTimer !== null) clearTimeout(flushTimer);
  eventSource?.close();
});

async function submitRequirement() {
  const text = requirement.value.trim();
  if (!text) {
    ElMessage.warning("先描述一下你的需求");
    return;
  }
  submitting.value = true;
  try {
    push({ kind: "user", content: text });
    const gen = await createGeneration(projectId, text);
    requirement.value = "";
    runningGen.value = gen;
    progressStage.value = "parse";
    previewRefresh.value += 1;
    watchGeneration(gen.id);
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || "提交失败，请重试");
  } finally {
    submitting.value = false;
  }
}

function watchGeneration(genId: number) {
  eventSource?.close();
  eventSource = new EventSource(generationEventUrl(genId));

  eventSource.addEventListener("stage", (e) => {
    const event = JSON.parse((e as MessageEvent).data) as SseEvent;
    const stage = String(event.stage);
    progressStage.value = stage;
    const info = stageInfo(stage);
    push({
      kind: "stage",
      stageTitle: info.title,
      stageHint: info.hint,
    });
    if (stage === "build") {
      push({ kind: "build", lines: [] });
    }
  });

  eventSource.addEventListener("thought", (e) => {
    const event = JSON.parse((e as MessageEvent).data) as SseEvent;
    const content = String(event.content || "").trim();
    if (content) {
      push({ kind: "think", content, collapsed: false });
    }
  });

  eventSource.addEventListener("reasoning_delta", (e) => {
    const event = JSON.parse((e as MessageEvent).data) as SseEvent;
    const text = String(event.text || "");
    if (text) queueDelta("think", text);
  });

  eventSource.addEventListener("assistant_delta", (e) => {
    const event = JSON.parse((e as MessageEvent).data) as SseEvent;
    const text = String(event.text || "");
    if (text) queueDelta("assistant", text);
  });

  eventSource.addEventListener("tool_call_started", (e) => {
    flushBuffers();
    const event = JSON.parse((e as MessageEvent).data) as SseEvent;
    const tool = String(event.tool || "");
    const args = (event.args || {}) as Record<string, unknown>;
    let detail = "";
    if (typeof args.path === "string") detail = args.path;
    else if (Array.isArray(args.command)) detail = args.command.join(" ");
    const previous = lastEntry();
    if (previous?.kind === "think" && previous.streaming) {
      previous.streaming = false;
    }
    push({ kind: "tool", tool, detail, pending: true });
    bumpStream();
  });

  eventSource.addEventListener("tool_call_completed", (e) => {
    const event = JSON.parse((e as MessageEvent).data) as SseEvent;
    const tool = String(event.tool || "");
    const entry = [...entries.value]
      .reverse()
      .find((item) => item.kind === "tool" && item.tool === tool && item.pending);
    if (entry) {
      entry.pending = false;
      entry.ok = event.ok !== false;
      if (!entry.detail && event.detail) entry.detail = String(event.detail);
    }
    bumpStream();
  });

  // mock 模式兼容：单条 tool_call 事件（无 started/completed）
  eventSource.addEventListener("tool_call", (e) => {
    const event = JSON.parse((e as MessageEvent).data) as SseEvent;
    const tool = String(event.tool || "");
    const args = (event.args || {}) as Record<string, unknown>;
    let detail = "";
    if (typeof args.path === "string") detail = args.path;
    else if (Array.isArray(args.command)) detail = args.command.join(" ");
    push({ kind: "tool", tool, detail, pending: false, ok: true });
    bumpStream();
  });

  eventSource.addEventListener("file_written", (e) => {
    const event = JSON.parse((e as MessageEvent).data) as SseEvent;
    const path = String(event.path || "");
    const last = entries.value[entries.value.length - 1];
    // 写入工具的 tool_call 已带同一 path，避免重复展示
    if (last?.kind === "tool" && last.detail === path) return;
    push({ kind: "file", detail: path });
  });

  eventSource.addEventListener("build_log", (e) => {
    const event = JSON.parse((e as MessageEvent).data) as SseEvent;
    let group = entries.value[entries.value.length - 1];
    if (group?.kind !== "build") {
      push({ kind: "build", lines: [] });
      group = entries.value[entries.value.length - 1];
    }
    group.lines?.push(String(event.line || ""));
  });

  eventSource.addEventListener("completed", (e) => {
    flushBuffers();
    const event = JSON.parse((e as MessageEvent).data) as SseEvent;
    const summary = String(event.summary || "");
    const previous = lastEntry();
    if (previous?.kind === "assistant" && previous.streaming) {
      previous.content = summary;
      previous.streaming = false;
    } else {
      push({ kind: "assistant", content: summary, collapsed: false });
    }
    progressStage.value = "done";
    eventSource?.close();
    previewRefresh.value += 1;
    refreshStatus(event.generation_id as number);
  });

  eventSource.addEventListener("error", (e) => {
    flushBuffers();
    const event = JSON.parse((e as MessageEvent).data) as SseEvent;
    push({ kind: "error", content: String(event.error || "任务失败了") });
    progressStage.value = "done";
    eventSource?.close();
    refreshStatus();
  });

  eventSource.addEventListener("cancelled", () => {
    flushBuffers();
    push({ kind: "info", content: "已取消这次生成" });
    progressStage.value = "done";
    eventSource?.close();
    refreshStatus();
  });

  eventSource.onerror = () => {
    eventSource?.close();
    refreshStatus();
  };
}

async function refreshStatus(genId?: number) {
  const id = genId ?? runningGen.value?.id;
  if (!id) return;
  const gen = await getGeneration(id);
  runningGen.value = gen;
  if (["succeeded", "failed", "cancelled", "timed_out"].includes(gen.status)) {
    eventSource?.close();
  }
}

async function cancel() {
  if (!runningGen.value) return;
  await cancelGeneration(runningGen.value.id);
  ElMessage.info("已请求取消");
}
</script>

<style scoped>
.workspace {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--canvas);
}
.topbar {
  height: 58px;
  background: var(--paper);
  border-bottom: 1px solid var(--line);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 18px;
  flex-shrink: 0;
}
.topbar .eyebrow {
  color: var(--amber);
  margin-bottom: 2px;
}
.left {
  display: flex;
  align-items: center;
  gap: 14px;
}
.back {
  width: 34px;
  height: 34px;
  border-radius: var(--radius-md);
  border: 1px solid var(--line-strong);
  background: var(--paper);
  color: var(--muted);
  font-size: 16px;
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s, background 0.15s;
}
.back:hover {
  color: var(--primary);
  border-color: var(--primary);
  background: var(--primary-soft);
}
.name {
  font-family: var(--font-display);
  font-size: 17px;
  font-weight: 600;
}
.right {
  display: flex;
  align-items: center;
  gap: 10px;
}
.state {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.06em;
  padding: 4px 12px;
  border-radius: 999px;
  border: 1px solid var(--line-strong);
  color: var(--muted);
  background: var(--canvas);
}
.state.ok {
  color: var(--green);
  border-color: rgba(47, 158, 111, 0.35);
  background: var(--green-soft);
}
.state.bad {
  color: var(--red);
  border-color: rgba(224, 91, 91, 0.35);
  background: var(--red-soft);
}
.state.run {
  color: #b97f1c;
  border-color: rgba(242, 169, 59, 0.4);
  background: var(--amber-soft);
}
.ghost {
  border: 1px solid var(--line-strong);
  background: var(--paper);
  color: var(--ink);
  padding: 7px 14px;
  border-radius: var(--radius-md);
  font-size: 13px;
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s, background 0.15s;
}
.ghost:hover {
  color: var(--primary);
  border-color: var(--primary);
  background: var(--primary-soft);
}
.split {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(430px, 44%) 1fr;
}
.chat-pane {
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  overflow-y: auto;
  border-right: 1px solid var(--line);
}
.stage-card {
  padding: 14px 16px;
  flex-shrink: 0;
}
.stage-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.stage-meta {
  font-size: 11px;
  color: var(--faint);
}
.error-line {
  margin-top: 12px;
}
.chat-card {
  flex: 1;
  min-height: 260px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.chat-list {
  flex: 1;
  overflow-y: auto;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.chat-msg {
  display: flex;
}
.chat-msg.user {
  justify-content: flex-end;
}
.bubble {
  max-width: 82%;
  padding: 10px 14px;
  border-radius: 16px;
  background: var(--paper);
  border: 1px solid var(--line);
  box-shadow: var(--shadow-sm);
}
.chat-msg.user .bubble {
  background: var(--primary-soft);
  border-color: transparent;
}
.who {
  display: block;
  font-size: 10px;
  letter-spacing: 0.1em;
  color: var(--faint);
  margin-bottom: 4px;
}
.chat-msg.user .who {
  color: var(--primary);
}
.bubble p {
  font-size: 14px;
  line-height: 1.65;
  white-space: pre-wrap;
}
.empty-tip {
  margin: 32px auto;
  text-align: center;
  color: var(--muted);
  font-size: 14px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}
.empty-mark {
  font-size: 30px;
  color: var(--primary);
  opacity: 0.5;
}
.empty-title {
  color: var(--ink);
  font-weight: 600;
  font-size: 15px;
}
.example {
  display: inline-block;
  margin-top: 6px;
  padding: 7px 12px;
  background: var(--amber-soft);
  border-radius: var(--radius-sm);
  font-size: 12px;
  color: #9a6b16;
}

/* 对话内事件流 */
.entry {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding: 7px 10px;
  border-radius: var(--radius-md);
  background: var(--canvas);
  border: 1px solid var(--line);
  font-size: 13px;
  line-height: 1.5;
  color: var(--ink);
}
.entry-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 7px;
  background: var(--primary-soft);
  color: var(--primary);
  flex-shrink: 0;
}
.entry-icon.think {
  background: var(--amber-soft);
  color: #b97f1c;
}
.entry-icon.ok {
  background: var(--green-soft);
  color: var(--green);
}
.entry-icon.bad {
  background: var(--red-soft);
  color: var(--red);
}
.entry-title {
  font-weight: 600;
}
.entry-hint {
  color: var(--muted);
  font-size: 12px;
}
.entry-detail {
  font-size: 12px;
  color: var(--muted);
  word-break: break-all;
  min-width: 0;
}
.tool-name {
  font-size: 12px;
  color: var(--primary-dark);
}
.stage-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--amber);
  box-shadow: 0 0 0 3px var(--amber-soft);
  flex-shrink: 0;
}
.stage-entry .entry-title b {
  color: var(--ink);
}
.collapsible {
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}
.collapsible:hover {
  border-color: var(--line-strong);
  background: var(--paper);
}
.chevron {
  margin-left: auto;
  color: var(--faint);
  font-size: 12px;
}
.entry-body {
  flex-basis: 100%;
  margin-top: 2px;
  padding: 8px 10px;
  background: var(--paper);
  border-radius: var(--radius-sm);
  border: 1px solid var(--line);
  font-size: 13px;
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--ink);
}
.think-body {
  max-height: 240px;
  overflow-y: auto;
  overscroll-behavior: contain;
}
.build-lines {
  flex-basis: 100%;
  max-height: 220px;
  overflow-y: auto;
  background: var(--warm-dark);
  border-radius: var(--radius-sm);
  padding: 8px 10px;
  margin-top: 2px;
}
.build-lines p {
  font-family: var(--font-mono);
  font-size: 12px;
  color: #e8e2d8;
  line-height: 1.7;
  word-break: break-all;
}
.error-entry {
  background: var(--red-soft);
  border-color: rgba(224, 91, 91, 0.35);
}
.error-entry .entry-body {
  border-color: rgba(224, 91, 91, 0.25);
  color: #a13a3a;
}
.info-entry {
  background: var(--primary-soft);
  border-color: rgba(91, 103, 241, 0.25);
}
.input-row {
  display: flex;
  gap: 10px;
  padding: 12px 14px;
  border-top: 1px solid var(--line);
}
.input-side {
  display: flex;
  flex-direction: column;
  gap: 8px;
  justify-content: flex-end;
  align-items: stretch;
}
.input-hint {
  font-size: 10px;
  color: var(--faint);
  text-align: center;
}
.preview-pane {
  min-width: 0;
  min-height: 0;
  padding: 16px 16px 16px 0;
}

/* 流式与工具状态 */
.spinner-ring {
  width: 13px;
  height: 13px;
  border-radius: 50%;
  border: 2px solid var(--line-strong);
  border-top-color: var(--primary);
  animation: spin 0.7s linear infinite;
  display: inline-block;
}
.spinner-ring.amber {
  border-top-color: var(--amber);
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
.tool-entry.pending {
  background: var(--amber-soft);
  border-color: rgba(242, 169, 59, 0.4);
}
.tool-entry.fail {
  background: var(--red-soft);
  border-color: rgba(224, 91, 91, 0.35);
}
.fail-hint {
  color: var(--red);
  font-weight: 600;
}
.streaming-hint {
  color: #b97f1c;
  font-weight: 500;
}
.entry.streaming {
  border-color: rgba(242, 169, 59, 0.45);
  background: var(--amber-soft);
}
.bubble.streaming p::after {
  content: "▍";
  color: var(--primary);
  margin-left: 1px;
  animation: blink 1s steps(2) infinite;
}
@keyframes blink {
  50% {
    opacity: 0;
  }
}

/* 响应式：窄屏上下堆叠 */
@media (max-width: 1024px) {
  .workspace {
    height: auto;
    min-height: 100vh;
  }
  .split {
    grid-template-columns: 1fr;
  }
  .chat-pane {
    border-right: none;
    overflow: visible;
  }
  .preview-pane {
    padding: 0 12px 16px;
    height: 56vh;
    min-height: 420px;
  }
}
</style>
