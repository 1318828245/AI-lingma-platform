# AI 灵码平台（AI-Lingma-Platform）

用户用自然语言描述需求 → 自动生成可运行前端工程 → 实时预览点选修改 → 一键部署独立 URL。
详细产品与技术规格见 [AI灵码平台-详细提示词-v3.md](AI灵码平台-详细提示词-v3.md)，构建进度见 `PROJECT_STATE.md`。

## 当前进度（M1 骨架阶段）

已实现：后端骨架（FastAPI + SQLAlchemy 2.x）、全部数据模型、JWT 认证（bcrypt）、内置管理员、3 个种子模板、项目/会话/模板/管理员基础 API、**生成工作流（LangGraph：解析→规划→生成→构建→修复）+ SSE 进度流 + 任务取消/超时/恢复**、**Vue 3 前端（登录/项目列表/生成对话/实时预览）+ 服务端预览代理**。M1 里程碑已完成。

## 快速体验生成流程

1. 启动后端（见下）
2. 登录拿令牌：

```powershell
$login = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/auth/login `
  -ContentType 'application/json' -Body '{"username":"admin","password":"admin123"}'
$headers = @{ Authorization = "Bearer $($login.access_token)" }
```

3. 新建项目并提交需求：

```powershell
$project = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/projects `
  -Headers $headers -ContentType 'application/json' `
  -Body '{"name":"我的名片","template":"个人名片页","tech_stack":"html"}'
$gen = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/projects/$($project.id)/generations" `
  -Headers $headers -ContentType 'application/json' `
  -Body '{"requirement":"做一个深色风格的个人名片页"}'
```

4. 轮询状态或订阅 SSE：

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/generations/$($gen.id)" -Headers $headers
# 浏览器打开：http://127.0.0.1:8000/api/generations/<id>/events 看实时进度
```

默认 `AI_LINGMA_BUILD_MODE=real` 会真实执行 npm 构建；无网络时设 `mock`。
LLM 默认使用内置 mock 执行器（无需 Key），配置 `AI_LINGMA_LLM_BASE_URL/API_KEY/MODEL`
后切换 OpenAI 兼容协议。

## 启动后端（开发环境）

```powershell
cd backend
python -m pip install -r requirements.txt   # 使用 conda 环境 env01-p10-drawimg
python -m app.scripts.init                  # 初始化数据库/管理员/种子模板
python -m uvicorn app.main:app --reload --port 8000
```

运行环境：conda `env01-p10-drawimg`（Python 3.10，已预装 langgraph 1.2.x）。

## 启动前端（开发环境，另开一个终端）

```powershell
cd frontend
npm install
npm run dev
```

浏览器打开 `http://127.0.0.1:5173`，用 `admin / admin123` 登录。
Vite 已配置 `/api` 与 `/preview` 代理到后端 8000。

默认管理员：`admin / admin123`（首次登录后请修改；生产环境通过 `.env` 的
`AI_LINGMA_ADMIN_USERNAME` / `AI_LINGMA_ADMIN_PASSWORD` 指定）。

配置项见 `backend/.env.example`。

## 测试

```powershell
cd backend
python -m pytest -q
```

## 安全边界

- 默认 SQLite + 本地文件存储；生产切换 PostgreSQL 与 Docker 沙箱（见提示词 v3）。
- 注册默认关闭（`AI_LINGMA_REGISTER_ENABLED=false`），仅管理员登录。
- Docker 沙箱、完整护轨（LLM 复核）、部署引擎等里程碑尚未实现，暂不用于生产。
