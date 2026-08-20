# PROJECT_STATE

更新：2026-08-20（以当前代码和自动化验证为准）

## 当前里程碑

- 当前：M3 异步素材编排、质量与安全闭环；M3-1 第一版异步素材编排已完成，下一项为 M3-2 持久化评估结果。
- M1 生成核心回路：完成。
- M2 可控修改回路：完成。
- M4 部署、M5 运营后台、M6 生产化：未开始。

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
- [x] 异步素材编排：生成和修改 Agent 均可调用 `collect_assets`；`asset_jobs`/`project_assets` 持久化候选与选用素材，并关联生成或修改任务，SSE/历史展示检索和降级结果。
- [x] 素材来源策略：Iconify/Lucide 图标经固定来源下载、大小/MIME/主动 SVG 校验后写入 `assets/icons/`；照片按 Pexels、Pixabay、Unsplash 自动降级检索，插画/矢量由 Pixabay 提供，均仅保留来源外链与署名，需分别配置 API Key。
- [x] `assets/manifest.json` 纳入项目版本快照，项目资产可通过 `GET /api/projects/{id}/assets` 查询，删除项目时清理记录和文件。

## 已验证

- 后端：`python -B -m pytest -q` 最近通过 84 项。
- 前端：`npm run build` 通过（含类型检查）。
- 真实模型：`backend/smoke_agent.py`、`smoke_route_agent.py`、`smoke_modification.py` 已完成生成、路由和修改冒烟。
- 静态检查：`git diff --check` 通过。

## 已知边界

- evaluation API 仍返回占位结果；`evaluations`、部署、指标等 ORM 表预留不代表功能已实现。
- 当前 SSE 缓冲和任务队列均为进程内实现；重启后依赖会话历史回放，不支持跨进程实时恢复。
- 预览 iframe 为保障运行仍允许脚本、同源、表单和弹窗；严格 CSP/容器隔离属于 M6。
- 浏览器人工验收尚需执行，清单见 `docs/BROWSER_ACCEPTANCE.md`。
- 素材任务当前随生成 Agent 的工具调用完成；独立 worker、取消、跨进程恢复、用户选择/替换 UI、图片转码和缩略图尚未实现。
- 真实图片来源需分别配置 Pexels、Pixabay 或 Unsplash Key，并完成来源条款与浏览器署名验收；未配置的来源会自动跳过。
- 来源连接失败会在素材完成事件和 `asset_jobs.error` 中保留具体来源错误，不再统一伪装为“未找到素材”。

## 下一步

实施 M3-2：生成/修改结束时计算并持久化统一评估结果，evaluation API 返回真实记录，项目页展示评估摘要和修复建议，并为成功/失败路径补齐回归测试与浏览器验收。素材部分随后补独立 worker、取消/恢复、来源展示和替换 UI。

## 续接

- 后端测试：`cd backend; python -B -m pytest -q`
- 前端构建：`cd frontend; npm run build`
- 真实模型冒烟：在配置模型环境后运行 `backend/smoke_*.py`
- 修改前先阅读本文件、`AI灵码平台-详细提示词-v3.md` 与相关测试；状态冲突时以代码为准。
