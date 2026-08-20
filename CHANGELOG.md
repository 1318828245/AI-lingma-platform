# 变更记录

## 2026-08-20：统一 ASCII 存储命名

- 新项目工作区标识改为 `yyyy-mm-dd-hh-mm-ss-random`，与项目显示名完全解耦。
- 缩略图和版本快照改用同一工作区标识；版本快照子目录也不再使用 `v1` 或项目数字 ID。
- 服务启动时迁移旧的中文或数字工作区目录到规范路径，并兼容清理旧缩略图和版本目录。

## 2026-08-20：模型与 Agent 工具调用分层

- 新增 Provider 无关的模型请求、响应和工具调用契约；OpenAI 兼容 HTTP/SSE 协议解析移入独立 Provider。
- 新增统一 Agent 工具 schema、`ToolCall`/`ToolResult`、策略校验和执行器；生成与修改 Agent 共用该调用链。
- 修改 Agent 明确禁止命令执行；敏感路径、越权工具、无效参数与过大写入会在执行前拦截。
- 验证：`python -B -m pytest -q` 通过（70 passed）。

## 2026-08-19：生成工作区与实时预览体验

- 将生成项目工作区按技术栈隔离为 `storage/workspaces/vue/<slug>` 和 `storage/workspaces/multifile/<slug>`，并禁止使用纯数字项目名称。
- Vite 构建使用相对资源路径，平台通过 `/preview/<project_id>/` 托管 `dist` 预览，修复资源路径错误造成的白屏。
- 约束生成 Agent 不启动本地开发服务器：仅允许安装依赖和构建；拒绝 Linux 专用的超时、休眠、临时目录、重定向和后台命令。
- 生成过程使用 SSE 展示阶段、思考、工具、文件和构建日志；等待提示改为不遮挡聊天内容的轻量进度条，结束后自动隐藏。
- 预览区域区分生成中、未生成、失败和可预览状态，并修复预览 iframe 已就绪时空态仍覆盖页面的问题。

## 验证

- `backend`: `python -B -m pytest -q`，67 passed。
- `frontend`: `npm run build`，通过类型检查与 Vite 构建。
