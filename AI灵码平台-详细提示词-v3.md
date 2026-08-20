# AI灵码平台 — 构建提示词与实施状态（v3，同步版）

> 更新：2026-08-20。本文是产品目标、实施边界和当前代码状态的统一说明；代码、自动化测试和 `PROJECT_STATE.md` 是实现事实的最终依据。
>
> 续接规则：每轮先核对 `PROJECT_STATE.md` 与代码；若有冲突，以代码为准修正文档。一次只完成一个可验证的步骤，并在结束时更新状态文档（不超过 120 行）。

---

## 1. 产品目标与边界

AI灵码平台让用户以自然语言生成并迭代前端项目：创建项目 → 生成 → 静态预览 → 点选或聊天修改 → 查看差异 → 接受或撤销修改。

- 产物：HTML 多文件项目或 Vue 3 项目，不生成、托管用户后端服务。
- 当前不提供：正式部署/独立访问 URL、完整管理后台、计费配额、多模型路由、自定义域名和源码编辑器。
- 工作区、缩略图与版本目录统一使用 ASCII 标识：`yyyy-mm-dd-hh-mm-ss-random`；不使用项目标题、中文或纯数字序号。

## 2. 当前里程碑

| 里程碑 | 状态 | 已交付内容 |
| --- | --- | --- |
| M1：生成核心回路 | 完成 | 项目、会话、LangGraph 生成工作流、构建、SSE、静态预览、任务恢复与取消。 |
| M2：可控修改回路 | 完成 | 点选/聊天修改、源码快照、差异、接受、撤销、交互与构建校验。 |
| M3：异步素材编排、质量与安全闭环 | 进行中 | 规则护轨、工具策略、基础回归评测与第一版素材编排已完成；下一步是持久化自评、错误知识库和 LLM 二次护轨。 |
| M4：部署与发布 | 未开始 | 数据模型预留，尚无部署 API、部署服务或独立 URL。 |
| M5：运营与管理 | 未开始 | 已有认证和部分管理员 API；完整后台、指标和配额治理未实现。 |
| M6：生产化 | 未开始 | Docker/Redis/队列、隔离执行和可观测性尚未落地。 |

## 3. 已实现架构

```text
Vue 3 + Vite + TypeScript + Pinia + Vue Router
  └─ REST + EventSource(SSE) ── FastAPI
       ├─ 项目 / 会话 / 模板 / 版本 / 预览 / 修改 API
       ├─ 任务队列、SSE 事件代理和任务恢复
       ├─ LangGraph 生成工作流
       ├─ 模型 Provider、工具定义/策略/执行层
       └─ SQLite + SQLAlchemy + Alembic
             └─ storage/workspaces/{multifile|vue}/{slug}
```

- 模型调用采用 OpenAI 兼容 Provider 契约；默认 mock 模式可离线测试，配置后可调用 DeepSeek。不是 LangChain 的模型调用链。
- 生成编排采用 LangGraph；修改流程目前是受控异步任务，不是 LangGraph 图。
- 前端实时输出使用 SSE，不使用 WebSocket。SSE 支持 `event_id` 和 `Last-Event-ID` 的进程内断线补发；服务重启后的历史由持久化会话消息回放。
- 预览由后端托管工作区或 Vue `dist` 静态文件。Vue 的构建命令会使用 `--base=./`；不启动 Vite 开发服务器。

## 4. 已实现功能

### 4.1 项目与身份

- JWT 登录、刷新、当前用户，注册开关和内置管理员初始化。
- 项目 CRUD、模板、会话和消息历史；项目数据按 owner 隔离。
- 管理员设置/用户管理 API 已存在；系统设置目前为进程内状态，非持久化运营配置。
- 创建项目时由“路由 Agent”判断 HTML 多文件或 Vue 的适配度；建议与用户选择冲突时要求确认，并将确认结果写入生成约束和项目标签。

### 4.2 生成、工具与构建

生成工作流的实际顺序为：

```text
input_guardrail → parse_requirements → create_plan → generate_code
→ output_guardrail → validate_build ──失败且可修复──→ generate_code
→ summarize
```

- `input_guardrail` 与 `output_guardrail` 为确定性规则检查，危险提示、路径和命令会被拦截并记录护轨事件。
- 生成和修改 Agent 共用模型 Provider 与工具层；工具层区分 schema、策略校验、调用记录和执行，修改 Agent 没有命令执行权限。
- 生成会输出阶段、思考、模型文本、工具开始/完成、写文件、素材检索候选/完成、构建日志、完成、错误和澄清等 SSE 事件。
- 构建支持 mock 与真实模式；Vue 使用受控的 `npm install`、`npm run build`，静态 JS 使用语法检查。构建失败可进入有限次数修复循环。

### 4.3 预览、修改与版本

- 项目页同屏显示对话、阶段栏和 iframe 预览；预览支持桌面、平板、手机视口。
- 点选元素会收集 DOM 定位信息；用户也可直接在聊天框提出修改。两种入口进入同一修改任务。
- 修改流程：定位 → 修改前快照 → 受策略约束的源码编辑 → 构建/交互检查 → 修改后快照、diff、总结。
- 构建或交互校验失败会自动恢复修改前快照。完成后用户可接受修改，或撤销到修改前版本；这些状态和历史可在重进项目后恢复。
- 任务恢复按项目 ID 重新订阅，防止项目之间复用聊天和 SSE 状态。

## 5. 提示词与 Agent 边界

所有实际使用的提示词均为 Markdown 文件，位于 `backend/app/prompts/`，由代码读取；不再维护与代码分离的大段内联提示词。

| 类型 | 文件 | 职责 |
| --- | --- | --- |
| 路由 Agent | `route_agent.md` | 判断 HTML/Vue 适配度与是否需要用户确认。 |
| 生成 Agent | `generation_agent.md` | 在工具策略约束下生成项目文件。 |
| 修改 Agent | `modification_agent.md` | 依据元素上下文修改源码，保持可交互性。 |
| 生成子任务 | `generation_tasks/requirement_parser.md` | 提取结构化需求。 |
| 生成子任务 | `generation_tasks/implementation_plan.md` | 生成实施计划。 |
| 生成子任务 | `generation_tasks/delivery_summary.md` | 输出交付总结。 |

回归评测基线位于 `backend/evals/agent_regression_cases.json`，pytest 会加载并校验路由、生成工具工作流、修改澄清和交互约束。

## 6. 当前 API 与数据边界

FastAPI 当前注册的路由模块为：`auth`、`users`、`projects`、`sessions`、`generations`、`templates`、`admin`、`preview`、`versions`、`modifications`。

- 已提供生成任务创建/查询/取消、追加消息、SSE 流、预览状态/文件树、版本与修改相关 API。
- `GET /api/generations/{id}/evaluation` 仍是 M3 占位接口，返回空评估；不能将其视为已完成自评。
- 部署、指标和评估相关 ORM 表已经预留，但没有对应的完整服务/API 流程；不能将数据模型预留视作上线功能。

## 7. 当前安全与可靠性边界

- 已有：所有者隔离、路径穿越防护、输入/输出规则护轨、工具权限/参数/写入量限制、修改前后快照、失败回滚、SSE 断线游标补发、任务取消/超时/恢复。
- iframe 预览采用 sandbox，但目前仍允许脚本、同源、表单和弹窗，以保障生成项目的基础运行；严格 CSP 与容器级执行隔离属于 M6。
- 当前任务队列和 SSE 缓冲是进程内实现；多进程共享、Redis 队列和跨进程实时恢复尚未实现。
- 生成命令只允许托管预览需要的白名单操作；修改 Agent 无 shell 工具。该机制不是 Docker 沙箱，不能宣称具备生产级代码隔离。

## 8. 已实现：第一版异步素材编排

素材编排用于补足“仅用 CSS 或前端组件拼出图形”的限制。生成 Agent 已可调用受控的 `collect_assets` 工具：后端创建 `asset_jobs` 记录，异步访问允许的来源适配器，持久化候选和选用结果，并向生成 SSE 流发送事件。修改 Agent 当前不具备该工具权限。

### 8.1 目标与交互

- 生成 Agent 先判断素材是否真正需要；简单图形优先使用 CSS、已有项目资产或不使用外部素材，避免无意义请求。
- Agent 只能传递 `kind`、语义查询、用途和方向；不能获得任意 URL、网络访问、下载路径或来源密钥。
- 来源适配器在事件循环中异步执行，并可并发扩展；第一版实现 Iconify/Lucide 图标适配器和可选 Pexels 图片适配器。Pexels 仅在配置 `AI_LINGMA_ASSET_PEXELS_API_KEY` 后启用。
- 工具会自动选择首个通过来源策略的候选。图标下载后经大小、内容类型与主动 SVG 内容校验，写入 `assets/icons/`；图片保留来源允许的外链及署名，不默认下载。
- 无候选、来源不可达或素材校验失败时，任务状态仍会完成但返回降级结果；生成 Agent 必须继续交付无外部素材版本并说明原因。
- 如果没有合规或可访问的候选项，任务应给出澄清问题或降级为占位图/CSS 方案，不能把“未写入文件”当作修改失败。

### 8.2 编排与数据流

```text
需求/修改上下文
  └─ 素材决策（不需要 / 需要）
       └─ 创建 asset_collection 子任务（来源适配器异步收集）
            ├─ 查询受允许的图标/插图/图片来源
            ├─ 标准化候选元数据、许可证与来源
            ├─ 安全下载或生成受控外链引用
            └─ 返回候选、降级原因或澄清请求
       └─ 自动选择安全候选 → 写入项目资产清单 → Agent 引用素材 → 构建/预览校验
```

- 已实现 `asset_jobs`（`pending/running/succeeded`）和 `project_assets`；任务关联项目、生成任务和会话，候选、选用项、失败原因均落库。
- `assets/manifest.json` 与本地图标会被普通项目版本快照覆盖；项目删除会清理素材记录和文件。项目资产可经 `GET /api/projects/{project_id}/assets` 查询。
- 当前素材任务跟随 Agent 工具调用完成，并发的是来源 I/O；独立 worker、任务取消、跨进程恢复、图片转码和缩略图生成仍是后续增强项。

### 8.3 来源、合规与安全约束

- 第一版将来源固定为 Iconify 的 Lucide 图标集与可选 Pexels API；禁止让模型任意抓取网页、搜索结果页或热链不明版权图片。
- 每个选用素材记录来源 URL、许可证、署名、获取时间、哈希（本地图标）和本地/外链位置；无法获取候选时不纳入产物。
- 图标只从固定 Iconify API URL 下载，并限制为 256 KiB、受限 MIME 和无脚本/事件处理器的 SVG；图片适配器仅保留返回的 HTTPS 外链。
- 禁止下载可执行内容、HTML 和未校验 SVG；不得携带用户令牌或私密数据访问第三方站点。
- 当前提供素材查询 API；项目页可接收 SSE/历史消息。素材替换/删除 UI、更多来源、显式人工选择和严格重定向校验属于后续工作。

### 8.4 第一阶段实施范围与验收

1. [x] `collect_assets` 工具契约、策略层、异步任务模型/服务、SSE 与会话历史事件。
2. [x] 素材表/`assets/manifest.json`/`assets/icons` 约定、项目资产查询 API、快照覆盖与项目删除清理。
3. [x] Iconify/Lucide 和可选 Pexels 白名单适配器；离线回归测试使用 mock 适配器。
4. [x] 无候选和校验失败时的降级结果；生成 Agent 可消费工具返回的素材路径或外链。
5. [ ] 素材任务取消/跨进程恢复、图片来源在浏览器的署名展示、用户选择/替换 UI、图片转码与缩略图、真实来源的端到端验收。

## 9. 目录约定

```text
backend/
  app/
    agents/                 # 生成 LangGraph、工具层与路由 Agent
    api/                    # FastAPI 路由
    prompts/                # 唯一的 Agent/子任务 Markdown 提示词来源
    services/               # 模型、任务、SSE、预览、版本等服务
  evals/                    # Agent 回归场景
  tests/                    # 后端及评测测试
frontend/src/
  views/ components/ stores/ services/
storage/
  workspaces/{multifile|vue}/{slug}/
  thumbnails/{slug}/
  versions/{slug}/
docs/
  BROWSER_ACCEPTANCE.md
PROJECT_STATE.md            # 当前实施状态，≤120 行
```

## 10. 当前验收事实

- 后端全量测试：`python -B -m pytest -q` 已通过 84 项（最近一次代码核对）。
- 前端：`npm run build` 已通过；首屏改为 Element Plus 必要组件注册与按需样式，避免全量组件包进入入口。
- 真实模型冒烟：`backend/smoke_agent.py`、`smoke_route_agent.py`、`smoke_modification.py` 已验证生成、路由与带点击反馈的修改链路。
- 浏览器人工验收清单在 `docs/BROWSER_ACCEPTANCE.md`；当前自动化环境无可控制浏览器，因此该清单仍需在实际浏览器中执行。

## 11. 后续：M3-2 评估结果闭环

完成异步素材编排后，应实现“生成/修改完成后的持久化评估闭环”：

1. 定义统一评估结果（结构完整性、构建、交互、需求覆盖、护轨）及失败原因；
2. 在生成和修改任务结束时写入 `evaluations`，并让现有 evaluation API 返回真实记录；
3. 在项目页保留可读的评估摘要和失败修复建议，不覆盖模型交付总结；
4. 以现有 `backend/evals/` 场景新增通过/失败测试，再完成浏览器验收清单中的生成、修改、重进恢复用例。

完成 M3-2 后，再决定是否加入 LLM 二次护轨与错误知识库（M3-3），随后才进入部署（M4）。
