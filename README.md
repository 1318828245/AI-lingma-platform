# AI 灵码平台

AI 灵码平台用于生成、预览、修改和发布 HTML 或 Vue 3/Vite 前端项目。用户用自然语言描述需求，在同一工作台跟踪生成过程、预览结果并迭代修改。

## 已具备能力

- HTML 多文件和 Vue 3/Vite 项目生成，含技术栈建议。
- 需求解析、实施计划、代码生成、构建/修复与交付总结；计划和任务进度可通过 SSE 实时恢复。
- 点选或聊天修改、快照/diff、校验失败回滚。
- 素材收集、交付评估、版本快照、静态发布与运营管理。
- 受控工具策略：生成 Agent 可执行受限构建工具，修改 Agent 不具备命令执行权限。

Alpha（OpenAPI/Swagger 契约驱动的数据前端）和 Beta（受控全栈交付）尚未实施。完整状态见 [PROJECT_STATE.md](PROJECT_STATE.md)。

## 架构

```text
Vue 3 + Vite + TypeScript
        │ REST / SSE
FastAPI ─┬─ LangGraph 工作流与 Agent 工具策略
         ├─ 预览、版本、发布、素材、评估与管理 API
         └─ SQLite（开发）/ PostgreSQL（生产）+ 文件存储
```

## 本地开发

```powershell
cd backend
python -m pip install -r requirements.txt
python -m app.scripts.init
python -m uvicorn app.main:app --reload --port 8000
```

```powershell
cd frontend
npm install
npm run dev
```

打开 `http://127.0.0.1:5173`。默认管理员 `admin / admin123` 仅用于本地开发。

## 验证

```powershell
cd backend
python -m pytest -q

cd ..\frontend
npm run build
```

Vue 项目的预览和发布必须使用 `AI_LINGMA_BUILD_MODE=real` 生成的 `dist/`；部署、排障和备份操作见 [部署手册](docs/部署手册.md)。

## 文档

- [当前状态与边界](PROJECT_STATE.md)
- [生产部署手册](docs/部署手册.md)
- [生产常用命令](docs/部署命令.md)
- [架构与运行边界](AI灵码平台-详细提示词-v3.md)
- [Agent 评测与护轨方案](docs/Agent评测与护轨方案.md)
- [Agent 提示词目录](backend/app/prompts/README.md)

生产配置保存在 `.env.production`，不得提交或输出到日志、聊天和截图中。
