# PROJECT_STATE
更新于：2026-08-15 09:40（每轮结束必须更新）

## 当前里程碑
- 里程碑：M1（骨架与核心生成回路）
- 完成度：100%（M1 全部完成：骨架 / 生成工作流 / SSE / 任务管理 / 基础预览 / 前端脚手架）

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
- [x] M1-3 前端脚手架：Vue 3 + Vite + TypeScript + Pinia + Vue Router + Element Plus + Axios
- [x] 页面：登录 / 项目列表（新建/删除）/ 生成对话（SSE 阶段条+日志+文件树）/ 预览工作台
      （桌面/平板/手机三档视口，iframe 沙箱）
- [x] 后端基础预览：/preview/{project_id}/{path}（dist 或工作区静态文件、SPA fallback、
      路径穿越防护、query token 鉴权）、/api/projects/{id}/preview/status、文件树 API
- [x] SSE 支持 query token（EventSource 无法自定义 header）
- [x] npm run build 通过；前后端 E2E 冒烟通过（Vite 代理登录→建项目→生成→预览 200）
- [x] pytest 34 例全部通过（新增预览/文件树/SSE token 6 例）
- [x] 安装 frontend-design 技能（anthropics/skills，C:\Users\13188\.codex\skills\frontend-design）
- [x] 前端 UI 重设计（按 frontend-design 方法论）：墨蓝+琥珀设计令牌、
      Space Grotesk / Inter / IBM Plex Mono 本地字体（fontsource，离线可用）
- [x] 生成对话页改为“左对话 + 右实时预览”同屏工作台，不再依赖按钮跳转预览；
      新增 LivePreviewPanel（设备框预览 + 三档视口 + 构建状态条）与 StageRail 流水线
- [x] 登录页 / 项目列表 / 全屏预览统一视觉；npm run build + 运行时冒烟通过
- [x] 按用户反馈做友好化调整：冷色控制室 → 温暖浅色工作室（奶油纸底 #F8F6F1 +
      柔和靛蓝 #5B67F1，琥珀只保留给“构建中”瞬间）
- [x] 交互友好化：全局键盘聚焦环、按钮悬停/按下/禁用态、Enter 发送（Shift+Enter 换行）、
      阶段提示 tooltip、更友善的空状态/错误文案、登录页暖色渐变与引导文案
- [x] 构建与冒烟通过
- [x] 接入真实 LLM：DeepSeek V4（deepseek-v4-flash，reasoning_effort=high，
      base_url=https://api.deepseek.com）；密钥存 backend/.env（gitignored，不提交）
- [x] LLM 适配层支持 reasoning_effort 与 thinking 模式；连通测试 200 + 真实端到端
      生成 succeeded（解析/规划/总结走 DeepSeek，构建仍为 mock 执行器）
- [x] LLM 自主写代码（ReAct Agent）：list_files/read_file/write_file/edit_file/
      run_command/finish 工具循环，输出护轨拦截危险写入，SSE 推送 thought/tool_call/
      file_written，轮次上限 10、token 用量统计、节点边界取消
- [x] generate_code 真实模式走 Agent，mock 回退保留；总结优先用 Agent finish(summary)
- [x] Agent 单元测试 3 例（写盘闭环/护轨拦截/轮次上限）+ 全量 pytest 37 passed
- [x] 真实 DeepSeek 冒烟：LLM 自主生成完整 index.html（落地页），status=succeeded
- [x] 修复预览静态资源 422：iframe 内相对资源（style.css/script.js）不带 query token；
      改为同源 Cookie（preview_token，path=/preview）鉴权，query token 保留兼容；
      pytest 38 passed + 运行时冒烟 root/css/js 均 200、无 Cookie 401
- [x] 对话流重构：移除独立“实时日志”区域；stage/think/tool_call/file_written/
      build_log/error 全部并入对话记录；思考与构建日志可点击折叠，工具调用带 SVG 图标，
      阶段以琥珀圆点+说明展示；窄屏（≤1024px）上下堆叠；npm run build + 冒烟通过
- [x] 修复生成对话页白屏：GenerationChatView 使用了 computed 但漏导入（vite build
      不做类型检查导致构建通过、运行时崩溃）；已补导入并接入 vue-tsc 类型门禁
      （npm run typecheck），构建脚本改为 typecheck && vite build
- [x] LLM 真实流式输出：DeepSeek 走 SSE stream，reasoning_content/content 逐字推送
      （reasoning_delta / assistant_delta，完整不截断）
- [x] 工具调用两段事件：tool_call_started（前端转圈“调用中…”）→ tool_call_completed
      （成功/失败标记）；写文件仍发 file_written
- [x] 前端对话流流式渲染：思考默认展开、逐字追加+光标闪烁，可点击折叠；工具条目转圈→图标；
      模型首轮后直接给正文总结时自动视为完成（不再空转到轮次耗尽）
- [x] 修复事件总线 asyncio.Lock 跨事件循环挂起（改用线程锁，短操作安全）
- [x] 真实冒烟：469 个 reasoning_delta（2005 字符思考）+ 93 个 assistant_delta +
      6 次工具 started/completed + 3 文件写入 → succeeded；pytest 38 passed
- [x] 流式渲染性能优化：增量 40ms 合批刷新（不再逐 token 重渲染/滚动），
      自动滚动只在用户接近底部时执行，避免强拉；组件卸载清理定时器
- [x] Markdown 渲染：AI 总结支持 GFM（标题/列表/引用/表格）+ 代码高亮
      （marked + marked-highlight + highlight.js + DOMPurify 消毒），代码块深色等宽
      且最大高度 340px 内部滚动
- [x] 思考内容 max-height 240px 内部滚动（overscroll contain），不再无限挤压页面
- [x] 过程事件持久化：stage/think/tool_call/file_written/build_log 落库为会话消息
      （services/chat_log.py），退出重进后对话流完整回放；流式增量在完成点持久化，
      避免碎片化；消息排序按 created_at+id
- [x] 前端历史加载按 msg_type 还原为同一套对话条目（阶段/思考/工具/文件/构建日志分组）
- [x] 真实生成验证：重新拉取消息含 text/stage/think/tool_call/file_written/
      build_log/summary 全部类型；pytest 38 passed + 前端 build 通过
- [x] 工具调用展示改版：与思考平级，连续工具调用合并为一个“工具调用”气泡
      （每行一个调用：图标/名称/路径/成功/失败/转圈）；历史回放同样合并
- [x] 规划阶段不再输出写死的“实施计划完成，共 N 步”：改为展示真实计划步骤列表；
      计划生成改为紧扣具体需求（prompt 明确禁止通用步骤，mock 也按需求特性生成）
- [x] 流式结束事件 stream_end：思考输出完后清除“思考中…”与转圈，并切换 Markdown 渲染；
      AI 正文同样在流结束后结束流式状态
- [x] 思考内容改为 Markdown 渲染（代码/列表/引用等友好展示，限高滚动保留）
- [x] 工具调用中文名：读取目录/读取文件/写入文件/修改文件/运行命令/完成
- [x] 修复工具“失败”误报：read_file 返回纯文本被成功判定当 JSON 解析导致全标失败；
      改为返回结构化 JSON，非 JSON 结果视为成功；白名单补充 npx；
      真实冒烟 6 次工具调用全部 ok=True
- [x] run_command 可用性：内置模拟 ls/cat/pwd/dir/type/echo/find/grep/where/cd
      （纯 Python，不依赖外部二进制，Windows 同样可用）；npm/npx/node/python 走真实
      子进程（.cmd 自动经 cmd.exe 包装）；工具描述明确支持范围；
      pytest 42 passed（新增沙箱 4 例）
- [x] 修复 node -e / python3 -c 失败：
      - python3 解析到 Windows 商店别名 stub（WindowsApps）→ WinError 1920，
        改为回退真实 python/py（跳过 WindowsApps）
      - 模型把整条命令作为单个字符串传入时被白名单拒绝 → 支持 shlex 拆分字符串命令
      - python 子进程强制 UTF-8 输出，输出解码 UTF-8 失败时回退 GBK，中文不乱码
      - 实测用户命令：node -e 总行数=4、python3 -c 总行数=3 均返回 0；
        pytest 44 passed（新增字符串命令/python3 回退 2 例）
- [x] 修复思考完成后仍转圈/“思考中”的竞态：stream_end 可能先于 40ms 合批刷新到达，
      旧逻辑按“最后一条”找思考条目会扑空；改为收到首个增量立即创建条目并用显式 ID
      追踪，stream_end/工具开始/完成/错误/取消统一清理
- [x] 思考完成自动收起（collapsed=true），历史回放的思考默认收起，可点击展开
- [x] 收起后可重新展开：点击后自动滚动到该条目；Markdown 渲染失败时降级纯文本兜底
- [x] 修复 run_command 展示逐字符间隔：模型以字符串传命令时先 shlex 拆分再生成
      detail（显示/执行一致）；失败时把错误信息（error/退出输出尾部）随事件与历史落库，
      前端“失败”徽标带 title 显示原因；pytest 45 passed
- [x] 思考 Markdown 展示加固：任何结束事件（stream_end/完成/错误/取消）统一扫描清除
      残留 streaming 标记，确保思考切换到 MarkdownView（含代码高亮/列表/加粗）；
      思考内容区改为“文档卡片”样式（琥珀左边线+内边距），Markdown 排版一眼可辨；
      验证 marked+marked-highlight 代码围栏输出 <pre><code class="hljs">
- [x] Agent 工具调用轮次上限 10 → 50（配置 AI_LINGMA_AGENT_MAX_ITERATIONS=50）
- [x] 受限环境子进程不可用（NotImplementedError）降级：
      - run_command 捕获 NotImplementedError 并给出明确原因
      - node --check 校验命令降级为“跳过+告警”（工具结果 exit_code=0），不再全盘失败
      - 静态构建门禁中 node 语法检查不可用时仅警告、不阻断构建
      - pytest 46 passed（新增降级单测）
- [x] 首页项目截图：后端用无头 Edge/Chrome 截取预览页并缓存 PNG
      （storage/thumbnails/{project_id}.png，index.html 变更后自动重截）；
      前端项目卡片显示真实网页截图，未生成/截图失败回退默认图块（“尚未生成”）；
      实测 API 返回 200 image/png（43KB）；pytest 50 passed（新增截图 4 例）

## 进行中 / 下一步
- [ ] 下一步：M2 预览点选修改（ElementPicker、修改工作流、版本快照/回滚、diff 面板）
- [ ] 后续：M3 护轨 LLM 复核与自评、M4 部署引擎（本轮不开始）

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
- LLM 实际配置：deepseek-v4-flash（high effort，thinking enabled），见 backend/.env
- 构建：AI_LINGMA_BUILD_MODE=mock（离线）/ real（真实 npm 构建）
- 预览：基础版直接服务 dist（优先）或工作区静态文件；按项目的 Vite dev-server
  热更新推迟到 M2/M6；iframe 使用 sandbox + 服务端代理
- SSE：EventSource 用 query token 鉴权；普通 API 仍用 Authorization header
- 前端构建暂为 vite build（未接入 vue-tsc 类型门禁，M6 打磨）
- 预览内嵌在生成对话页右侧；全屏预览页仍保留供独立查看
- 字体全部本地打包（@fontsource），不依赖外部 CDN
- Agent 轮次上限默认 10（AI_LINGMA_AGENT_MAX_ITERATIONS）；run_command 走白名单+超时
- 预览鉴权：preview_token Cookie（path=/preview，前端 JS 写入，非 HttpOnly）；
  仅限本地/内网开发，M4/M6 部署隔离时升级为 HttpOnly + 严格 CSP
- SSE 事件扩展：reasoning_delta / assistant_delta / tool_call_started /
  tool_call_completed（原有事件保留兼容）
- 前端渲染：marked/highlight.js/dompurify 本地打包；流式期间显示纯文本+光标，
  结束后切 Markdown 渲染，避免逐字重排
- 会话回放：生成过程事件落库（msg_type=stage/think/tool_call/file_written/build_log），
  与实时 SSE 同源映射，前端历史与实时渲染共用一套条目模型
- 对话条目模型：思考=think（可折叠），连续工具调用=tools 组气泡，其余 stage/file/
  build/error/info 各自成条
- 沙箱 run_command：白名单 npm/npx/node/python/python3；只读检查命令由 Python 内置
  模拟（ls/cat/pwd/dir/type/echo/find/grep/where/cd），输出有长度与条数上限
- 沙箱 run_command：接受字符串命令自动 shlex 拆分；python3 回退真实 python/py
  （跳过 WindowsApps stub）；python 子进程 PYTHONUTF8=1，输出 GBK/UTF-8 双解码
- 受限环境降级：子进程 NotImplementedError → BuildError；node --check 跳过并告警，
  npm 等构建命令在环境不支持时仍明确失败（不伪造构建成功）
- 截图：AI_LINGMA_BACKEND_URL 供无头浏览器回访预览页；截图失败/未生成返回 404，
  前端 <img> 加载失败自动显示默认占位卡片
- 管理员设置（注册开关/配额）暂为内存态，重启恢复 env 默认值；M5 做持久化
- 登录为无状态 JWT，logout 仅前端丢弃令牌；黑名单在 M5 补齐
- 项目删除先停任务（当前无任务）再清理库记录与工作区目录

## 最近构建/测试结果
- 最后命令：python -m pytest -q → 34 passed；npm run build → 通过（conda + node 18）
- 最后命令：python -m pytest -q → 37 passed（新增 Agent 3 例）
- 最后命令：python -m pytest -q → 38 passed（新增 Cookie 预览 1 例）
- 真实 LLM 连通：POST /chat/completions → 200；端到端生成 succeeded（model=deepseek-v4-flash）
- 真实 Agent 冒烟：python smoke_agent.py → succeeded，LLM 自主写 index.html
- 前后端 E2E 冒烟：Vite 代理登录→创建项目→生成 succeeded→预览 HTTP 200
- UI 冒烟：新工作台布局页面可正常服务，登录/项目列表 API 正常
- alembic upgrade head → 通过（e0806b14bcc1 + 1c4243ee8fbd；dev 库已迁移）
- 真实构建冒烟：任务看板模板生成 → npm install/build → dist/index.html 产出，succeeded
- uvicorn 冒烟：health ok、admin 登录 200（M1-1）
- 最后错误：无

## 已知问题与阻塞
- Starlette 1.6 提示 httpx TestClient 弃用（仅警告，不影响运行）
- 暂无 LLM API Key / base_url 配置；真实生成联调需在 .env 提供
- PyPI 索引对 langgraph-core 包名仍 404，但 conda 环境预装 langgraph 1.2.11 已满足
- Windows 控制台向 Python 传中文 stdin 会乱码；中文脚本请写成 .py 文件执行

## 续接指引
- 启动：cd backend && python -m uvicorn app.main:app --reload --port 8000
- 初始化：python -m app.scripts.init
- 测试：python -m pytest -q
- 端口：后端 8000、前端 5173（npm run dev）
- 管理员账号：admin / admin123（.env 可改）
- 快速体验生成：POST /api/projects/{id}/generations {"requirement":"..."}，
  然后 GET /api/generations/{id}/events 看 SSE，GET /api/generations/{id} 轮询状态
- 下一步入口：M2 —— backend/app/agents/modification/ + 前端 ElementPicker
