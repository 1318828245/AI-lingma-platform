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
          <div class="chat-list">
            <div
              v-for="(msg, idx) in messages"
              :key="idx"
              class="chat-msg"
              :class="msg.role"
            >
              <div class="bubble">
                <span class="who mono">{{ msg.role === "user" ? "你" : "灵码" }}</span>
                <p>{{ msg.content }}</p>
              </div>
            </div>
            <div v-if="!messages.length" class="empty-tip">
              <p class="empty-mark" aria-hidden="true">✦</p>
              <p class="empty-title">从这里开始</p>
              <p>描述你想做的页面，比如：</p>
              <p class="mono example">“做一个深色风格的个人名片页，展示技能与作品”</p>
            </div>
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

        <section class="panel log-card">
          <div class="log-head">
            <span class="panel-title">实时日志</span>
            <span class="mono log-count">{{ logs.length }} 条</span>
          </div>
          <div class="log-body">
            <p v-for="(line, idx) in logs" :key="idx" class="log-line">
              {{ line }}
            </p>
            <p v-if="!logs.length" class="log-empty">还没开始，提交需求后这里会滚动起来</p>
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
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import LivePreviewPanel from "../components/LivePreviewPanel.vue";
import StageRail from "../components/StageRail.vue";
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
} from "../api/projects";
import type {
  Generation,
  Message,
  Project,
  SseEvent,
} from "../types";

const route = useRoute();
const router = useRouter();
const projectId = Number(route.params.id);

const project = ref<Project | null>(null);
const requirement = ref("");
const messages = ref<Array<{ role: string; content: string }>>([]);
const runningGen = ref<Generation | null>(null);
const progressStage = ref("parse");
const logs = ref<string[]>([]);
const submitting = ref(false);
const previewRefresh = ref(0);
let eventSource: EventSource | null = null;

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

onMounted(async () => {
  project.value = await getProject(projectId);
  const sessions = await listSessions(projectId);
  if (sessions.length) {
    const history = (await listMessages(sessions[0].id)) as Message[];
    messages.value = history.map((m) => ({ role: m.role, content: m.content }));
  }
});

onBeforeUnmount(() => {
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
    messages.value.push({ role: "user", content: text });
    const gen = await createGeneration(projectId, text);
    requirement.value = "";
    runningGen.value = gen;
    progressStage.value = "parse";
    logs.value = [];
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
    progressStage.value = event.stage as string;
    logs.value.push(`[stage] ${event.stage}`);
  });
  eventSource.addEventListener("thought", (e) => {
    const event = JSON.parse((e as MessageEvent).data) as SseEvent;
    logs.value.push(`[think] ${event.content}`);
  });
  eventSource.addEventListener("build_log", (e) => {
    const event = JSON.parse((e as MessageEvent).data) as SseEvent;
    logs.value.push(String(event.line));
  });
  eventSource.addEventListener("file_written", (e) => {
    const event = JSON.parse((e as MessageEvent).data) as SseEvent;
    logs.value.push(`[write] ${event.path}`);
  });
  eventSource.addEventListener("completed", (e) => {
    const event = JSON.parse((e as MessageEvent).data) as SseEvent;
    messages.value.push({ role: "assistant", content: String(event.summary) });
    progressStage.value = "done";
    eventSource?.close();
    previewRefresh.value += 1;
    refreshStatus(event.generation_id as number);
  });
  eventSource.addEventListener("error", (e) => {
    const event = JSON.parse((e as MessageEvent).data) as SseEvent;
    ElMessage.error(String(event.error || "任务失败了"));
    progressStage.value = "done";
    eventSource?.close();
    refreshStatus();
  });
  eventSource.addEventListener("cancelled", () => {
    ElMessage.warning("已取消这次生成");
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
.stage-head,
.log-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.stage-meta,
.log-count {
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
}
.chat-msg {
  display: flex;
  margin-bottom: 14px;
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
  margin-top: 44px;
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
.log-card {
  flex-shrink: 0;
}
.log-body {
  height: 150px;
  overflow-y: auto;
  background: var(--warm-dark);
  border-radius: var(--radius-md);
  padding: 10px 12px;
}
.log-line {
  font-family: var(--font-mono);
  font-size: 12px;
  color: #e8e2d8;
  line-height: 1.7;
  word-break: break-all;
}
.log-empty {
  font-size: 12px;
  color: #8b8376;
}
.preview-pane {
  min-width: 0;
  min-height: 0;
  padding: 16px 16px 16px 0;
}
</style>
