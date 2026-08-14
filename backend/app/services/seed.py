"""内置管理员与种子模板初始化。"""

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.template import Template
from app.models.user import User


def ensure_admin(db: Session) -> User:
    settings = get_settings()
    user = db.query(User).filter(User.username == settings.admin_username).first()
    if user is not None:
        return user
    user = User(
        username=settings.admin_username,
        password_hash=hash_password(settings.admin_password),
        email=settings.admin_email,
        role="admin",
        status="active",
        quota=999999,
        used_count=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


TEMPLATES: list[dict] = [
    {
        "key": "business-card",
        "name": "个人名片页",
        "description": "响应式个人名片页：头像、姓名/职位、简介、技能标签、作品列表、联系方式，深色现代风格。",
        "tech_stack": "html",
        "files": {
            "index.html": """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>个人名片</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <main class="card">
    <img class="avatar" src="https://api.dicebear.com/9.x/notionists/svg?seed=Alex" alt="头像">
    <h1 id="name">林晓</h1>
    <p class="role">前端工程师 / 产品设计师</p>
    <p class="intro">热爱把复杂问题变成简单优雅的界面，专注 Web 交互与用户体验。</p>
    <section>
      <h2>技能</h2>
      <ul class="tags" id="skills">
        <li>Vue 3</li>
        <li>TypeScript</li>
        <li>Node.js</li>
        <li>UI 设计</li>
      </ul>
    </section>
    <section>
      <h2>作品</h2>
      <ul class="works" id="works"></ul>
    </section>
    <footer>
      <h2>联系方式</h2>
      <p id="contact">邮箱：hello@example.com · 微信：linxiao-dev</p>
    </footer>
  </main>
  <script src="script.js"></script>
</body>
</html>
""",
            "style.css": """* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
  background: #0f172a;
  color: #e2e8f0;
  min-height: 100vh;
  display: flex;
  justify-content: center;
  padding: 40px 16px;
}
.card {
  max-width: 560px;
  width: 100%;
  background: #1e293b;
  border-radius: 20px;
  padding: 32px;
  box-shadow: 0 20px 50px rgba(0,0,0,.35);
}
.avatar { width: 96px; height: 96px; border-radius: 50%; margin-bottom: 16px; }
h1 { font-size: 28px; margin-bottom: 4px; }
.role { color: #38bdf8; margin-bottom: 12px; }
.intro { color: #94a3b8; line-height: 1.7; margin-bottom: 20px; }
h2 { font-size: 15px; color: #94a3b8; margin: 20px 0 10px; }
.tags { list-style: none; display: flex; flex-wrap: wrap; gap: 8px; }
.tags li {
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 999px;
  padding: 6px 14px;
  font-size: 14px;
}
.works { list-style: none; display: grid; gap: 10px; }
.works li { background: #0f172a; border-radius: 10px; padding: 12px 16px; }
footer p { color: #94a3b8; font-size: 14px; }
@media (max-width: 480px) {
  .card { padding: 20px; }
}
""",
            "script.js": """const works = [
  { name: "灵码看板", desc: "AI 辅助任务管理工具" },
  { name: "时光笔记", desc: "极简 Markdown 笔记应用" },
  { name: "像素画廊", desc: "前端创意视觉实验集" },
];
const list = document.getElementById("works");
works.forEach((item) => {
  const li = document.createElement("li");
  const strong = document.createElement("strong");
  strong.textContent = item.name;
  const span = document.createElement("span");
  span.textContent = " — " + item.desc;
  li.append(strong, span);
  list.appendChild(li);
});
""",
        },
    },
    {
        "key": "kanban",
        "name": "任务看板",
        "description": "三列任务看板：待办/进行中/已完成，支持新建、移动、删除，localStorage 持久化，浅色简洁风格。",
        "tech_stack": "vue3",
        "files": {
            "package.json": """{
  "name": "kanban-board",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.4.21"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.4",
    "vite": "^5.2.8"
  }
}
""",
            "vite.config.js": """import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  server: { port: 5173 },
});
""",
            "index.html": """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>任务看板</title>
</head>
<body>
  <div id="app"></div>
  <script type="module" src="/src/main.js"></script>
</body>
</html>
""",
            "src/main.js": """import { createApp } from "vue";
import App from "./App.vue";
import "./style.css";

createApp(App).mount("#app");
""",
            "src/style.css": """* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: "Segoe UI", "Microsoft YaHei", sans-serif; background: #f1f5f9; color: #334155; }
""",
            "src/App.vue": """<template>
  <div class="board">
    <header>
      <h1>任务看板</h1>
      <form class="add-form" @submit.prevent="addTask">
        <input v-model="newTitle" placeholder="输入新任务，回车添加" />
        <button type="submit">添加</button>
      </form>
    </header>
    <div class="columns">
      <section v-for="col in columns" :key="col.key" class="column">
        <h2>{{ col.title }}</h2>
        <ul>
          <li v-for="task in tasksByStatus(col.key)" :key="task.id" class="task">
            <span>{{ task.title }}</span>
            <div class="actions">
              <button v-if="col.key !== 'todo'" @click="move(task, -1)">←</button>
              <button v-if="col.key !== 'done'" @click="move(task, 1)">→</button>
              <button class="danger" @click="removeTask(task.id)">删除</button>
            </div>
          </li>
          <li v-if="tasksByStatus(col.key).length === 0" class="empty">暂无任务</li>
        </ul>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";

const columns = [
  { key: "todo", title: "待办" },
  { key: "doing", title: "进行中" },
  { key: "done", title: "已完成" },
];
const statusOrder = ["todo", "doing", "done"];
const newTitle = ref("");
const tasks = ref([]);

const tasksByStatus = (status) => computed(() =>
  tasks.value.filter((t) => t.status === status)
);

function addTask() {
  const title = newTitle.value.trim();
  if (!title) return;
  tasks.value.push({ id: Date.now(), title, status: "todo" });
  newTitle.value = "";
}

function move(task, offset) {
  const index = statusOrder.indexOf(task.status);
  const next = statusOrder[index + offset];
  if (next) task.status = next;
}

function removeTask(id) {
  tasks.value = tasks.value.filter((t) => t.id !== id);
}

watch(tasks, (value) => localStorage.setItem("kanban-tasks", JSON.stringify(value)), { deep: true });
onMounted(() => {
  try {
    tasks.value = JSON.parse(localStorage.getItem("kanban-tasks") || "[]");
  } catch {
    tasks.value = [];
  }
});
</script>

<style scoped>
.board { max-width: 1000px; margin: 0 auto; padding: 24px 16px; }
header { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; margin-bottom: 20px; }
h1 { font-size: 24px; }
.add-form { display: flex; gap: 8px; }
input { padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 8px; min-width: 240px; }
button { padding: 8px 14px; border: none; border-radius: 8px; background: #2563eb; color: #fff; cursor: pointer; }
button:hover { opacity: 0.9; }
button.danger { background: #dc2626; }
.columns { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.column { background: #fff; border-radius: 12px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }
.column h2 { font-size: 16px; margin-bottom: 12px; }
.task { display: flex; justify-content: space-between; align-items: center; gap: 8px; padding: 10px; background: #f8fafc; border-radius: 8px; margin-bottom: 8px; }
.actions { display: flex; gap: 6px; }
.actions button { padding: 4px 10px; font-size: 13px; }
.empty { color: #94a3b8; font-size: 14px; list-style: none; }
@media (max-width: 720px) {
  .columns { grid-template-columns: 1fr; }
}
</style>
""",
        },
    },
    {
        "key": "admin-dashboard",
        "name": "管理后台模板",
        "description": "管理后台布局：侧边导航 + 顶部栏 + 表格/筛选/分页/弹窗示例，适合快速改造成管理页面。",
        "tech_stack": "vue3",
        "files": {
            "package.json": """{
  "name": "admin-dashboard",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.4.21"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.4",
    "vite": "^5.2.8"
  }
}
""",
            "vite.config.js": """import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  server: { port: 5173 },
});
""",
            "index.html": """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>管理后台</title>
</head>
<body>
  <div id="app"></div>
  <script type="module" src="/src/main.js"></script>
</body>
</html>
""",
            "src/main.js": """import { createApp } from "vue";
import App from "./App.vue";
import "./style.css";

createApp(App).mount("#app");
""",
            "src/style.css": """* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: "Segoe UI", "Microsoft YaHei", sans-serif; background: #f1f5f9; color: #334155; }
""",
            "src/App.vue": """<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="logo">灵码管理台</div>
      <nav>
        <a v-for="item in menus" :key="item" :class="{ active: item === current }" @click="current = item">{{ item }}</a>
      </nav>
    </aside>
    <main class="main">
      <header class="topbar">
        <span>{{ current }}</span>
        <span class="user">管理员</span>
      </header>
      <section class="content">
        <div class="toolbar">
          <input v-model="keyword" placeholder="搜索名称" />
          <select v-model="statusFilter">
            <option value="">全部状态</option>
            <option value="在售">在售</option>
            <option value="下架">下架</option>
          </select>
          <button @click="openDialog()">新增商品</button>
        </div>
        <table>
          <thead>
            <tr><th>名称</th><th>价格</th><th>状态</th><th>操作</th></tr>
          </thead>
          <tbody>
            <tr v-for="row in pagedRows" :key="row.id">
              <td>{{ row.name }}</td>
              <td>¥{{ row.price }}</td>
              <td>{{ row.status }}</td>
              <td>
                <button class="link" @click="openDialog(row)">编辑</button>
                <button class="link danger" @click="remove(row.id)">删除</button>
              </td>
            </tr>
            <tr v-if="pagedRows.length === 0"><td colspan="4" class="empty">暂无数据</td></tr>
          </tbody>
        </table>
        <div class="pager">
          <button :disabled="page <= 1" @click="page--">上一页</button>
          <span>第 {{ page }} / {{ totalPages }} 页</span>
          <button :disabled="page >= totalPages" @click="page++">下一页</button>
        </div>
      </section>
    </main>
    <div v-if="dialogVisible" class="mask" @click.self="dialogVisible = false">
      <div class="dialog">
        <h3>{{ form.id ? "编辑商品" : "新增商品" }}</h3>
        <label>名称 <input v-model="form.name" /></label>
        <label>价格 <input v-model.number="form.price" type="number" /></label>
        <div class="dialog-actions">
          <button @click="dialogVisible = false">取消</button>
          <button @click="save">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";

const menus = ["商品管理", "订单管理", "用户管理", "系统设置"];
const current = ref("商品管理");
const keyword = ref("");
const statusFilter = ref("");
const page = ref(1);
const pageSize = 5;
const dialogVisible = ref(false);
const form = ref({ id: null, name: "", price: 0, status: "在售" });

const rows = ref([
  { id: 1, name: "机械键盘", price: 399, status: "在售" },
  { id: 2, name: "无线鼠标", price: 129, status: "在售" },
  { id: 3, name: "显示器支架", price: 199, status: "下架" },
  { id: 4, name: "USB 集线器", price: 89, status: "在售" },
  { id: 5, name: "笔记本内胆包", price: 59, status: "在售" },
  { id: 6, name: "拓展坞", price: 259, status: "下架" },
  { id: 7, name: "屏幕挂灯", price: 149, status: "在售" },
]);

const filtered = computed(() =>
  rows.value.filter(
    (r) =>
      r.name.includes(keyword.value) &&
      (!statusFilter.value || r.status === statusFilter.value)
  )
);
const totalPages = computed(() => Math.max(1, Math.ceil(filtered.value.length / pageSize)));
const pagedRows = computed(() =>
  filtered.value.slice((page.value - 1) * pageSize, page.value * pageSize)
);

function openDialog(row) {
  form.value = row
    ? { ...row }
    : { id: null, name: "", price: 0, status: "在售" };
  dialogVisible.value = true;
}
function save() {
  if (!form.value.name) return;
  if (form.value.id) {
    const idx = rows.value.findIndex((r) => r.id === form.value.id);
    rows.value[idx] = { ...form.value };
  } else {
    rows.value.push({ ...form.value, id: Date.now() });
  }
  dialogVisible.value = false;
}
function remove(id) {
  if (confirm("确认删除该商品？")) rows.value = rows.value.filter((r) => r.id !== id);
}
</script>

<style scoped>
.layout { display: flex; min-height: 100vh; }
.sidebar { width: 200px; background: #0f172a; color: #e2e8f0; padding: 20px 12px; }
.logo { font-weight: 700; margin-bottom: 24px; }
nav a { display: block; padding: 10px 12px; border-radius: 8px; cursor: pointer; color: #94a3b8; }
nav a.active, nav a:hover { background: #1e293b; color: #fff; }
.main { flex: 1; display: flex; flex-direction: column; }
.topbar { height: 56px; background: #fff; display: flex; align-items: center; justify-content: space-between; padding: 0 20px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }
.content { padding: 20px; }
.toolbar { display: flex; gap: 8px; margin-bottom: 16px; }
input, select { padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 8px; }
button { padding: 8px 14px; border: none; border-radius: 8px; background: #2563eb; color: #fff; cursor: pointer; }
button:disabled { opacity: 0.5; cursor: not-allowed; }
button.link { background: transparent; color: #2563eb; padding: 4px 8px; }
button.link.danger { color: #dc2626; }
table { width: 100%; background: #fff; border-radius: 12px; overflow: hidden; border-collapse: collapse; }
th, td { text-align: left; padding: 12px 16px; border-bottom: 1px solid #f1f5f9; }
th { background: #f8fafc; }
.empty { text-align: center; color: #94a3b8; }
.pager { display: flex; align-items: center; gap: 12px; margin-top: 16px; }
.mask { position: fixed; inset: 0; background: rgba(15,23,42,.45); display: flex; align-items: center; justify-content: center; }
.dialog { background: #fff; border-radius: 12px; padding: 24px; width: 360px; }
.dialog label { display: block; margin: 12px 0; }
.dialog label input { width: 100%; margin-top: 4px; }
.dialog-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; }
</style>
""",
        },
    },
]


def seed_templates(db: Session) -> int:
    count = 0
    for item in TEMPLATES:
        exists = db.query(Template).filter(Template.name == item["name"]).first()
        if exists is not None:
            continue
        db.add(
            Template(
                name=item["name"],
                description=item["description"],
                tech_stack=item["tech_stack"],
                files_json=item["files"],
                is_active=True,
            )
        )
        count += 1
    db.commit()
    return count
