# AI 灵码平台：架构与功能说明

本文是产品、架构与运行边界的简明说明。当前执行状态以 [PROJECT_STATE.md](PROJECT_STATE.md) 为准；实际 Agent 提示词位于 `backend/app/prompts/`。

## 产品边界

平台交付 HTML 多文件页面或 Vue 3/Vite 前端工程，支持生成、实时预览、局部修改、版本管理与静态发布。

- Alpha：计划支持 OpenAPI/Swagger 契约导入与真实数据绑定；尚未实现。
- Beta：计划在结构化规格、隔离执行、测试证据和审批下交付全栈应用；尚未实现。

## 组件与数据流

```text
浏览器工作台
  └─ REST + SSE ── FastAPI
       ├─ 项目、会话、生成、修改、预览、版本、发布与管理 API
       ├─ LangGraph 生成工作流
       ├─ 模型 Provider / 工具 schema / 权限策略 / 执行器
       ├─ 素材、质量评估、截图和任务服务
       └─ SQLite 或 PostgreSQL + workspace 文件存储
```

前端为 Vue 3、Vite、TypeScript、Pinia 与 Vue Router。模型层使用供应商无关的请求、响应和工具调用契约；当前可使用 OpenAI 兼容接口或离线 mock。

## 生成与修改

生成顺序：

```text
input_guardrail → parse_requirements → create_plan → generate_code
→ output_guardrail → validate_build → summarize
```

构建失败时可在受限次数内返回代码生成修复。生成任务可执行受策略限制的文件与构建工具；修改任务只能编辑获授权源码，不能改写 `dist`、`build`、依赖目录或运行命令。

工作台显示阶段、实施计划、流式文本、工具调用、文件写入、构建日志和最终结果。计划与任务状态会持久化；任务事件支持游标补发，重新进入项目可恢复会话与未完成任务。

## 预览、版本与发布

- HTML 项目从工作区静态文件预览；Vue 项目从 `dist/` 预览。
- Vue/Vite 必须真实构建，平台以 `--base=./` 生成相对资源路径；`mock` 模式只做结构检查，不能验证 Vue 预览。
- 点选元素和聊天指令都会进入同一修改任务。修改前后保存快照，构建或交互检查失败会恢复修改前快照。
- 成功版本可发布为独立 slug 地址；稳定地址只指向当前激活版本，可恢复历史版本或下线。

## 素材与质量

素材任务由独立 worker 异步执行。模型只能请求受控类型、语义查询与用途，不能自行访问任意 URL 或密钥。

- 图标仅使用经过 SVG 校验的 Iconify/Lucide 来源。
- 图片按 Pexels、Pixabay、Unsplash 等已配置来源检索，保留来源与署名；无可用候选时降级，不阻塞交付。
- 生成或修改成功后可记录可执行性、结构完整性、需求与体验、安全检查四维评估；低分改进必须经用户确认。

## 安全与运行边界

- API 按项目 owner 隔离，工具调用执行路径、参数、写入量和敏感路径均受策略校验。
- 开发环境的 `shell` 命令模式等同本机权限，不可用于生产声明。
- 生产环境使用内网 Compose、受控存储目录和外层 HTTPS Nginx；不得暴露 Docker socket 或提交密钥。
- Docker 命令沙箱可限制网络、capabilities、PID、CPU、内存和文件系统。跨进程任务队列不属于当前实现范围。

## 目录

```text
backend/app/agents/     # 生成、修改、工具策略
backend/app/api/        # FastAPI 路由
backend/app/prompts/    # 实际运行的 Markdown 提示词
backend/app/services/   # 模型、任务、预览、版本、发布等服务
backend/evals/          # Agent 离线回归样例
frontend/src/           # Vue 工作台
storage/workspaces/     # 项目源码与 Vue dist
storage/versions/       # 版本快照
storage/publish/        # 公开静态产物
docs/                   # 部署文档
```
