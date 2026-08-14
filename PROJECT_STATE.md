# PROJECT_STATE
更新于：2026-08-14 21:40（每轮结束必须更新）

## 当前里程碑
- 里程碑：M1（骨架与核心生成回路）
- 完成度：35%（本轮完成 M1 第 1 步：后端骨架 + 认证 + 项目/会话/模板/管理员 API）

## 已完成（含验证方式）
- [x] 后端骨架可启动（uvicorn 冒烟：/api/health 返回 ok；admin 登录成功）
- [x] 全部 14 张数据表模型（users/projects/sessions/generations/modifications/
      files/file_versions/project_versions/messages/deployments/templates/
      evaluations/guardrail_events/metrics/daily_stats）
- [x] Alembic 脚手架 + 初始迁移（对全新 SQLite 库 autogenerate 并 upgrade head 通过）
- [x] JWT + bcrypt 认证：登录/登出/刷新/me；注册受开关控制（默认关闭）
- [x] 内置管理员初始化脚本（python -m app.scripts.init，幂等）
- [x] 3 个种子模板（个人名片页/任务看板/管理后台模板），新建项目自动落盘到工作区
- [x] 项目 CRUD（owner 隔离、slug 唯一、级联删除工作区）、会话列表/消息、模板列表
- [x] 管理员 API：系统设置（内存态）、用户列表/修改/重置密码；不可自降级
- [x] pytest 21 例全部通过（认证 7 + 项目 5 + 会话 2 + 管理员 5 + 健康 1 + 模板 1）

## 进行中 / 下一步
- [ ] 下一步：M1-2 生成工作流（LangGraph/状态机：解析→规划→生成→构建→基础修复）
      + SSE 进度流 + 任务状态/取消 + 生成消息入库
- [ ] 后续：M1-3 基础实时预览（iframe + Vite 代理）与前端 Vue3 脚手架
- [ ] 后续：M2 点选修改、M3 护轨与自评、M4 部署引擎（本轮不开始）

## 关键决策与默认值
- 数据库：SQLite（storage/app.db），生产切 PostgreSQL；开发用 create_all，
  Alembic 迁移已就绪并验证
- 本机 Python 3.10.19（文档要求 3.11+），代码按 3.10 兼容编写；Node 18.20.8
- 沙箱：本地开发暂用受限子进程（未实现 Docker 沙箱），README 已标注
- LLM：本轮未接入；M1-2 先实现 mock 执行器，`langchain-openai` 适配随后接
- 管理员设置（注册开关/配额）暂为内存态，重启恢复 env 默认值；M5 做持久化
- 登录为无状态 JWT，logout 仅前端丢弃令牌；黑名单在 M5 补齐
- 项目删除先停任务（当前无任务）再清理库记录与工作区目录

## 最近构建/测试结果
- 最后命令：pytest -q → 21 passed（backend/.venv）
- alembic upgrade head → 通过（初始迁移 e0806b14bcc1）
- uvicorn 冒烟：health ok、admin 登录 200
- 最后错误：无

## 已知问题与阻塞
- Starlette 1.6 提示 httpx TestClient 弃用（仅警告，不影响运行）
- 暂无 LLM API Key / base_url 配置；真实生成联调需在 .env 提供
- Windows 下沙箱环境写文件需提权（开发机限制，不影响运行时）

## 续接指引
- 启动：cd backend && .\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
- 初始化：.\.venv\Scripts\python -m app.scripts.init
- 测试：.\.venv\Scripts\python -m pytest -q
- 端口：后端 8000（前端 5173 尚未搭建）
- 管理员账号：admin / admin123（.env 可改）
- 下一步入口：backend/app/agents/generation（尚未创建），先建工作流状态与节点
