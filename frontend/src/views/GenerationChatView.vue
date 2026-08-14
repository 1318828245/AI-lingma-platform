<template>
  <div class="page gen-page">
    <header class="page-header">
      <div>
        <el-button link @click="$router.push('/')">← 项目列表</el-button>
        <h1 class="page-title">{{ project?.name || "生成对话" }}</h1>
        <p class="muted">用自然语言描述需求，AI 自动生成前端工程</p>
      </div>
      <el-button type="primary" @click="goPreview">打开预览</el-button>
    </header>

    <el-card v-if="runningGen" class="progress-card" shadow="never">
      <WorkflowProgress :stage="progressStage" />
      <div class="gen-meta muted">
        状态：{{ runningGen.status }} · 构建尝试：{{
          runningGen.build_attempt
        }}
        <el-button
          v-if="runningGen.status === 'running'"
          size="small"
          type="danger"
          plain
          @click="cancel"
        >
          取消任务
        </el-button>
      </div>
      <el-alert
        v-if="runningGen.error"
        :title="runningGen.error"
        type="error"
        :closable="false"
        class="mt-8"
      />
    </el-card>

    <el-row :gutter="16">
      <el-col :xs="24" :md="14">
        <el-card shadow="never" class="chat-card">
          <div class="chat-list">
            <div
              v-for="(msg, idx) in messages"
              :key="idx"
              class="chat-msg"
              :class="msg.role"
            >
              <div class="bubble">{{ msg.content }}</div>
            </div>
            <div v-if="!messages.length" class="muted empty-tip">
              输入你的第一个需求，例如：“做一个深色风格的个人名片页”
            </div>
          </div>
          <div class="input-row">
            <el-input
              v-model="requirement"
              type="textarea"
              :rows="3"
              :disabled="!!runningGen"
              placeholder="描述你要生成的前端页面…"
            />
            <el-button
              type="primary"
              :loading="submitting"
              :disabled="!!runningGen"
              @click="submitRequirement"
            >
              生成
            </el-button>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :md="10">
        <el-card shadow="never" class="side-card">
          <template #header>实时日志</template>
          <div class="log-list">
            <p v-for="(line, idx) in logs" :key="idx" class="log-line">
              {{ line }}
            </p>
            <p v-if="!logs.length" class="muted">等待任务开始…</p>
          </div>
        </el-card>
        <el-card shadow="never" class="side-card mt-8">
          <template #header>生成文件（{{ files.length }}）</template>
          <el-scrollbar height="220px">
            <p v-for="f in files" :key="f.path" class="file-line">{{ f.path }}</p>
            <p v-if="!files.length" class="muted">暂无文件</p>
          </el-scrollbar>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import WorkflowProgress from "../components/WorkflowProgress.vue";
import {
  cancelGeneration,
  createGeneration,
  generationEventUrl,
  getGeneration,
} from "../api/generations";
import {
  getProject,
  listMessages,
  listProjectFiles,
  listSessions,
} from "../api/projects";
import type {
  Generation,
  Message,
  Project,
  ProjectFile,
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
const files = ref<ProjectFile[]>([]);
const submitting = ref(false);
let eventSource: EventSource | null = null;

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
    ElMessage.warning("请先输入需求");
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
    watchGeneration(gen.id);
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || "提交失败");
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
    logs.value.push(`阶段：${event.stage}`);
  });
  eventSource.addEventListener("thought", (e) => {
    const event = JSON.parse((e as MessageEvent).data) as SseEvent;
    logs.value.push(`思考：${event.content}`);
  });
  eventSource.addEventListener("build_log", (e) => {
    const event = JSON.parse((e as MessageEvent).data) as SseEvent;
    logs.value.push(String(event.line));
  });
  eventSource.addEventListener("file_written", (e) => {
    const event = JSON.parse((e as MessageEvent).data) as SseEvent;
    logs.value.push(`写入：${event.path}`);
    refreshFiles();
  });
  eventSource.addEventListener("completed", (e) => {
    const event = JSON.parse((e as MessageEvent).data) as SseEvent;
    messages.value.push({ role: "assistant", content: String(event.summary) });
    progressStage.value = "done";
    eventSource?.close();
    refreshStatus(event.generation_id as number);
    refreshFiles();
  });
  eventSource.addEventListener("error", (e) => {
    const event = JSON.parse((e as MessageEvent).data) as SseEvent;
    ElMessage.error(String(event.error || "任务失败"));
    progressStage.value = "done";
    eventSource?.close();
    refreshStatus();
  });
  eventSource.addEventListener("cancelled", () => {
    ElMessage.warning("任务已取消");
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

async function refreshFiles() {
  files.value = await listProjectFiles(projectId);
}

async function cancel() {
  if (!runningGen.value) return;
  await cancelGeneration(runningGen.value.id);
  ElMessage.info("已请求取消");
}

function goPreview() {
  router.push(`/projects/${projectId}/preview`);
}
</script>

<style scoped>
.progress-card {
  margin-bottom: 16px;
}
.gen-meta {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 12px;
}
.chat-card {
  height: 640px;
  display: flex;
  flex-direction: column;
}
.chat-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}
.chat-msg {
  margin-bottom: 12px;
  display: flex;
}
.chat-msg.user {
  justify-content: flex-end;
}
.bubble {
  max-width: 80%;
  padding: 10px 14px;
  border-radius: 12px;
  background: #f0f2f5;
  white-space: pre-wrap;
  line-height: 1.6;
}
.chat-msg.user .bubble {
  background: #409eff;
  color: #fff;
}
.empty-tip {
  text-align: center;
  margin-top: 40px;
}
.input-row {
  display: flex;
  gap: 12px;
  padding: 12px 0 0;
}
.side-card {
  margin-bottom: 16px;
}
.log-list {
  height: 260px;
  overflow-y: auto;
  background: #0f172a;
  border-radius: 8px;
  padding: 10px;
}
.log-line {
  color: #cbd5e1;
  font-size: 12px;
  font-family: Consolas, monospace;
  line-height: 1.7;
  word-break: break-all;
}
.file-line {
  font-family: Consolas, monospace;
  font-size: 13px;
  padding: 2px 0;
}
.mt-8 {
  margin-top: 8px;
}
</style>
