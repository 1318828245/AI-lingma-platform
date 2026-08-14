# AI 灵码平台（AI-Lingma-Platform）

用户用自然语言描述需求 → 自动生成可运行前端工程 → 实时预览点选修改 → 一键部署独立 URL。
详细产品与技术规格见 [AI灵码平台-详细提示词-v3.md](AI灵码平台-详细提示词-v3.md)，构建进度见 `PROJECT_STATE.md`。

## 当前进度（M1 骨架阶段）

已实现：后端骨架（FastAPI + SQLAlchemy 2.x）、全部数据模型、JWT 认证（bcrypt）、内置管理员、3 个种子模板、项目/会话/模板/管理员基础 API。

## 启动后端（开发环境）

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m app.scripts.init   # 初始化数据库/管理员/种子模板
.\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

默认管理员：`admin / admin123`（首次登录后请修改；生产环境通过 `.env` 的
`AI_LINGMA_ADMIN_USERNAME` / `AI_LINGMA_ADMIN_PASSWORD` 指定）。

配置项见 `backend/.env.example`。

## 测试

```powershell
cd backend
.\.venv\Scripts\python -m pytest -q
```

## 安全边界

- 默认 SQLite + 本地文件存储；生产切换 PostgreSQL 与 Docker 沙箱（见提示词 v3）。
- 注册默认关闭（`AI_LINGMA_REGISTER_ENABLED=false`），仅管理员登录。
- 任务执行沙箱、护轨、部署引擎等里程碑尚未实现，暂不用于生产。
