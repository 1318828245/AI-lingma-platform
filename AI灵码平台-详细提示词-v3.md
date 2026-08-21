# AI灵码平台 — 构建提示词与实施状态（v3，同步版）

> 更新：2026-08-22。本文是产品目标、实施边界和当前代码状态的统一说明；代码、自动化测试和 `PROJECT_STATE.md` 是实现事实的最终依据。
>
> 续接规则：每轮先核对 `PROJECT_STATE.md` 与代码；若有冲突，以代码为准修正文档。一次只完成一个可验证的步骤，并在结束时更新状态文档（不超过 120 行）。

---

## 1. 产品目标与边界

AI灵码平台让用户以自然语言生成并迭代前端项目：创建项目 → 生成 → 静态预览 → 点选或聊天修改 → 查看差异 → 接受或撤销修改。

- 当前模式：生成 HTML 多文件项目或 Vue 3 demo/静态站点；现有生成、修改、版本和发布流程保持不变，不生成或托管用户后端服务。
- Alpha 目标（仅介绍，未实现）：以“接口契约优先 + AI 辅助”为方式，导入 OpenAPI/Swagger 等接口文档并结合自然语言需求，生成可连接真实测试环境的 Vue 前端。自然语言描述页面与业务意图；接口契约约束请求、字段、鉴权和错误处理。
- Alpha 的计划产物：类型安全 API Client、数据访问层、Mock/真实数据源切换，以及可由用户确认的页面—接口—字段绑定清单；不得仅依赖自然语言猜测任意后端接口。
- Beta 目标（仅介绍，未实现）：以受控规格生成全栈应用交付物，包括前端、后端服务、数据库模型/迁移、鉴权和部署配置。Beta 必须以结构化规格、隔离执行、测试证据与人工审批为前提，不承诺仅凭自然语言生成任意生产后端。
- 已提供：静态发布与稳定项目访问地址、管理员运营后台、用户生成配额与审计记录。
- 当前不提供：Alpha 数据源导入、真实接口绑定、密钥管理、接口验证和 Alpha 项目创建；Beta 后端/数据库/鉴权/部署生成；以及用户后端托管、多模型路由、自定义域名、源码编辑器和生产级容器隔离执行环境。
- 工作区、缩略图与版本目录统一使用 ASCII 标识：`yyyy-mm-dd-hh-mm-ss-random`；不使用项目标题、中文或纯数字序号。

## 2. 当前里程碑

| 里程碑 | 状态 | 已交付内容 |
| --- | --- | --- |
| M1：生成核心回路 | 完成 | 项目、会话、LangGraph 生成工作流、构建、SSE、静态预览、任务恢复与取消。 |
| M2：可控修改回路 | 完成 | 点选/聊天修改、源码快照、差异、接受、撤销、交互与构建校验。 |
| M3：异步素材编排、质量与安全闭环 | 完成 | 异步素材 worker、候选选择/替换、四维交付评估与低分修复闭环。 |
| M4：部署与发布 | 完成 | 静态发布、公开 slug 地址、稳定项目地址、历史版本恢复与下线。 |
| M5：运营与管理 | 完成 | 管理台、搜索分页、配额/启停、素材重试与持久化审计。 |
| M6-0：可观测性 | 完成 | 健康、队列、成功率、告警和项目级执行链路观测。 |
| M6-1：Docker 命令沙箱 | 完成 | 可选 Docker 执行模式、无网络/最小权限/资源限制、基础镜像与回归测试。 |
| M6：生产化 | 进行中 | M6-2 已加入 Compose 基线（前后端镜像、Nginx、PostgreSQL、持久化目录与健康检查）；服务器镜像构建、HTTPS、备份、独立命令执行器与跨进程队列尚未落地。 |
| M7 Alpha：数据集成 | 规划中 | OpenAPI/Swagger 导入、契约解析、真实数据绑定与接口验证；当前仅有前端介绍入口。 |
| M8 Beta：全栈交付 | 概念阶段 | 受控后端、数据库、鉴权、测试与部署交付；当前仅有前端介绍入口。 |

## 3. 已实现架构

```text
Vue 3 + Vite + TypeScript + Pinia + Vue Router
  └─ REST + EventSource(SSE) ── FastAPI
       ├─ 项目 / 会话 / 模板 / 版本 / 预览 / 修改 / 发布 / 管理 API
       ├─ 生成与素材任务队列、SSE 事件代理和任务恢复
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
- 管理员运营台支持项目、用户、任务和发布记录管理；可调整用户生成配额、启停账号、重试失败素材任务，并记录持久化审计日志。
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
- 成功生成或修改会写入四维交付评估（可执行性、结构完整性、需求与体验、安全）；低分修复建议须经用户确认后才会创建受限修改任务。
- 版本快照可发布为静态站点。稳定项目地址始终指向当前线上版本；可恢复历史发布或下线当前公开版本。

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

FastAPI 当前注册的路由模块包括：`auth`、`users`、`projects`、`sessions`、`generations`、`templates`、`admin`、`preview`、`versions`、`modifications` 与 `deployments`；项目资产由项目 API 提供。

- 已提供生成任务创建/查询/取消、追加消息、SSE 流、预览状态/文件树、版本/修改/素材/评估与发布相关 API。
- `GET /api/generations/{id}/evaluation` 返回真实持久化评估；项目工作台可重新检查并显示修复建议。
- 管理员 `GET /api/admin/observability` 聚合数据库、队列、视觉评估与素材来源健康，并提供指标、告警和有限时间线。

## 7. 当前安全与可靠性边界

- 已有：所有者隔离、路径穿越防护、输入/输出规则护轨、工具权限/参数/写入量限制、修改前后快照、失败回滚、SSE 断线游标补发、任务取消/超时/恢复。
- iframe 预览采用 sandbox，但目前仍允许脚本、同源、表单和弹窗，以保障生成项目的基础运行；严格 CSP 与容器级执行隔离属于 M6。
- 当前任务队列和 SSE 缓冲是进程内实现；多进程共享、Redis 队列和跨进程实时恢复尚未实现。
- M6-2 的 Compose 将 PostgreSQL、后端和 Web 服务置于内部网络，Web 端口只绑定宿主机 `127.0.0.1:8080`，由宿主 Nginx 再提供公网 HTTPS；后端不挂载 `/var/run/docker.sock`。初始生产配置为 `mock + sandbox`，真实代码执行须等待独立沙箱执行器。
- `AI_LINGMA_COMMAND_MODE=docker` 可将非内置检查命令放入独立 Docker 容器：默认无网络、移除 capabilities、禁止新增权限、限制 PID/CPU/内存并使用只读根文件系统；仅工作区可写。镜像必须预构建，依赖通过镜像或受控离线缓存提供。开发默认 `shell` 仍是本机终端，不应作为生产隔离声明。

## 8. 已实现：异步素材编排

素材编排用于补足“仅用 CSS 或前端组件拼出图形”的限制。生成和修改 Agent 都可创建受控的 `asset_jobs`：独立 worker 异步访问允许的来源适配器，持久化候选和选用结果，并向任务 SSE 流发送事件。

### 8.1 目标与交互

- 生成 Agent 先判断素材是否真正需要；简单图形优先使用 CSS、已有项目资产或不使用外部素材，避免无意义请求。
- Agent 只能传递 `kind`、语义查询、用途和方向；不能获得任意 URL、网络访问、下载路径或来源密钥。
- 独立 worker 支持并发检索、启动恢复、取消和重试。图标来源为 Iconify/Lucide；照片按 Pexels、Pixabay、Unsplash 自动降级，插图/矢量使用 Pixabay；各图片来源仅在对应 API Key 配置后启用。
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
- 素材任务支持候选缩略图/轮播、分页、用户选择与替换；仅当源码存在唯一素材占位符时，才受控回填素材并刷新预览。Vue 项目回填后会重新构建预览产物。

### 8.3 来源、合规与安全约束

- 图标来源固定为 Iconify 的 Lucide 图标集；照片与插图仅从受控适配器检索，禁止让模型任意抓取网页、搜索结果页或热链不明版权图片。
- 每个选用素材记录来源 URL、许可证、署名、获取时间、哈希（本地图标）和本地/外链位置；无法获取候选时不纳入产物。
- 图标只从固定 Iconify API URL 下载，并限制为 256 KiB、受限 MIME 和无脚本/事件处理器的 SVG；图片适配器仅保留返回的 HTTPS 外链。
- 禁止下载可执行内容、HTML 和未校验 SVG；不得携带用户令牌或私密数据访问第三方站点。
- 当前提供素材查询 API；项目页可接收 SSE/历史消息，并支持候选项的人工选择与替换。更多来源、严格重定向校验和图片转码仍属后续增强。

### 8.4 当前边界

- 图片来源的真实调用需要分别配置 Pexels、Pixabay 或 Unsplash Key；未配置来源会被自动跳过。
- 来源错误会写入素材完成事件与 `asset_jobs.error`，不伪装为“未找到素材”。
- 跨进程实时恢复、图片转码及生产级队列仍属于 M6 范围。

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
  publish/{deployment-slug}/
docs/
  BROWSER_ACCEPTANCE.md
PROJECT_STATE.md            # 当前实施状态，≤120 行
```

## 10. 当前验收事实

- 后端：管理员观测接口测试最近通过 7 项；管理与发布定向测试最近通过 9 项。
- 前端：`npm run build` 已通过；首屏改为 Element Plus 必要组件注册与按需样式，避免全量组件包进入入口。
- 真实模型冒烟：`backend/smoke_agent.py`、`smoke_route_agent.py`、`smoke_modification.py` 已验证生成、路由与带点击反馈的修改链路。
- 浏览器人工验收已按 `docs/BROWSER_ACCEPTANCE.md` 通过，覆盖技术栈确认、生成/修改恢复与预览性能。

## 11. 下一步：M6 生产化

1. 在 Docker 主机验证 `docker-compose.yml` 的前后端与 PostgreSQL 镜像构建、启动和健康检查，配置宿主 Nginx、域名、HTTPS 以及 PostgreSQL/storage 的备份和升级/回滚；
2. 在不向公开后端暴露 Docker socket 的前提下，完成独立命令沙箱执行器与严格预览隔离；随后落地跨进程任务队列和数据运维能力；
3. 在 M6 基础稳定后，保留 LangGraph 作为业务编排层，采用适配器模式渐进评估 Deep Agents：先接入上下文压缩、工作区 filesystem backend 与 Todo，再将生成和修改迁移为不同权限的 harness profile；Docker sandbox、审批 interrupt、长期记忆和只读 verifier 子 Agent 仅在 PoC 验证质量、成本及事件兼容性后启用。
4. 启动 M7 Alpha：以 OpenAPI/Swagger 导入为首个数据源，生成类型安全 API Client 与数据访问层，支持 Mock/真实数据源切换，并在生成前要求用户确认页面—接口—字段映射；现有 demo 生成模式继续独立保留。
5. 在 M7 的契约、权限和验证机制稳定后评估 M8 Beta：从结构化规格和受控 sandbox 开始，再逐步加入后端模板、数据库迁移、鉴权、测试与部署；当前 Beta 入口仅展示目标，不创建或运行全栈项目。

不采用 OpenClaw 或 DeepSeek Harness 作为平台核心运行时；项目、版本、预览、发布、审批和审计仍由本平台负责，Deep Agents 仅可作为受控代码任务执行 harness。生成 profile 可读写项目文件并使用受控构建和素材工具；修改 profile 仅能读写获授权文件且无 shell；verifier profile 只读并输出构建、测试和质量证据。任务耐久性仍由 LangGraph checkpoint 与持久化 worker 承担。
