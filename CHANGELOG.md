# 变更记录

## 2026-08-19：生成工作区与实时预览体验

- 将生成项目工作区按技术栈隔离为 `storage/workspaces/vue/<slug>` 和 `storage/workspaces/multifile/<slug>`，并禁止使用纯数字项目名称。
- Vite 构建使用相对资源路径，平台通过 `/preview/<project_id>/` 托管 `dist` 预览，修复资源路径错误造成的白屏。
- 约束生成 Agent 不启动本地开发服务器：仅允许安装依赖和构建；拒绝 Linux 专用的超时、休眠、临时目录、重定向和后台命令。
- 生成过程使用 SSE 展示阶段、思考、工具、文件和构建日志；等待提示改为不遮挡聊天内容的轻量进度条，结束后自动隐藏。
- 预览区域区分生成中、未生成、失败和可预览状态，并修复预览 iframe 已就绪时空态仍覆盖页面的问题。

## 验证

- `backend`: `python -B -m pytest -q`，67 passed。
- `frontend`: `npm run build`，通过类型检查与 Vite 构建。
