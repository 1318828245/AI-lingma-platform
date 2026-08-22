# PROJECT_STATE

> 部署流程见 [docs/部署手册.md](docs/部署手册.md)，日常命令见 [docs/部署命令.md](docs/部署命令.md)。当前服务器已确认采用 OpenCloudOS 9.6，Docker 29.7.2/Compose v5.5.0 已验收。M6-2 部署资产、真实 LLM 配置说明、HTTPS、备份/恢复和升级手册已完成；域名解析、HTTPS 签发、真实 API 验收和恢复演练需在服务器执行。

更新：2026-08-22（以当前代码和自动化验证为准）

## 当前里程碑

- 当前：M6-0 可观测性完成；M3/M4/M5 交付与运营闭环完成。
- M1 生成核心回路：完成。
- M2 可控修改回路：完成。
- M5-2 运营动作、M6-0 可观测性：完成；M6-1 Docker 命令沙箱：完成；M6-2 生产部署资产与运维手册：完成，待服务器验收。
- Alpha（接口契约驱动的真实数据前端生成）：仅完成产品介绍页，尚未实现数据源导入、真实接口绑定或 Alpha 项目创建。
- Beta（受控全栈应用生成）：仅完成产品介绍页，尚未生成后端服务、数据库、鉴权或部署交付物。

## 已完成

- [x] 身份、项目、模板、会话、消息和基础管理员 API；项目按 owner 隔离。
- [x] 工作区、缩略图、版本目录统一使用 `yyyy-mm-dd-hh-mm-ss-random` ASCII 标识；按 `multifile`/`vue` 分流存储。
- [x] 路由 Agent 在创建前校验 HTML/Vue 适配度，冲突时要求确认。
- [x] 生成 LangGraph：护轨 → 需求解析 → 计划 → 生成 → 输出护轨 → 构建/修复 → 总结。
- [x] 模型 Provider、工具 schema/策略/执行分层；生成和修改使用统一工具链，修改无 shell 权限。
- [x] SSE 实时事件、`event_id`/`Last-Event-ID` 进程内补发、运行中任务重订阅与历史回放。
- [x] 静态预览、视口切换、Vue `dist` 托管及 `--base=./` 构建修复。
- [x] 点选和聊天修改、源码快照、diff、接受、撤销、构建/交互失败自动回滚。
- [x] 规则护轨、路径防护、工具参数/权限/写入量限制和护轨事件记录。
- [x] 提示词收敛为 `backend/app/prompts/` 下 6 个 Markdown 文件；Agent 回归场景位于 `backend/evals/`。
- [x] 前端入口按需注册 Element Plus 必要组件与样式，避免全量组件包影响首屏。
- [x] 异步素材编排：生成和修改 Agent 均可创建后台 `asset_jobs`；独立 worker 并发检索来源，支持启动恢复、取消、重试、候选选择/替换，并在源码唯一占位符存在时受控回填素材。
- [x] 素材来源策略：Iconify/Lucide 图标经固定来源下载、大小/MIME/主动 SVG 校验后写入 `assets/icons/`；照片按 Pexels、Pixabay、Unsplash 自动降级检索，插画/矢量由 Pixabay 提供，均仅保留来源外链与署名，需分别配置 API Key。
- [x] `assets/manifest.json` 纳入项目版本快照，项目资产可通过 `GET /api/projects/{id}/assets` 查询，删除项目时清理记录和文件。
- [x] M4-1 静态发布：Vue 项目从版本快照复制 `dist/`，HTML/multifile 项目复制静态根交付物到独立发布目录，生成绝对公开 slug 地址；工作台发布中心展示发布状态、版本、访问链接与失败原因。
- [x] M4-2 发布管理：稳定项目地址只指向当前线上版本；可从成功的历史发布恢复线上版本，并可下线当前版本使稳定地址与版本公开链接立即失效。
- [x] M5-1 运营总览：管理员可在独立管理台查看项目、用户、生成/修改/素材任务与发布记录；首页仅向管理员展示管理台入口，路由和 API 均校验管理员权限。
- [x] M5-2 运营动作：管理台支持按分区搜索与分页，可修改其他用户的生成配额和启停状态，并可重新排队失败素材任务；用户管理、平台设置、素材重试和发布创建/上线/下线均写入持久化审计记录。
- [x] M6-0 可观测性：`/api/admin/observability` 聚合数据库、进程内生成/素材队列、视觉评估和素材来源的健康状态，计算队列深度、成功率、失败事件并给出告警；管理台按运营大屏、项目管理、用户管理、操作管理组织，大屏限制最近 12 条事件，项目运行观测限制选中项目最近 20 条链路事件。
- [x] M6-1 Docker 命令沙箱：`AI_LINGMA_COMMAND_MODE=docker` 时，非内置检查命令在独立容器中执行；默认无网络、移除 capabilities、禁止新增权限、限制 PID/CPU/内存、只读根文件系统，仅将项目工作区挂载到容器。基础镜像与部署说明位于 `backend/docker/sandbox/`；依赖必须预构建或使用受控离线缓存。
- [x] M6-2 生产部署资产：前后端镜像、内部 PostgreSQL、Nginx 反代、健康检查、仅绑定 `127.0.0.1:8080` 的 Compose 配置、真实 DeepSeek 配置模板、备份脚本、systemd 定时器、恢复与升级手册已完成；实际镜像构建、域名/HTTPS、真实 API 与恢复演练未完成。

## 已验证

- M3-2：生成与修改成功后会持久化四维交付评估（可执行性、结构完整性、需求与使用体验、安全检查）；Qwen 视觉模型根据预览截图评估需求与体验，安全扫描保留命中文件与行号；项目级 API 与工作台质量面板均返回真实记录、重新检查和修复建议。
- M3-3：低分建议会先由用户确认，再创建限定该建议范围的修改任务；修改成功后的 SSE 结果会更新质量面板，并显示相对确认前评分的变化。取消、提交失败和任务失败不会遗留待比较的评分状态。
- M4-1：Vue `dist/` 与 HTML/multifile 静态交付物的发布快照、公开访问、版本绑定和失败记录已由 `tests/test_deployments.py` 覆盖；不会直接公开工作区目录。
- M4-2：发布新版本、切换历史版本、稳定地址解析和下线后访问返回 404 已由 `tests/test_deployments.py` 覆盖。
- M5：`GET /api/admin/overview` 的权限、运营分区和用户操作审计已由 `tests/test_admin.py` 覆盖；发布创建、上线、下线与公开访问由 `tests/test_deployments.py` 覆盖。管理台前端生产构建通过。
- M6-0：管理员观测接口返回健康、指标、告警和时间线已由 `tests/test_admin.py` 覆盖；前端四模块管理台生产构建通过。

- 后端：管理员观测接口测试最近通过 7 项；管理与发布定向测试最近通过 9 项。
- 前端：`npm run build` 通过（含类型检查）。
- 真实模型：`backend/smoke_agent.py`、`smoke_route_agent.py`、`smoke_modification.py` 已完成生成、路由和修改冒烟。
- 静态检查：`git diff --check` 通过。
- M6-1：Docker 参数隔离与执行分流由 `tests/test_sandbox.py` 覆盖；实际 Docker 镜像运行验收取决于部署主机已安装 Docker。
- 部署主机：OpenCloudOS 9.6（x86_64）、4G 内存/60G 磁盘/1G swap；`deploy` 密钥登录和 sudo、Docker 29.7.2、Compose v5.5.0、`hello-world`、Docker 自启动均已人工验收。

## 已知边界

- 视觉评估依赖本地无头浏览器截图与独立 Qwen 视觉模型配置；任一环节不可用时会明确返回原因，不伪造视觉评分。
- 当前 SSE 缓冲和任务队列均为进程内实现；重启后依赖会话历史回放，不支持跨进程实时恢复。
- 预览 iframe 为保障运行仍允许脚本、同源、表单和弹窗；严格 CSP/容器隔离属于 M6。
- 素材任务由独立 worker 执行，支持取消、启动恢复、候选缩略图/轮播、分页与用户选择替换；Vue 项目选择素材后会重建预览产物并使首页缩略图失效。
- 真实图片来源需分别配置 Pexels、Pixabay 或 Unsplash Key，并完成来源条款与浏览器署名验收；未配置的来源会自动跳过。
- 来源连接失败会在素材完成事件和 `asset_jobs.error` 中保留具体来源错误，不再统一伪装为“未找到素材”。

## 下一步

1. 在服务器验收 M6-2：完成域名 DNS、HTTPS、真实 API、Compose 健康检查、备份定时器与恢复演练；独立命令沙箱执行器落地前，生产保持 `mock + sandbox`，不向公开后端挂载 Docker socket。
2. M6 基础稳定后，以渐进方式评估并接入 Deep Agents：先接入上下文压缩、工作区 filesystem backend 与运行中 Todo；再将生成和修改分别迁移为受控 harness profile；Docker sandbox、审批 interrupt、长期记忆和只读 verifier 子 Agent 按验证结果分阶段启用。
3. 启动 Alpha 数据集成里程碑：先实现 OpenAPI/Swagger 导入、接口契约解析、类型安全 API Client、Mock/真实数据源切换和页面—接口—字段绑定确认；现有 demo 生成模式保持不变。
4. 在 Alpha 的契约、权限和验证机制稳定后，评估 Beta 全栈范围：以结构化规格、受控沙箱、数据库迁移、权限校验、测试证据和人工审批为前提；不承诺仅凭自然语言生成任意生产后端。

## 架构决策

- Agent 编排继续以 LangGraph 为主；不将 OpenClaw 或 DeepSeek Harness 作为平台运行时或状态真相来源。
- Deep Agents 是后续候选 harness，必须通过独立 PoC 验证事件协议、工具权限、工作区后端、质量和成本后，才可进入正式生成链路。
- Deep Agents 的接入采用适配器模式：平台仍负责身份、项目、版本、预览、发布、审批和审计；harness 仅负责受控代码任务执行。
- 生成 profile 可读写项目文件并使用受控构建和素材工具；修改 profile 仅能读写获授权文件且无 shell；verifier profile 只读并输出构建、测试和质量证据。
- LangGraph checkpoint 与持久化 worker 负责任务耐久性；不得把项目版本、发布状态或审计记录迁入 harness 内部状态。
- Alpha 采用“契约优先 + AI 辅助”的定位：自然语言描述页面与业务意图，导入的接口契约约束数据、请求和鉴权；Alpha 不是仅凭自然语言猜测任意后端接口。
- Beta 是独立的未来全栈模式：平台将继续保留当前 demo 和 Alpha 模式；Beta 的后端、数据库、鉴权和部署能力必须经受控执行、测试和审批后才可交付。

## 续接

- 后端测试：`cd backend; python -B -m pytest -q`
- 前端构建：`cd frontend; npm run build`
- 真实模型冒烟：在配置模型环境后运行 `backend/smoke_*.py`
- 修改前先阅读本文件、`AI灵码平台-详细提示词-v3.md` 与相关测试；状态冲突时以代码为准。
