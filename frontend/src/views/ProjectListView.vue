<template>
  <div class="page">
    <header class="page-header">
      <div>
        <h1 class="page-title">AI 灵码平台</h1>
        <p class="muted">你好，{{ auth.user?.username }}</p>
      </div>
      <div>
        <el-button type="primary" @click="openCreate">新建项目</el-button>
        <el-button @click="logout">退出登录</el-button>
      </div>
    </header>

    <el-row v-if="projects.length" :gutter="16">
      <el-col v-for="p in projects" :key="p.id" :xs="24" :sm="12" :md="8">
        <el-card class="project-card" shadow="hover">
          <div class="card-head">
            <h3>{{ p.name }}</h3>
            <el-tag size="small">{{ p.tech_stack }}</el-tag>
          </div>
          <p class="muted card-desc">{{ p.description || "暂无描述" }}</p>
          <p class="muted">模板：{{ p.template }} · {{ p.status }}</p>
          <div class="card-actions">
            <el-button size="small" type="primary" @click="openGeneration(p)">
              生成对话
            </el-button>
            <el-button size="small" @click="openPreview(p)">预览</el-button>
            <el-button size="small" type="danger" plain @click="remove(p)">
              删除
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
    <el-empty v-else description="还没有项目，点击右上角新建" />

    <el-dialog v-model="dialogVisible" title="新建项目" width="480px">
      <el-form label-position="top">
        <el-form-item label="项目名称" required>
          <el-input v-model="form.name" placeholder="例如：我的个人名片" />
        </el-form-item>
        <el-form-item label="起始模板">
          <el-select v-model="form.template" style="width: 100%">
            <el-option label="空白项目" value="blank" />
            <el-option
              v-for="t in templates"
              :key="t.id"
              :label="`${t.name}（${t.tech_stack}）`"
              :value="t.name"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="技术栈">
          <el-select v-model="form.tech_stack" style="width: 100%">
            <el-option label="纯 HTML/CSS/JS" value="html" />
            <el-option label="Vue 3 + Vite" value="vue3" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="2"
            placeholder="可选"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="create">
          创建
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  createProject,
  deleteProject,
  listProjects,
  listTemplates,
} from "../api/projects";
import { useAuthStore } from "../stores/auth";
import type { Project, Template } from "../types";

const router = useRouter();
const auth = useAuthStore();
const projects = ref<Project[]>([]);
const templates = ref<Template[]>([]);
const dialogVisible = ref(false);
const creating = ref(false);
const form = reactive({
  name: "",
  description: "",
  template: "blank",
  tech_stack: "html",
});

onMounted(async () => {
  projects.value = await listProjects();
  templates.value = await listTemplates();
});

function openCreate() {
  form.name = "";
  form.description = "";
  form.template = "blank";
  form.tech_stack = "html";
  dialogVisible.value = true;
}

async function create() {
  if (!form.name.trim()) {
    ElMessage.warning("请输入项目名称");
    return;
  }
  creating.value = true;
  try {
    const project = await createProject({
      name: form.name.trim(),
      description: form.description,
      template: form.template,
      tech_stack: form.tech_stack,
    });
    ElMessage.success("项目创建成功");
    dialogVisible.value = false;
    projects.value.unshift(project);
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || "创建失败");
  } finally {
    creating.value = false;
  }
}

function openGeneration(project: Project) {
  router.push(`/projects/${project.id}`);
}

function openPreview(project: Project) {
  router.push(`/projects/${project.id}/preview`);
}

async function remove(project: Project) {
  await ElMessageBox.confirm(
    `确定删除项目「${project.name}」？工作区、版本与部署记录会一并清理。`,
    "删除确认",
    { type: "warning" }
  );
  await deleteProject(project.id);
  projects.value = projects.value.filter((p) => p.id !== project.id);
  ElMessage.success("已删除");
}

function logout() {
  auth.logout();
  router.push("/login");
}
</script>

<style scoped>
.project-card {
  margin-bottom: 16px;
}
.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.card-desc {
  margin: 6px 0;
  min-height: 20px;
}
.card-actions {
  margin-top: 12px;
}
</style>
