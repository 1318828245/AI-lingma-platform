# AI 灵码平台（AI-Lingma-Platform）

用户用自然语言描述需求 → 自动生成可运行前端工程 → 实时预览点选修改 → 一键部署独立 URL。
详细产品与技术规格见 [AI灵码平台-详细提示词-v3.md](AI灵码平台-详细提示词-v3.md)，构建进度见 `PROJECT_STATE.md`。

## 当前进度（M1 骨架阶段）

已实现：后端骨架（FastAPI + SQLAlchemy 2.x）、全部数据模型、JWT 认证（bcrypt）、内置管理员、3 个种子模板、项目/会话/模板/管理员基础 API、**生成工作流（LangGraph：解析→规划→生成→构建→修复）+ SSE 进度流 + 任务取消/超时/恢复**、**Vue 3 前端（登录/项目列表/生成对话/实时预览）+ 服务端预览代理**。M1 里程碑已完成。

### 模型与工具调用边界

- `services/model/`：以 `ModelRequest`、`ModelResponse`、`ModelToolCall` 作为供应商无关契约；当前 `OpenAICompatibleProvider` 负责 Chat Completions 请求与流式增量聚合。
- `services/llm.py`：保留业务门面与 mock 模式，不再直接承担 HTTP/SSE 协议解析。
- `agents/tooling/`：集中维护工具 schema、调用/结果契约、Agent 权限策略、执行器和安全展示摘要。
- 生成 Agent 可调用文件与构建工具；修改 Agent 不允许运行命令。所有工具调用均先经参数、敏感路径与写入大小校验，再进入副作用执行。

### 存储命名

项目显示名称可以使用中文，但所有文件系统产物只使用 `yyyy-mm-dd-hh-mm-ss-random`。同一个标识同时用于 `storage/workspaces/` 下的工作区、`storage/thumbnails/<id>.png` 和 `storage/versions/<id>/`；版本快照子目录也使用同样格式，绝不使用项目数字 ID。

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
LLM 已接入 DeepSeek V4：`AI_LINGMA_LLM_MODEL=deepseek-v4-flash`、
`AI_LINGMA_LLM_REASONING_EFFORT=high`，密钥等配置在 `backend/.env`
（已被 gitignore，不会提交；需要时用 `backend/.env.example` 复制）。
移除 `.env` 中的配置即回退到内置 mock 执行器（无需 Key）。
配置后，生成环节由 DeepSeek 通过 ReAct 工具循环自主读写代码
（list_files / read_file / write_file / edit_file / run_command / finish），
思考过程与正文通过 SSE **逐字流式**推送到对话流（reasoning_delta/assistant_delta），
工具调用以“调用中…”转圈状态呈现。

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
进入项目后是“左对话 + 右实时预览”同屏工作台：提交需求后，右侧预览随生成过程实时更新。

默认管理员：`admin / admin123`（首次登录后请修改；生产环境通过 `.env` 的
`AI_LINGMA_ADMIN_USERNAME` / `AI_LINGMA_ADMIN_PASSWORD` 指定）。

配置项见 `backend/.env.example`。

## 测试

```powershell
cd backend
python -m pytest -q
```

当前代码包含 70 个后端测试，最近一次 `python -m pytest -q` 全部通过；前端 `npm run build` 已包含 `vue-tsc --noEmit` 类型检查并通过。后端测试配置已关闭不必要的 pytest 缓存插件，避免在当前工作区文件系统上测试完成后卡在收尾阶段。

当前 M2-1/M2-2/M2-3 已完成：生成或修改成功会自动创建项目版本快照；提供版本列表、版本 diff、回滚 API；预览支持点选元素、采集元素快照并提交修改；真实 LLM 配置下由修改 Agent 通过工具循环完成文本、样式或结构局部编辑，未配置 LLM 时使用 Mock 修改器离线回归。

## 安全边界

- 默认 SQLite + 本地文件存储；生产切换 PostgreSQL 与 Docker 沙箱（见提示词 v3）。
- **命令执行默认 shell 模式**（`AI_LINGMA_COMMAND_MODE=shell`）：AI 的工具命令等同本机
  终端权限，支持 `&&`/`||`/`;` 与引号；仅限本地开发。生产环境务必改为
  `sandbox`（白名单受限执行）并配合 Docker 沙箱。
- 注册默认关闭（`AI_LINGMA_REGISTER_ENABLED=false`），仅管理员登录。
- Docker 沙箱、完整护轨（LLM 复核）、部署引擎等里程碑尚未实现，暂不用于生产。

## 本轮前端与执行能力更新（2026-08-18）

- 生成工作台采用明亮视觉体系：白色内容面板、浅灰画布、蓝紫主色、统一圆角与阴影。
- 统一字体与信息层级：页面标题更醒目，正文、事件标题、辅助信息和等宽代码文字分别设置字号与字重。
- 左右工作区支持按住鼠标拖动调整宽度；使用 Pointer Events 与边界约束，松开鼠标后立即停止拖动。
- 左侧对话区区分 Stage、Thinking、工具调用、文件写入、构建日志和错误事件，不再全部使用相同气泡样式。
- `reasoning_delta`、`assistant_delta` 和 `file_written` 通过 SSE 实时展示；文件写入事件可展开查看当前生成代码。
- 桌面、平板、手机预览视口会根据预览容器宽度适配，减少无效留白。
- 命令执行兼容完整字符串命令及 shell 组合语法；补充 `ls -la`、`wc -l`、`head -c` 等常用检查命令的处理。
- 前端验证：`npm run build`（包含 `vue-tsc --noEmit`）通过；后端全量回归 63 例通过。

- M3：LLM 护轨复核、5 维自动评估、低分自动修复循环和评估结果展示。
- M3：5 维自动评估、低分自动修复、LLM 二次护轨。
- M4：独立 slug 部署、部署历史、部署回滚与下线。
- M5/M6：完整 RBAC/配额/监控后台、Docker 沙箱、Compose 生产部署与数据运维能力。
