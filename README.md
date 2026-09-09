# AI 灵码平台

AI 灵码平台用于生成、预览、修改和发布 HTML 或 Vue 3 前端项目。用户以自然语言描述需求，在同屏工作台中查看生成过程与实时预览；生成后可点选元素修改、比较版本并发布静态站点。

## 当前能力

- HTML 多文件与 Vue 3/Vite 项目生成；创建时会给出技术栈建议。
- SSE 推送生成阶段、模型输出、工具调用、文件写入与构建日志，支持断线补发。
- 聊天或点选修改；修改前后保存快照、diff，校验失败自动回滚。
- 异步素材收集、质量评估、版本快照、静态发布和管理员运营台。
- 生成 Agent 可使用受控文件与构建工具；修改 Agent 无命令执行权限。

Alpha（OpenAPI/Swagger 契约驱动的数据前端）和 Beta（受控全栈交付）目前仅有介绍入口，不属于已交付功能。

## 架构

```text
Vue 3 + Vite + TypeScript
        │ REST / SSE
FastAPI ─┬─ LangGraph 生成编排
         ├─ 模型 Provider 与工具策略层
         ├─ 预览、版本、发布、素材、评估与管理 API
         └─ SQLite（开发）/ PostgreSQL（生产）+ 文件存储
```

生成工作流：`输入护轨 → 需求解析 → 实施计划 → 代码生成 → 输出护轨 → 构建/修复 → 总结`。

项目文件位于 `storage/workspaces/{multifile|vue}/{slug}/`；Vue 预览和发布均使用构建产物 `dist/`。

## 本地开发

后端：

```powershell
cd backend
python -m pip install -r requirements.txt
python -m app.scripts.init
python -m uvicorn app.main:app --reload --port 8000
```

前端：

```powershell
cd frontend
npm install
npm run dev
```

打开 `http://127.0.0.1:5173`。初始化后的默认管理员为 `admin / admin123`，仅限本地开发。

## 构建模式与 Vue 预览

`AI_LINGMA_BUILD_MODE=real` 会真实执行构建；这是 Vue 项目可预览的必要条件。平台会对 Vite 构建追加 `--base=./`，使 `dist/index.html` 引用 `./assets/...`，而不是 `/assets/...`。

`mock` 仅做离线结构检查，不生成新的 Vite `dist`，仅适合离线测试。若 Vue 预览白屏，先检查 `dist/index.html`：出现 `src="/assets/..."` 说明产物需要用真实构建重新生成。详见 [部署手册](docs/部署手册.md#vue-预览白屏)。

## 验证

```powershell
cd backend
python -m pytest -q

cd ..\frontend
npm run build
```

Agent 离线回归样例位于 `backend/evals/`；真实模型冒烟脚本位于 `backend/smoke_*.py`。

## 文档

- [当前状态与边界](PROJECT_STATE.md)
- [架构与功能说明](AI灵码平台-详细提示词-v3.md)
- [生产部署手册](docs/部署手册.md)
- [生产常用命令](docs/部署命令.md)
- [Agent 提示词目录](backend/app/prompts/README.md)

生产环境配置存放于 `.env.production`，不得提交、复制到聊天或写入日志。
