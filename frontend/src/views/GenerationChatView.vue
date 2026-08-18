<template>
  <div class="workspace">
    <header class="topbar">
      <div class="left">
        <button class="back" title="返回项目列表" @click="$router.push('/')">←</button>
        <div class="brand-mark" aria-hidden="true">✦</div>
        <div>
          <p class="eyebrow">LINGMA / BUILD ROOM</p>
          <h1 class="name">{{ project?.name || "生成对话" }}</h1>
        </div>
      </div>
      <div class="right">
        <span class="state" :class="genStateClass">{{ genStateLabel }}</span>
        <button class="ghost" title="重命名项目" @click="renameProject">
          重命名
        </button>
        <button
          class="ghost"
          title="在新页面单独查看预览"
          @click="$router.push(`/projects/${projectId}/preview`)"
        >
          全屏预览
        </button>
      </div>
    </header>

    <div ref="splitRef" class="split" :style="{ gridTemplateColumns: `${chatWidth}px 10px minmax(360px, 1fr)` }">
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
                :class="{ open: !entry.collapsed, streaming: entry.streaming, 'think-entry': true }"
                role="button"
                tabindex="0"
                @click="toggleCollapsed(entry, $event)"
                @keydown.enter="toggleCollapsed(entry, $event)"
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
                <div v-if="!entry.collapsed" class="entry-body think-body">
                  <MarkdownView
                    v-if="!entry.streaming"
                    :content="entry.content || ''"
                  />
                  <p v-else>{{ entry.content }}</p>
                </div>
              </div>

              <!-- 工具调用组（连续调用合并为一个气泡，与思考平级） -->
              <div v-else-if="entry.kind === 'tools'" class="entry tools-entry">
                <span class="entry-icon"><ToolIcon name="tool" /></span>
                <div class="tools-body">
                  <div
                    v-for="(item, idx) in entry.items"
                    :key="idx"
                    class="tool-item"
                    :class="{ pending: item.pending, fail: item.ok === false }"
                  >
                    <span v-if="item.pending" class="spinner-ring" />
                    <ToolIcon
                      v-else
                      :name="item.ok === false ? 'alert' : toolIcon(item.tool)"
                    />
                    <span class="mono tool-name">{{ toolLabel(item.tool) }}</span>
                    <span v-if="item.pending" class="entry-hint">调用中…</span>
                    <span v-else-if="item.detail" class="entry-detail mono">
                      {{ item.detail }}
                    </span>
                    <span
                      v-if="item.ok === false"
                      class="entry-hint fail-hint"
                      :title="item.error || '工具执行失败'"
                    >
                      失败
                    </span>
                    <button
                      v-if="item.content"
                      class="file-toggle mono"
                      type="button"
                      @click.stop="item.codeOpen = !item.codeOpen"
                    >
                      {{ item.codeOpen ? "收起代码" : "查看代码" }}
                    </button>
                    <pre v-if="item.content && item.codeOpen" class="code-preview tool-code"><code>{{ item.content }}</code></pre>
                  </div>
                  <div v-if="toolsAllDone(entry)" class="tools-done">
                    <ToolIcon name="check" /> 完成
                  </div>
                </div>
              </div>

              <!-- 写入文件：独立代码记录，不混入工具气泡 -->
              <div v-else-if="entry.kind === 'file'" class="entry file-entry">
                <span class="entry-icon ok"><ToolIcon name="check" /></span>
                <div class="file-main">
                  <div class="file-head">
                    <span class="file-action">已写入</span>
                    <span class="entry-detail mono">{{ entry.detail }}</span>
                    <button
                      v-if="entry.content"
                      class="file-toggle mono"
                      type="button"
                      @click.stop="entry.codeOpen = !entry.codeOpen"
                    >
                      {{ entry.codeOpen ? "收起代码" : "查看代码" }}
                    </button>
                  </div>
                  <pre v-if="entry.content && entry.codeOpen" class="code-preview"><code>{{ entry.content }}</code></pre>
                </div>
              </div>

              <!-- 构建日志（可折叠） -->
              <div
                v-else-if="entry.kind === 'build'"
                class="entry collapsible build-entry"
                :class="{ open: !entry.collapsed }"
                role="button"
                tabindex="0"
                @click="toggleCollapsed(entry, $event)"
                @keydown.enter="toggleCollapsed(entry, $event)"
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

      <div
        ref="splitterRef"
        class="splitter"
        role="separator"
        aria-label="调整聊天和预览宽度"
        :aria-valuenow="chatWidth"
        aria-valuemin="360"
        aria-valuemax="900"
        tabindex="0"
        @pointerdown="startResize"
        @keydown.left.prevent="resizeBy(-24)"
        @keydown.right.prevent="resizeBy(24)"
      >
        <span class="splitter-grip" />
      </div>
      <main class="preview-pane">
        <LivePreviewPanel
          :project-id="projectId"
          :stage="progressStage"
          :running="!!runningGen"
          :build-attempt="runningGen?.build_attempt || 0"
          :refresh-token="previewRefresh"
          :selected-element="selectedElement"
          @element-selected="onElementSelected"
        >
          <template #overlay="{ style }">
            <div v-if="selectedElement" class="element-popover" :style="style">
              <ModifyPanel
                :project-id="projectId"
                :generation-id="runningGen?.id"
                :session-id="runningGen?.session_id"
                :element="selectedElement"
                @completed="onModificationCompleted"
              />
            </div>
          </template>
        </LivePreviewPanel>
        <button
          class="version-fab"
          :class="{ active: versionsOpen }"
          title="打开版本历史"
          @click="versionsOpen = !versionsOpen"
        >
          <span class="version-fab-mark">◷</span>
          <span>版本</span>
        </button>
        <VersionHistory
          v-if="versionsOpen"
          class="floating-version-history"
          :floating="true"
          :project-id="projectId"
          :refresh-token="previewRefresh"
          @rollback="onModificationCompleted"
        />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import LivePreviewPanel from "../components/LivePreviewPanel.vue";
import ModifyPanel from "../components/ModifyPanel.vue";
import VersionHistory from "../components/VersionHistory.vue";
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
import {
  getProject,
  listMessages,
  listSessions,
  updateProject,
} from "../api/projects";
import type {
  ElementSnapshot,
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
    | "tools"
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
  codeOpen?: boolean;
  pending?: boolean;
  ok?: boolean;
  items?: Array<{
    tool: string;
    detail: string;
    pending: boolean;
    ok?: boolean;
    error?: string;
    content?: string;
    codeOpen?: boolean;
  }>;
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
const selectedElement = ref<ElementSnapshot | null>(null);
const versionsOpen = ref(false);
const streamTick = ref(0);
const chatListRef = ref<HTMLElement | null>(null);
const splitRef = ref<HTMLElement | null>(null);
const splitterRef = ref<HTMLElement | null>(null);
const chatWidth = ref(560);
let resizeMove: ((event: PointerEvent) => void) | null = null;
let resizeEnd: (() => void) | null = null;
let eventSource: EventSource | null = null;
let seq = 0;
let thinkBuffer = "";
let assistantBuffer = "";
let flushTimer: ReturnType<typeof setTimeout> | null = null;
let activeThinkId: number | null = null;
let activeAssistantId: number | null = null;

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

function resizeBy(delta: number) {
  chatWidth.value = Math.min(900, Math.max(360, chatWidth.value + delta));
}

function onElementSelected(element: ElementSnapshot) {
  selectedElement.value = element;
}

function onModificationCompleted() {
  previewRefresh.value += 1;
}

function startResize(event: PointerEvent) {
  if (window.innerWidth <= 1024 || event.button !== 0) return;
  const splitter = splitterRef.value;
  const split = splitRef.value;
  if (!splitter || !split) return;

  const splitRect = split.getBoundingClientRect();
  const startX = event.clientX;
  const startWidth = chatWidth.value;
  const minWidth = 360;
  const rightMinWidth = 360;
  const dividerWidth = 10;
  const maxWidth = Math.max(
    minWidth,
    splitRect.width - rightMinWidth - dividerWidth,
  );

  document.body.classList.add("is-resizing");
  splitter.setPointerCapture?.(event.pointerId);
  resizeMove = (moveEvent: PointerEvent) => {
    const nextWidth = startWidth + moveEvent.clientX - startX;
    chatWidth.value = Math.min(maxWidth, Math.max(minWidth, nextWidth));
  };
  const finishResize = () => {
    document.body.classList.remove("is-resizing");
    if (resizeMove) window.removeEventListener("pointermove", resizeMove);
    window.removeEventListener("pointerup", finishResize);
    window.removeEventListener("pointercancel", finishResize);
    splitter.releasePointerCapture?.(event.pointerId);
    resizeMove = null;
    resizeEnd = null;
  };
  resizeEnd = finishResize;
  window.addEventListener("pointermove", resizeMove);
  window.addEventListener("pointerup", finishResize);
  window.addEventListener("pointercancel", finishResize);
}

function lastEntry() {
  return entries.value[entries.value.length - 1];
}

function toggleCollapsed(entry: ChatEntry, event: Event) {
  entry.collapsed = !entry.collapsed;
  if (!entry.collapsed) {
    const el = event.currentTarget as HTMLElement | null;
    nextTick(() => el?.scrollIntoView({ block: "nearest" }));
  }
}

function toolsAllDone(entry: ChatEntry) {
  const items = entry.items || [];
  return items.length > 0 && items.every((item) => !item.pending);
}

function queueDelta(kind: "think" | "assistant", text: string) {
  if (kind === "think") {
    if (activeThinkId === null) {
      const entry = push({
        kind: "think",
        content: "",
        streaming: true,
        collapsed: false,
      });
      activeThinkId = entry.id;
    }
    thinkBuffer += text;
  } else {
    if (activeAssistantId === null) {
      const entry = push({
        kind: "assistant",
        content: "",
        streaming: true,
        collapsed: false,
      });
      activeAssistantId = entry.id;
    }
    assistantBuffer += text;
  }
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
    const entry = entries.value.find((e) => e.id === activeThinkId);
    if (entry) {
      entry.content = (entry.content || "") + thinkBuffer;
    }
    thinkBuffer = "";
  }
  if (assistantBuffer) {
    const entry = entries.value.find((e) => e.id === activeAssistantId);
    if (entry) {
      entry.content = (entry.content || "") + assistantBuffer;
    }
    assistantBuffer = "";
  }
  bumpStream();
}

function endStreaming() {
  flushBuffers();
  if (activeThinkId !== null) {
    const entry = entries.value.find((e) => e.id === activeThinkId);
    if (entry) {
      entry.streaming = false;
      entry.collapsed = true; // 思考完成自动收起
    }
    activeThinkId = null;
  }
  if (activeAssistantId !== null) {
    const entry = entries.value.find((e) => e.id === activeAssistantId);
    if (entry) {
      entry.streaming = false;
    }
    activeAssistantId = null;
  }
  clearAllStreaming();
  bumpStream();
}

function clearAllStreaming() {
  // 双保险：扫描清掉任何残留的流式标记，确保思考/正文切换为 Markdown 渲染
  for (const entry of entries.value) {
    if (
      (entry.kind === "think" || entry.kind === "assistant") &&
      entry.streaming
    ) {
      entry.streaming = false;
      if (entry.kind === "think") entry.collapsed = true;
    }
  }
  activeThinkId = null;
  activeAssistantId = null;
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
    list_files: "读取目录",
    finish: "完成",
    file: "写入文件",
  };
  return map[tool || ""] || tool || "工具";
}

function toolIcon(tool?: string) {
  if (tool === "write_file" || tool === "edit_file") return "pencil";
  if (tool === "run_command") return "terminal";
  if (tool === "read_file" || tool === "list_files") return "folder";
  if (tool === "finish") return "flag";
  if (tool === "file") return "check";
  return "info";
}

onMounted(async () => {
  project.value = await getProject(projectId);
  const sessions = await listSessions(projectId);
  if (sessions.length) {
    const history = (await listMessages(sessions[0].id)) as Message[];
    entries.value = historyToEntries(history);
  }
  // 首页“生成项目”带提示词跳转：自动开始生成
  const autoRequirement = route.query.requirement;
  if (
    route.query.auto === "1" &&
    typeof autoRequirement === "string" &&
    autoRequirement.trim()
  ) {
    router.replace({ query: {} });
    requirement.value = autoRequirement;
    await submitRequirement();
  }
});

function historyToEntries(history: Message[]): ChatEntry[] {
  const list: ChatEntry[] = [];
  let currentTools: ChatEntry | null = null;
  for (const m of history) {
    if (m.role === "user") {
      currentTools = null;
      list.push({ id: ++seq, kind: "user", content: m.content, collapsed: false });
      continue;
    }
    if (m.msg_type === "summary") {
      currentTools = null;
      list.push({ id: ++seq, kind: "assistant", content: m.content, collapsed: false });
      continue;
    }
    if (m.msg_type === "stage") {
      currentTools = null;
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
      currentTools = null;
      list.push({ id: ++seq, kind: "think", content: m.content, collapsed: true });
      continue;
    }
    if (m.msg_type === "tool_call") {
      const tj = (m.tool_call_json || {}) as {
        tool?: string;
        ok?: boolean;
        detail?: string;
        error?: string;
      };
      if (currentTools?.kind !== "tools") {
        currentTools = {
          id: ++seq,
          kind: "tools",
          items: [],
          collapsed: false,
        };
        list.push(currentTools);
      }
      currentTools.items?.push({
        tool: tj.tool || "",
        detail: m.content || tj.detail || "",
        pending: false,
        ok: tj.ok !== false,
        error: tj.error || undefined,
      });
      continue;
    }
    if (m.msg_type === "file_written") {
      if (currentTools?.kind === "tools") {
        const items = currentTools.items || [];
        const prevItem = items[items.length - 1];
        if (prevItem && prevItem.tool !== "file" && prevItem.detail === m.content) {
          continue;
        }
        items.push({ tool: "file", detail: m.content, pending: false, ok: true });
      } else {
        list.push({ id: ++seq, kind: "file", detail: m.content, collapsed: false });
      }
      continue;
    }
    if (m.msg_type === "build_log") {
      currentTools = null;
      const last = list[list.length - 1];
      if (last?.kind === "build") last.lines?.push(m.content);
      else list.push({ id: ++seq, kind: "build", lines: [m.content], collapsed: true });
      continue;
    }
    if (m.msg_type === "error") {
      currentTools = null;
      list.push({ id: ++seq, kind: "error", content: m.content, collapsed: false });
      continue;
    }
    if (m.msg_type === "info") {
      currentTools = null;
      list.push({ id: ++seq, kind: "info", content: m.content, collapsed: false });
      continue;
    }
    currentTools = null;
    list.push({ id: ++seq, kind: "assistant", content: m.content, collapsed: false });
  }
  return list;
}

onBeforeUnmount(() => {
  if (flushTimer !== null) clearTimeout(flushTimer);
  eventSource?.close();
  resizeEnd?.();
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

  eventSource.addEventListener("stream_end", () => {
    endStreaming();
  });

  eventSource.addEventListener("tool_call_started", (e) => {
    endStreaming();
    const event = JSON.parse((e as MessageEvent).data) as SseEvent;
    const tool = String(event.tool || "");
    const args = (event.args || {}) as Record<string, unknown>;
    let detail = "";
    if (typeof args.path === "string") detail = args.path;
    else if (Array.isArray(args.command)) detail = args.command.join(" ");
    let group = lastEntry();
    if (group?.kind !== "tools") {
      group = push({ kind: "tools", items: [] });
    }
    group.items?.push({ tool, detail, pending: true });
    bumpStream();
  });

  eventSource.addEventListener("tool_call_completed", (e) => {
    const event = JSON.parse((e as MessageEvent).data) as SseEvent;
    const tool = String(event.tool || "");
    for (const entry of [...entries.value].reverse()) {
      if (entry.kind !== "tools") continue;
      const item = [...(entry.items || [])]
        .reverse()
        .find((i) => i.tool === tool && i.pending);
      if (item) {
        item.pending = false;
        item.ok = event.ok !== false;
        if (!item.detail && event.detail) item.detail = String(event.detail);
        item.error = event.error ? String(event.error) : undefined;
        break;
      }
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
    let group = lastEntry();
    if (group?.kind !== "tools") {
      group = push({ kind: "tools", items: [] });
    }
    group.items?.push({ tool, detail, pending: false, ok: true });
    bumpStream();
  });

  eventSource.addEventListener("file_written", (e) => {
    const event = JSON.parse((e as MessageEvent).data) as SseEvent;
    const path = String(event.path || "");
    const content = typeof event.content === "string" ? event.content : undefined;
    // 代码查看区只跟随当前正在写入的文件，避免连续生成多个文件时
    // 把整个聊天栏撑成一串巨型代码卡片。
    for (const entry of entries.value) {
      entry.codeOpen = false;
      entry.items?.forEach((item) => {
        item.codeOpen = false;
      });
    }
    const last = lastEntry();
    if (last?.kind === "tools") {
      const items = last.items || [];
      const prevItem = items[items.length - 1];
      // 写入工具的 tool_call 已带同一 path，避免重复展示
      if (prevItem && prevItem.tool !== "file" && prevItem.detail === path) {
        prevItem.content = content;
        prevItem.codeOpen = Boolean(content);
        bumpStream();
        return;
      }
      items.push({ tool: "file", detail: path, pending: false, ok: true, content, codeOpen: Boolean(content) });
    } else {
      push({ kind: "file", detail: path, content, codeOpen: Boolean(content) });
    }
    bumpStream();
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
    const streamedAssistant =
      activeAssistantId !== null
        ? entries.value.find((entry) => entry.id === activeAssistantId)
        : null;
    if (streamedAssistant) {
      streamedAssistant.content = summary;
      streamedAssistant.streaming = false;
      activeAssistantId = null;
    } else {
      push({ kind: "assistant", content: summary, collapsed: false });
    }
    clearAllStreaming();
    progressStage.value = "done";
    eventSource?.close();
    previewRefresh.value += 1;
    refreshStatus(event.generation_id as number);
  });

  eventSource.addEventListener("error", (e) => {
    endStreaming();
    const event = JSON.parse((e as MessageEvent).data) as SseEvent;
    push({ kind: "error", content: String(event.error || "任务失败了") });
    progressStage.value = "done";
    eventSource?.close();
    refreshStatus();
  });

  eventSource.addEventListener("cancelled", () => {
    endStreaming();
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

async function renameProject() {
  if (!project.value) return;
  try {
    const { value } = await ElMessageBox.prompt(
      "输入新的项目名称",
      "重命名项目",
      {
        inputValue: project.value.name,
        inputValidator: (v: string) =>
          v.trim() ? true : "项目名称不能为空",
      }
    );
    const updated = await updateProject(projectId, { name: value.trim() });
    project.value = updated;
    ElMessage.success("已重命名");
  } catch {
    // 用户取消不提示
  }
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
  grid-template-columns: 560px 10px minmax(360px, 1fr);
  gap: 0;
}
.chat-pane {
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  overflow: hidden;
  border-right: 1px solid var(--line);
}
.splitter {
  position: relative;
  cursor: col-resize;
  touch-action: none;
  background: var(--canvas-deep);
  border-right: 1px solid var(--line);
  border-left: 1px solid var(--line);
  transition: background 0.15s;
}
.splitter:hover,
.splitter:focus-visible {
  background: var(--primary-soft);
}
.splitter-grip {
  position: absolute;
  left: 3px;
  top: 50%;
  width: 3px;
  height: 46px;
  transform: translateY(-50%);
  border-radius: 99px;
  background: var(--line-strong);
}
.splitter:hover .splitter-grip,
.splitter:focus-visible .splitter-grip {
  background: var(--primary);
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
  background: #fcfbf8;
}
.chat-list {
  flex: 1;
  overflow-y: auto;
  padding: 18px 16px 24px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.chat-msg {
  display: flex;
}
.chat-msg .bubble {
  border-radius: 10px 10px 10px 3px;
  box-shadow: none;
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
  border-radius: 10px 10px 3px 10px;
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
  padding: 9px 11px;
  border-radius: 8px;
  background: var(--paper);
  border: 1px solid var(--line);
  font-size: 13px;
  line-height: 1.5;
  color: var(--ink);
}
.stage-entry {
  border: none;
  border-left: 2px solid var(--amber);
  border-radius: 0;
  background: transparent;
  padding: 8px 10px;
  color: var(--muted);
}
.stage-entry .entry-title {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.02em;
}
.stage-entry .entry-hint {
  font-size: 11px;
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
  background: var(--paper);
  border: 1px solid var(--line);
  border-left: 3px solid var(--amber);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  margin-top: 6px;
}
.think-entry,
.entry.collapsible.streaming {
  background: #fffbf2;
  border-color: rgba(242, 169, 59, 0.4);
  border-left: 3px solid var(--amber);
}
.think-body :deep(p),
.think-body p {
  font-size: 12px;
  line-height: 1.65;
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
.file-entry {
  align-items: flex-start;
  background: #f4f7ff;
  border-color: rgba(91, 103, 241, 0.24);
  border-left: 3px solid var(--primary);
}
.file-main {
  flex: 1;
  min-width: 0;
}
.file-head {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 22px;
}
.file-action {
  color: var(--primary-dark);
  font-size: 12px;
  font-weight: 600;
}
.file-toggle {
  margin-left: auto;
  border: 0;
  background: transparent;
  color: var(--primary-dark);
  font-size: 10px;
  cursor: pointer;
  white-space: nowrap;
}
.file-toggle:hover {
  text-decoration: underline;
}
.code-preview {
  max-height: 172px;
  overflow: auto;
  margin: 9px 0 0;
  padding: 12px;
  border-radius: 7px;
  background: #1f2430;
  color: #d8e0ef;
  font-family: var(--font-mono);
  font-size: 11px;
  line-height: 1.65;
  white-space: pre;
  tab-size: 2;
}
.tool-code {
  flex-basis: 100%;
  width: 100%;
  margin-left: 21px;
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
  position: relative;
  min-width: 0;
  min-height: 0;
  padding: 16px 16px 16px 10px;
}

.element-popover {
  position: absolute;
  z-index: 20;
  width: min(350px, calc(100% - 24px));
  filter: drop-shadow(0 16px 28px rgba(35, 48, 75, 0.2));
  animation: popover-in 0.16s ease-out;
}
.element-popover::before {
  content: "";
  position: absolute;
  top: 24px;
  left: -7px;
  width: 14px;
  height: 14px;
  background: #fff;
  border-left: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
  transform: rotate(45deg);
  z-index: -1;
}
.element-popover :deep(.modify-panel) {
  margin: 0;
  border-color: rgba(82, 100, 216, 0.24);
}
.version-fab {
  position: absolute;
  right: 22px;
  bottom: 20px;
  z-index: 25;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 9px 13px 9px 10px;
  border: 1px solid rgba(82, 100, 216, 0.25);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.94);
  color: var(--primary-dark);
  box-shadow: 0 10px 24px rgba(35, 48, 75, 0.16);
  backdrop-filter: blur(10px);
  cursor: pointer;
  font-size: 12px;
  transition: transform 0.16s, box-shadow 0.16s, background 0.16s;
}
.version-fab:hover,
.version-fab.active {
  transform: translateY(-2px);
  background: var(--primary);
  color: #fff;
  box-shadow: 0 14px 30px rgba(82, 100, 216, 0.28);
}
.version-fab-mark { font-size: 18px; line-height: 1; }
.floating-version-history {
  position: absolute;
  right: 18px;
  bottom: 68px;
  z-index: 24;
  width: min(430px, calc(100% - 36px));
  max-height: min(70vh, 620px);
  overflow: auto;
  margin: 0;
  box-shadow: 0 18px 44px rgba(35, 48, 75, 0.22);
  animation: popover-in 0.16s ease-out;
}
@keyframes popover-in {
  from { opacity: 0; transform: translateY(5px) scale(0.985); }
  to { opacity: 1; transform: translateY(0) scale(1); }
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
.tools-entry {
  align-items: flex-start;
  border-left: 3px solid var(--primary);
  background: #f8f8ff;
}
.tools-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.tools-done {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--green);
  font-size: 12px;
  font-weight: 600;
  padding: 2px 2px 0;
}
.tool-item {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  background: var(--paper);
  border: 1px solid var(--line);
}
.tool-item.pending {
  background: var(--amber-soft);
  border-color: rgba(242, 169, 59, 0.4);
}
.tool-item.fail {
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
  .splitter {
    display: none;
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
  .version-fab { right: 16px; bottom: 18px; }
  .floating-version-history { right: 12px; bottom: 66px; width: calc(100% - 24px); }
}

:global(body.is-resizing) {
  cursor: col-resize;
  user-select: none;
}

/* Build Room 视觉系统：明亮工作台 + 清晰事件层级 */
.workspace {
  --paper: #ffffff;
  --canvas: #f5f7fb;
  --canvas-deep: #edf1f7;
  --line: #e6eaf1;
  --line-strong: #d3dae6;
  --ink: #20283a;
  --muted: #718096;
  --faint: #a4afbf;
  --primary: #5264d8;
  --primary-dark: #3f50c2;
  --primary-soft: #eef0ff;
  --amber: #d89132;
  --amber-soft: #fff5e4;
  --green: #2f9e78;
  --green-soft: #e8f7f0;
  --red: #d95f6b;
  --red-soft: #fff0f1;
  --warm-dark: #252b38;
  --warm-dark-2: #323a4c;
  --shadow-sm: 0 4px 16px rgba(35, 48, 75, 0.07);
  --shadow-md: 0 14px 36px rgba(35, 48, 75, 0.12);
  background: var(--canvas);
}
.topbar {
  height: 76px;
  padding: 0 24px;
  background: rgba(255, 255, 255, 0.96);
  border-bottom-color: var(--line);
  box-shadow: 0 1px 0 rgba(36, 48, 73, 0.03);
}
.topbar .eyebrow {
  color: var(--primary);
  letter-spacing: 0.16em;
  font-size: 10px;
  margin-bottom: 4px;
}
.brand-mark {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  color: #ffffff;
  font-size: 17px;
  background: linear-gradient(135deg, #6878e8, #8f9cff);
  border-radius: 11px;
  box-shadow: 0 5px 14px rgba(82, 100, 216, 0.24);
}
.name {
  color: var(--ink);
  font-size: 22px;
  line-height: 1.15;
  letter-spacing: -0.035em;
}
.back,
.ghost {
  background: var(--paper);
  border-color: var(--line);
  color: var(--muted);
}
.back:hover,
.ghost:hover {
  color: var(--ink);
  border-color: rgba(139, 155, 255, 0.65);
  background: var(--primary-soft);
}
.state {
  background: rgba(255, 255, 255, 0.035);
  border-color: var(--line);
}
.split {
  padding: 18px 20px 20px;
}
.chat-pane {
  padding: 0 16px 0 0;
  border-right: 0;
}
.stage-card,
.chat-card,
.preview-panel {
  border-color: var(--line);
  box-shadow: var(--shadow-sm);
}
.stage-card {
  background: var(--paper);
  padding: 18px 20px 16px;
}
.stage-head .panel-title {
  color: var(--ink);
  font-size: 12px;
  letter-spacing: 0.1em;
  font-weight: 600;
}
.stage-meta {
  color: var(--faint);
}
.chat-card {
  background: var(--paper);
  border-radius: 18px;
}
.chat-list {
  padding: 20px 18px 26px;
}
.chat-msg .bubble {
  background: #f8f9fc;
  border-color: var(--line);
}
.chat-msg.user .bubble {
  background: var(--primary-soft);
  border-color: #dce1ff;
}
.who {
  color: var(--faint);
}
.chat-msg.user .who {
  color: var(--primary-dark);
}
.bubble p,
.entry-body,
.entry-title {
  color: var(--ink);
}
.bubble p {
  font-size: 14px;
  line-height: 1.72;
}
.entry-title {
  font-size: 13px;
  font-weight: 650;
}
.entry-detail,
.entry-hint,
.tool-name {
  font-size: 11px;
  line-height: 1.55;
}
.empty-tip {
  color: var(--muted);
}
.example {
  color: var(--primary-dark);
  background: var(--primary-soft);
}
.entry {
  background: #fbfcfe;
  border-color: var(--line);
}
.stage-entry {
  border-left-color: var(--green);
  color: var(--muted);
}
.stage-dot {
  background: var(--green);
  box-shadow: 0 0 0 3px var(--green-soft), 0 0 14px rgba(91, 224, 173, 0.45);
}
.think-entry,
.entry.collapsible.streaming {
  background: #fffaf1;
  border-color: rgba(255, 184, 102, 0.28);
}
.think-body,
.entry-body {
  background: #ffffff;
  border-color: var(--line);
  color: var(--ink);
}
.tools-entry {
  background: #f7f8ff;
  border-left-color: var(--primary);
}
.tool-item,
.file-entry {
  background: #ffffff;
  border-color: var(--line);
}
.tool-item.pending {
  background: var(--amber-soft);
  border-color: rgba(255, 184, 102, 0.35);
}
.file-entry {
  background: rgba(91, 224, 173, 0.07);
  border-left-color: var(--green);
}
.file-action,
.tool-name {
  color: var(--primary-dark);
}
.entry-detail,
.entry-hint {
  color: var(--muted);
}
.input-row {
  padding: 14px 16px 16px;
  background: #ffffff;
  border-top-color: var(--line);
}
.input-row :deep(.el-textarea__inner) {
  color: var(--ink);
  background: #f8f9fc;
  border-color: var(--line-strong);
  box-shadow: none;
}
.input-row :deep(.el-textarea__inner::placeholder) {
  color: var(--faint);
}
.input-row :deep(.el-textarea__inner:focus) {
  border-color: rgba(139, 155, 255, 0.8);
  box-shadow: 0 0 0 3px rgba(139, 155, 255, 0.12);
}
.input-side :deep(.el-button--primary) {
  border: 0;
  background: linear-gradient(135deg, #8797ff, #5d6ef1);
  box-shadow: 0 8px 24px rgba(93, 110, 241, 0.3);
}
.preview-pane {
  padding: 0 0 0 12px;
}
.preview-panel {
  background: #f7f8fc;
  border-radius: 18px;
}
.splitter {
  background: transparent;
  border-color: transparent;
}
.splitter-grip {
  width: 4px;
  background: rgba(139, 155, 255, 0.4);
  box-shadow: 0 0 16px rgba(139, 155, 255, 0.25);
}
.splitter:hover,
.splitter:focus-visible {
  background: rgba(139, 155, 255, 0.08);
}
.build-lines,
.code-preview {
  background: #070c16;
  border: 1px solid rgba(158, 177, 220, 0.15);
}

@media (max-width: 1024px) {
  .split {
    padding: 12px;
  }
  .chat-pane {
    padding-right: 0;
  }
  .preview-pane {
    padding: 12px 0 0;
  }
}
</style>
