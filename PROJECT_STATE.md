# PROJECT_STATE
更新于：2026-08-14 22:40（每轮结束必须更新）

## 当前里程碑
- 里程碑：M1（骨架与核心生成回路）
- 完成度：65%（M1-1 后端骨架 + M1-2 生成工作流已完成；剩余 M1-3 前端与基础预览）

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
- [x] M1-2 生成工作流：解析→规划→生成→输出护轨→构建→修复→总结（状态机等价 LangGraph，
      节点/状态字段与提示词 6.1 对齐，可平替）
- [x] SSE 事件流：stage/thought/tool_call/file_written/build_log/completed/error/cancelled
- [x] 任务模型：pending→running→succeeded/failed/cancelled/timed_out/interrupted；
      并发上限 2、FIFO 队列、单任务超时、节点边界取消、启动时遗留任务恢复
- [x] 输入/输出护轨（规则版）：注入/危险命令拦截并写入 guardrail_events（LLM 复核 M3）
- [x] LLM 适配层：默认 mock 执行器离线可跑；配置 base_url/api_key 走 OpenAI 兼容协议
- [x] 构建：mock 模式（测试）+ 真实模式（npm install --ignore-scripts / npm run build、
      静态 JS 走 node --check）
- [x] 生成 API：创建/查询/取消/追加消息/SSE/评估占位
- [x] pytest 28 例全部通过；真实 npm 构建冒烟通过（dist/index.html 产出）
- [x] 生成工作流迁移到 LangGraph StateGraph（conda 环境预装 langgraph 1.2.11）；
      节点/条件边与文档 6.1 完全一致，pytest 28 例复测通过
- [x] 运行环境切换为 conda env01-p10-drawimg（用户指定），依赖已装齐且 pip check 无冲突

## 进行中 / 下一步
- [ ] 下一步：M1-3 基础实时预览（iframe + Vite 代理）与前端 Vue3 脚手架
- [ ] 后续：M2 点选修改、M3 护轨与自评、M4 部署引擎（本轮不开始）

## 关键决策与默认值
- 数据库：SQLite（storage/app.db），生产切 PostgreSQL；开发用 create_all，
  Alembic 迁移已就绪并验证
- 本机 Python 3.10.19（文档要求 3.11+），代码按 3.10 兼容编写；Node 18.20.8
- 沙箱：本地开发为受限子进程（白名单命令 + 超时 + 工作区约束），Docker 沙箱 M6 补齐
- 运行环境：conda env01-p10-drawimg（Python 3.10；langgraph 1.2.11 / langchain-core 1.5.4 /
  langchain-openai 1.5.0）；backend/.venv 已停用但未删除（gitignored，可自行清理）
- LangGraph：conda 环境预装 langgraph 1.2.x，生成工作流已用 StateGraph 实现；
  PyPI 索引对 langgraph-core 包仍 404，但不影响（langgraph 包已满足需求）
- LLM：默认 mock；配置 AI_LINGMA_LLM_BASE_URL/API_KEY/MODEL 后走 OpenAI 兼容协议
- 构建：AI_LINGMA_BUILD_MODE=mock（离线）/ real（真实 npm 构建）
- 管理员设置（注册开关/配额）暂为内存态，重启恢复 env 默认值；M5 做持久化
- 登录为无状态 JWT，logout 仅前端丢弃令牌；黑名单在 M5 补齐
- 项目删除先停任务（当前无任务）再清理库记录与工作区目录

## 最近构建/测试结果
- 最后命令：python -m pytest -q → 28 passed（conda env01-p10-drawimg）
- alembic upgrade head → 通过（e0806b14bcc1 + 1c4243ee8fbd；dev 库已迁移）
- 真实构建冒烟：任务看板模板生成 → npm install/build → dist/index.html 产出，succeeded
- uvicorn 冒烟：health ok、admin 登录 200（M1-1）
- 最后错误：无

## 已知问题与阻塞
- Starlette 1.6 提示 httpx TestClient 弃用（仅警告，不影响运行）
- 暂无 LLM API Key / base_url 配置；真实生成联调需在 .env 提供
- LangGraph/LangChain 依赖因网络受限未安装（见关键决策）
- Windows 控制台向 Python 传中文 stdin 会乱码；中文脚本请写成 .py 文件执行

## 续接指引
- 启动：cd backend && python -m uvicorn app.main:app --reload --port 8000
- 初始化：python -m app.scripts.init
- 测试：python -m pytest -q
- 端口：后端 8000（前端 5173 尚未搭建）
- 管理员账号：admin / admin123（.env 可改）
- 快速体验生成：POST /api/projects/{id}/generations {"requirement":"..."}，
  然后 GET /api/generations/{id}/events 看 SSE，GET /api/generations/{id} 轮询状态
- 下一步入口：frontend/（尚未创建）+ backend/app/api/preview.py（M1-3）
