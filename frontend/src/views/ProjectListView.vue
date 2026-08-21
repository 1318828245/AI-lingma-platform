<template>
  <div class="studio-shell">
    <header class="top-nav">
      <button class="brand-lockup" type="button" title="项目列表" @click="scrollToProjects">
        <span class="brand-icon" aria-hidden="true"><i /><i /><i /></span>
        <span>AI 灵码平台</span>
      </button>
      <div class="nav-user">
        <span class="avatar" aria-hidden="true">{{ (auth.user?.username || 'U').slice(0, 1).toUpperCase() }}</span>
        <span class="user-name">{{ auth.user?.username || '未登录用户' }}</span>
        <button class="logout" type="button" @click="logout">退出登录</button>
      </div>
    </header>

    <main class="studio-main">
      <aside class="project-sidebar" aria-label="项目列表导航">
        <div class="side-heading"><span class="side-icon" aria-hidden="true">▦</span><div><p>工作区</p><strong>项目列表</strong></div><b>{{ projects.length }}</b></div>
        <div v-if="projects.length" class="side-projects">
          <button v-for="project in projects" :key="project.id" class="side-project" type="button" @click="openGeneration(project)">
            <span class="side-project-mark" :class="project.tech_stack.toLowerCase().startsWith('vue') ? 'vue' : 'html'" />
            <span><strong>{{ project.name }}</strong><small>{{ projectType(project) }} · {{ formatDate(project.updated_at) }}</small></span>
            <i aria-hidden="true">›</i>
          </button>
        </div>
        <div v-else class="side-empty">创建第一个项目后，它会显示在这里。</div>
      </aside>

      <section class="home-content">
        <header class="hero">
          <p class="hero-eyebrow"><span /> AI-ASSISTED CREATION STUDIO</p>
          <h1>AI 灵码平台</h1>
          <p>从一句想法开始，生成、预览、修改并发布你的网页项目。</p>
          <div class="hero-rail" aria-hidden="true"><i /><i /><i /><i /></div>
        </header>

        <section class="quick-create" aria-labelledby="quick-create-title">
          <div class="quick-head"><div><p class="section-kicker">NEW PROJECT</p><h2 id="quick-create-title">快速生成项目</h2><p>写下你想做的页面，选择技术栈后立即进入生成工作区。</p></div><span class="quick-spark" aria-hidden="true">✦</span></div>
          <div class="creation-form">
            <label class="prompt-field"><span>项目需求</span><textarea v-model="quickPrompt" rows="4" placeholder="例如：做一个有作品展示和联系表单的个人主页" @keydown.enter.exact.prevent="quickCreate" /></label>
            <div class="creation-controls"><div><span class="control-label">技术栈</span><div class="stack-toggle"><button v-for="stack in stacks" :key="stack.value" type="button" :class="{ active: quickStack === stack.value }" @click="quickStack = stack.value">{{ stack.label }}</button></div></div><button class="create-button" type="button" @click="quickCreate"><span>✦</span> 生成项目</button></div>
          </div>
          <div class="template-row"><span>快捷灵感</span><button v-for="template in quickTemplates" :key="template" type="button" @click="quickPrompt = template">{{ template }} <i>→</i></button></div>
        </section>

        <section id="project-overview" class="project-overview" aria-labelledby="projects-title">
          <div class="overview-head"><div><p class="section-kicker">RECENT WORK</p><h2 id="projects-title">项目概览</h2></div><p v-if="projects.length > 8">展示最近 8 个项目，其余项目可从左侧列表进入。</p><p v-else>点击项目卡片进入工作区。</p></div>
          <div v-if="visibleProjects.length" class="project-grid">
            <article v-for="(project, index) in visibleProjects" :key="project.id" class="project-card" :data-project-id="project.id" :ref="(element) => observeProjectCard(project.id, element as Element | null)" role="button" tabindex="0" :style="{ '--delay': `${index * 55}ms` }" @click="openGeneration(project)" @keydown.enter="openGeneration(project)">
              <div class="project-preview">
                <img v-if="thumbRequested[project.id]" :class="{ visible: thumbState[project.id] === 'ok' }" :src="thumbSrc(project)" :alt="`${project.name} 项目预览`" @load="thumbState[project.id] = 'ok'" @error="thumbState[project.id] = 'error'" />
                <div v-if="thumbState[project.id] !== 'ok'" class="preview-placeholder"><span>{{ thumbState[project.id] === 'loading' ? '正在生成预览…' : '项目预览' }}</span><i aria-hidden="true">▧</i></div>
              </div>
              <div class="project-card-top"><span class="type-chip" :class="project.tech_stack.toLowerCase().startsWith('vue') ? 'vue' : 'html'">{{ projectType(project) }}</span><button class="preview-project" type="button" @click.stop="openPreview(project)">预览 <i>↗</i></button></div>
              <h3>{{ project.name }}</h3><p>{{ project.description || '尚未填写项目描述，进入工作区开始创作。' }}</p>
              <footer><span>创建于 {{ formatDate(project.created_at) }}</span><span aria-hidden="true">↗</span></footer>
              <button class="delete-project" type="button" title="删除项目" @click.stop="remove(project)">删除</button>
            </article>
          </div>
          <div v-else class="empty-projects"><span>✦</span><h3>从一个想法开始</h3><p>在上方输入你的项目需求，AI 会为你创建可继续修改的网页项目。</p></div>
        </section>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { createProject, deleteProject, listProjects } from "../api/projects";
import { useAuthStore } from "../stores/auth";
import type { Project } from "../types";

const router = useRouter();
const auth = useAuthStore();
const projects = ref<Project[]>([]);
const quickPrompt = ref("");
const quickStack = ref<"html" | "vue3">("html");
const stacks = [{ value: "html", label: "HTML" }, { value: "vue3", label: "Vue 3" }] as const;
const quickTemplates = ["个人主页", "任务看板", "商品管理表格"];
const visibleProjects = computed(() => projects.value.slice(0, 8));
const thumbState = ref<Record<number, "loading" | "ok" | "error">>({});
const thumbRequested = ref<Record<number, boolean>>({});
const thumbVersions = ref<Record<number, number>>({});
let thumbnailObserver: IntersectionObserver | undefined;

onMounted(async () => {
  if ("IntersectionObserver" in window) {
    thumbnailObserver = new IntersectionObserver((entries) => entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      requestThumb(Number((entry.target as HTMLElement).dataset.projectId));
      thumbnailObserver?.unobserve(entry.target);
    }), { rootMargin: "240px 0px" });
  }
  projects.value = await listProjects();
});
onBeforeUnmount(() => thumbnailObserver?.disconnect());
function projectType(project: Project) { return project.tech_stack.toLowerCase().startsWith("vue") ? "Vue 项目" : "HTML 项目"; }
function formatDate(value: string) { return new Date(value).toLocaleDateString("zh-CN", { month: "short", day: "numeric" }); }
function thumbSrc(project: Project) { return `/api/projects/${project.id}/screenshot?token=${encodeURIComponent(auth.accessToken)}&project=${encodeURIComponent(project.slug)}&t=${thumbVersions.value[project.id] || 0}`; }
function requestThumb(projectId: number) { if (!Number.isFinite(projectId) || thumbRequested.value[projectId]) return; thumbRequested.value[projectId] = true; thumbState.value[projectId] = "loading"; }
function observeProjectCard(projectId: number, element: Element | null) { if (!element || thumbRequested.value[projectId]) return; if (thumbnailObserver) thumbnailObserver.observe(element); else requestThumb(projectId); }
function scrollToProjects() { document.getElementById("project-overview")?.scrollIntoView({ behavior: "smooth", block: "start" }); }
function openGeneration(project: Project) { router.push(`/projects/${project.id}`); }
function openPreview(project: Project) { router.push(`/projects/${project.id}/preview`); }

async function quickCreate() {
  const prompt = quickPrompt.value.trim();
  if (!prompt) { ElMessage.warning("先输入你想生成的项目需求"); return; }
  try {
    const project = await createProject({ name: prompt.split(/\n/)[0].trim().slice(0, 24) || "未命名项目", template: "blank", tech_stack: quickStack.value });
    ElMessage.success("项目创建成功，正在进入工作区");
    projects.value.unshift(project); quickPrompt.value = "";
    router.push({ path: `/projects/${project.id}`, query: { requirement: prompt, auto: "1" } });
  } catch (error: any) { ElMessage.error(error.response?.data?.detail || "创建失败"); }
}
async function remove(project: Project) {
  await ElMessageBox.confirm(`确定删除项目「${project.name}」？工作区、版本与部署记录会一并清理。`, "删除确认", { type: "warning", confirmButtonText: "删除项目", cancelButtonText: "取消" });
  await deleteProject(project.id); projects.value = projects.value.filter((item) => item.id !== project.id); ElMessage.success("项目已删除");
}
function logout() { auth.logout(); router.push("/login"); }
</script>

<style scoped>
.studio-shell { min-height:100vh; background:#f4f6fb; color:#1e2948; } .top-nav { position:sticky; z-index:5; top:0; display:flex; align-items:center; justify-content:space-between; height:68px; padding:0 clamp(20px,4vw,58px); border-bottom:1px solid rgba(207,216,240,.75); background:rgba(250,251,255,.9); box-shadow:0 8px 24px rgba(45,58,105,.05); backdrop-filter:blur(16px); } .brand-lockup { display:inline-flex; align-items:center; gap:11px; border:0; background:transparent; color:#24325e; font:700 18px/1 var(--font-display); cursor:pointer; } .brand-icon { display:grid; grid-template-columns:repeat(2,7px); gap:3px; padding:8px; border-radius:10px; background:linear-gradient(135deg,#33478e,#7285f3); box-shadow:0 5px 12px rgba(58,75,166,.25); } .brand-icon i { width:7px; height:7px; border-radius:2px; background:#fff; } .brand-icon i:last-child { grid-column:span 2; width:17px; opacity:.68; } .nav-user { display:flex; align-items:center; gap:9px; } .avatar { display:grid; place-items:center; width:30px; height:30px; border-radius:50%; background:#e1e7ff; color:#4255b7; font-size:13px; font-weight:800; } .user-name { font-size:14px; font-weight:650; } .logout { min-height:34px; margin-left:7px; border:1px solid #ccd5f5; border-radius:8px; padding:6px 10px; background:#fff; color:#4658ae; font-size:13px; font-weight:700; cursor:pointer; transition:.16s ease; } .logout:hover { border-color:#7183df; background:#f3f5ff; }
.studio-main { display:grid; grid-template-columns:270px minmax(0,1fr); width:100%; min-height:calc(100vh - 68px); } .project-sidebar { position:sticky; top:68px; align-self:start; height:calc(100vh - 68px); box-sizing:border-box; overflow:auto; padding:26px 15px; border-right:1px solid #e0e5f3; background:#f9faff; } .side-heading { display:grid; grid-template-columns:34px 1fr auto; align-items:center; gap:9px; padding:0 8px 18px; } .side-icon { display:grid; place-items:center; width:32px; height:32px; border-radius:9px; background:#e9edff; color:#4b5fc5; font-size:17px; } .side-heading p { margin:0 0 2px; color:#7783a5; font-size:11px; font-weight:700; letter-spacing:.08em; } .side-heading strong { font-size:16px; } .side-heading b { min-width:23px; padding:3px 5px; border-radius:999px; background:#e8edff; color:#4355b5; text-align:center; font-size:12px; } .side-projects { display:grid; gap:4px; } .side-project { display:grid; grid-template-columns:7px minmax(0,1fr) 14px; align-items:center; gap:9px; width:100%; border:1px solid transparent; border-radius:9px; padding:10px 8px; background:transparent; color:#334060; text-align:left; cursor:pointer; transition:.16s ease; } .side-project:hover,.side-project:focus-visible { border-color:#d4dcfb; background:#f0f3ff; outline:none; } .side-project-mark { width:7px; height:24px; border-radius:999px; background:#8d9bbb; } .side-project-mark.vue { background:#42a886; } .side-project-mark.html { background:#e69b3c; } .side-project strong,.side-project small { display:block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; } .side-project strong { font-size:13px; } .side-project small { margin-top:3px; color:#7b87a5; font-size:11px; } .side-project i { color:#8792b4; font-size:18px; font-style:normal; } .side-empty { padding:14px 9px; color:#7783a0; font-size:13px; line-height:1.55; }
.home-content { box-sizing:border-box; width:min(100%,1500px); min-width:0; margin:0 auto; padding:clamp(30px,4vw,64px) clamp(28px,4.5vw,78px) 58px; } .hero { position:relative; overflow:hidden; padding:12px 0 39px; } .hero::after { content:""; position:absolute; z-index:0; right:3%; top:-90px; width:250px; height:250px; border:1px solid #d9e0fb; border-radius:50%; box-shadow:0 0 0 27px rgba(219,226,255,.38),0 0 0 56px rgba(219,226,255,.19); } .hero > * { position:relative; z-index:1; } .hero-eyebrow,.section-kicker { margin:0; color:#5368ca; font:750 11px/1.25 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:.12em; } .hero-eyebrow span { display:inline-block; width:8px; height:8px; margin-right:7px; border-radius:50%; background:#6b7ce0; box-shadow:0 0 0 4px #e3e8ff; } .hero h1 { max-width:750px; margin:13px 0 10px; color:#21305c; font:700 clamp(40px,5.4vw,70px)/1 var(--font-display); letter-spacing:-.055em; } .hero > p:not(.hero-eyebrow) { max-width:570px; margin:0; color:#65728f; font-size:18px; line-height:1.65; } .hero-rail { display:flex; gap:6px; margin-top:25px; } .hero-rail i { width:34px; height:4px; border-radius:999px; background:#d5ddfb; } .hero-rail i:first-child { background:#5c70d8; } .hero-rail i:nth-child(2) { opacity:.78; } .hero-rail i:nth-child(3) { opacity:.55; } .hero-rail i:nth-child(4) { opacity:.3; }
.quick-create { padding:28px; border:1px solid #dce3f6; border-radius:18px; background:#fff; box-shadow:0 18px 38px rgba(45,59,112,.08); } .quick-head { display:flex; align-items:flex-start; justify-content:space-between; gap:16px; padding-bottom:22px; border-bottom:1px solid #e8ebf5; } .quick-head h2,.overview-head h2 { margin:6px 0 5px; color:#26355f; font:700 25px/1.2 var(--font-display); letter-spacing:-.035em; } .quick-head p:not(.section-kicker) { margin:0; color:#687591; font-size:14px; } .quick-spark { display:grid; place-items:center; width:42px; height:42px; border-radius:12px; background:#eff2ff; color:#566bd1; font-size:20px; transform:rotate(11deg); } .creation-form { display:grid; grid-template-columns:minmax(0,1fr) auto; gap:19px; padding-top:22px; } .prompt-field { display:block; } .prompt-field > span,.control-label { display:block; margin-bottom:8px; color:#52617f; font-size:13px; font-weight:750; } .prompt-field textarea { box-sizing:border-box; width:100%; min-height:112px; resize:vertical; border:1px solid #cbd5f1; border-radius:11px; padding:14px 15px; background:#fbfcff; color:#263452; font:15px/1.6 var(--font-body); outline:none; transition:.16s ease; } .prompt-field textarea:focus { border-color:#6175db; box-shadow:0 0 0 4px rgba(93,112,215,.13); background:#fff; } .creation-controls { display:flex; flex-direction:column; justify-content:space-between; min-width:172px; } .stack-toggle { display:flex; overflow:hidden; border:1px solid #cbd5f1; border-radius:9px; background:#f6f8ff; } .stack-toggle button { flex:1; min-height:38px; border:0; border-right:1px solid #d8def2; background:transparent; color:#657390; font-size:13px; font-weight:700; cursor:pointer; } .stack-toggle button:last-child { border-right:0; } .stack-toggle button.active { background:#fff; color:#4156bb; box-shadow:0 1px 5px rgba(46,60,130,.12); } .create-button { display:inline-flex; align-items:center; justify-content:center; gap:8px; min-height:46px; border:0; border-radius:10px; padding:10px 16px; background:linear-gradient(135deg,#3f52b4,#7588ef); color:#fff; font-size:14px; font-weight:750; cursor:pointer; box-shadow:0 8px 16px rgba(73,91,190,.22); transition:.16s ease; } .create-button:hover { transform:translateY(-2px); box-shadow:0 12px 22px rgba(73,91,190,.28); } .template-row { display:flex; flex-wrap:wrap; align-items:center; gap:8px; margin-top:19px; } .template-row > span { margin-right:3px; color:#73809c; font-size:12px; font-weight:700; } .template-row button { border:1px solid #d6ddf4; border-radius:999px; padding:7px 10px; background:#fff; color:#526181; font-size:12px; cursor:pointer; transition:.15s ease; } .template-row button i { margin-left:4px; color:#6376d5; font-style:normal; } .template-row button:hover { border-color:#91a0e9; background:#f2f4ff; color:#364cb5; }
.project-overview { margin-top:41px; } .overview-head { display:flex; align-items:flex-end; justify-content:space-between; gap:18px; margin-bottom:18px; } .overview-head > p { max-width:330px; margin:0; color:#71809b; font-size:13px; line-height:1.5; text-align:right; } .project-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:18px; } .project-card { position:relative; min-width:0; overflow:hidden; border:1px solid #dce3f5; border-radius:14px; padding:0 18px 18px; background:#fff; cursor:pointer; animation:card-in .4s both; animation-delay:var(--delay); transition:transform .17s ease,box-shadow .17s ease,border-color .17s ease; } .project-card::after { content:""; position:absolute; right:-30px; bottom:-34px; width:105px; height:105px; border:1px solid #e1e6fa; border-radius:50%; transition:.2s ease; } .project-card:hover,.project-card:focus-visible { z-index:1; border-color:#98a7ec; box-shadow:0 12px 24px rgba(45,61,124,.13); outline:none; transform:translateY(-4px); } .project-card:hover::after { transform:scale(1.15); border-color:#c3ccf7; } .project-preview { position:relative; height:154px; margin:0 -18px 16px; overflow:hidden; border-bottom:1px solid #e5e9f5; background:linear-gradient(135deg,#e8edff,#f8f9ff); } .project-preview img { width:100%; height:100%; object-fit:cover; object-position:top; opacity:0; transition:opacity .25s ease; } .project-preview img.visible { opacity:1; } .preview-placeholder { position:absolute; inset:0; display:flex; align-items:center; justify-content:space-between; padding:14px; color:#7181bd; font-size:12px; font-weight:700; } .preview-placeholder i { color:#8d9ce4; font-size:25px; font-style:normal; } .project-card-top { display:flex; justify-content:space-between; gap:7px; } .type-chip { display:inline-flex; align-items:center; min-height:24px; border-radius:999px; padding:3px 7px; font-size:11px; font-weight:750; } .type-chip { background:#fff1dc; color:#a56c17; } .type-chip.vue { background:#e4f7ef; color:#207a59; } .preview-project { display:inline-flex; align-items:center; gap:4px; min-height:26px; border:1px solid #c8d2fa; border-radius:7px; padding:3px 8px; background:#f4f6ff; color:#4057bd; font-size:12px; font-weight:750; cursor:pointer; transition:.15s ease; } .preview-project i { font-size:14px; font-style:normal; } .preview-project:hover { border-color:#7c8be0; background:#eaf0ff; transform:translateY(-1px); } .project-card h3 { overflow:hidden; margin:16px 0 9px; color:#29365f; font:700 17px/1.3 var(--font-display); text-overflow:ellipsis; white-space:nowrap; } .project-card > p { display:-webkit-box; min-height:60px; margin:0; overflow:hidden; color:#697691; font-size:13px; line-height:1.52; -webkit-box-orient:vertical; -webkit-line-clamp:3; } .project-card footer { display:flex; align-items:center; justify-content:space-between; margin-top:17px; padding-top:12px; border-top:1px solid #edf0f7; color:#77839e; font-size:11px; } .project-card footer span:last-child { color:#5c70d2; font-size:17px; font-weight:800; } .delete-project { position:absolute; z-index:2; top:11px; right:11px; opacity:0; border:1px solid #efc1c9; border-radius:7px; padding:5px 7px; background:#fff7f8; color:#b44357; font-size:11px; cursor:pointer; transform:translateY(-3px); transition:.15s ease; } .project-card:hover .delete-project,.delete-project:focus-visible { opacity:1; transform:none; outline:2px solid rgba(199,67,88,.22); outline-offset:2px; } .empty-projects { display:grid; place-items:center; min-height:260px; border:1px dashed #bdc8ec; border-radius:16px; background:#fbfcff; text-align:center; } .empty-projects span { color:#6a7ddb; font-size:29px; } .empty-projects h3 { margin:8px 0 5px; font-size:20px; } .empty-projects p { max-width:350px; margin:0; color:#72809c; font-size:14px; line-height:1.55; } @keyframes card-in { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:none; } }
@media (max-width:1160px) { .studio-main { grid-template-columns:220px minmax(0,1fr); } .home-content { padding-inline:32px; } .project-grid { grid-template-columns:repeat(3,minmax(0,1fr)); } } @media (max-width:850px) { .studio-main { display:block; } .project-sidebar { position:relative; top:0; height:auto; max-height:230px; border-right:0; border-bottom:1px solid #e0e5f3; } .side-projects { grid-template-columns:repeat(2,minmax(0,1fr)); } .creation-form { grid-template-columns:1fr; } .creation-controls { flex-direction:row; align-items:flex-end; gap:15px; } .project-grid { grid-template-columns:repeat(2,minmax(0,1fr)); } } @media (max-width:560px) { .top-nav { height:62px; padding:0 16px; } .brand-lockup { font-size:16px; } .user-name { display:none; } .studio-main { min-height:calc(100vh - 62px); } .home-content { padding:28px 16px 42px; } .hero h1 { font-size:42px; } .hero > p:not(.hero-eyebrow) { font-size:16px; } .quick-create { padding:20px; } .creation-controls { align-items:stretch; flex-direction:column; } .side-projects { grid-template-columns:1fr; } .overview-head { align-items:flex-start; flex-direction:column; } .overview-head > p { text-align:left; } .project-grid { grid-template-columns:1fr; } }
</style>
