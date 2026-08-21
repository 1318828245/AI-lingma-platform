# 项目生命周期流程图

```mermaid
flowchart TD
    A[用户登录<br/>JWT 鉴权] --> B[创建项目<br/>名称 + 模板 + 初始技术栈]
    B --> C[创建会话与项目工作区<br/>按 HTML / Vue 分流]
    C --> D[提交自然语言需求]

    D --> E{项目已有可预览输出<br/>且不是明确新建/重建？}
    E -- 是 --> M[创建修改任务]
    E -- 否 --> F[路由 Agent 判断技术栈]

    F --> G{建议技术栈<br/>与初始选择一致？}
    G -- 否 --> H[用户确认<br/>切换或保留技术栈]
    G -- 是 --> I[创建生成任务]
    H --> I

    I --> J[生成 LangGraph<br/>护轨 → 需求解析 → 实施计划]
    J --> K[生成 Agent ReAct 工具循环<br/>读写源码 / 构建 / 结束总结]
    K --> L{需要图标、照片或插画？}
    L -- 是 --> LA[创建后台 asset_job<br/>立即继续代码生成]
    LA --> LQ[独立素材 worker<br/>可取消、重试与启动恢复]
    LQ --> LB[collect_assets 受控素材收集]
    LA --> LB[图标：Iconify / Lucide<br/>下载、SVG 安全校验、写入 assets/]
    LA --> LC[照片：Pexels → Pixabay → Unsplash<br/>自动降级、保留外链和署名]
    LA --> LD[插画/矢量：Pixabay<br/>保留外链和署名]
    LB --> N[写入 assets/manifest.json<br/>持久化候选与选用素材]
    LC --> N
    LD --> N
    L -- 否 --> O[输出护轨]
    N --> NP{源码有唯一素材占位符？}
    NP -- 是 --> NQ[受控回填素材 URL<br/>刷新预览]
    NP -- 否 --> O
    NQ --> O
    O --> P[构建与校验]
    P --> Q{构建成功？}
    Q -- 否，仍可修复 --> K
    Q -- 否，无法修复 --> R[任务失败<br/>保留错误与事件]
    Q -- 是 --> S[创建项目版本快照]
    S --> T[完成生成任务<br/>实时预览可用]

    M --> MA[定位选中元素/候选源码]
    MA --> MB[创建修改前快照]
    MB --> MC[修改 Agent 工具循环<br/>仅能编辑源码，不能执行命令]
    MC --> MD{修改需要视觉素材？}
    MD -- 是 --> LA
    MD -- 否 --> ME[源码与交互校验]
    N --> ME
    ME --> MF{Vue 项目？}
    MF -- 是 --> MG[重新构建预览]
    MF -- 否 --> MH[生成 diff]
    MG --> MH
    MH --> MI{校验通过？}
    MI -- 否 --> MJ[自动回滚到修改前快照]
    MJ --> R
    MI -- 是 --> MK[创建修改后版本快照]
    MK --> ML[完成卡片：接受或撤销]
    ML -- 接受 --> T
    ML -- 撤销 --> MN[回滚到修改前版本]
    MN --> T

    T --> U[项目工作台]
    U --> V[左侧：聊天、阶段、工具与素材事件]
    U --> W[右侧：预览、视口切换、元素点选]
    W --> D

    I -. SSE 事件与历史回放 .-> V
    M -. SSE 事件与历史回放 .-> V
    T -. 版本、资产与预览 API .-> U
```

## M3 quality loop

After a successful generation or modification, the platform commits the delivery, then runs an auditable four-dimension evaluation: executability, project structure, user intent and experience, and safety. The intent dimension uses a separate Qwen vision provider with a preview screenshot; source safety findings retain file and line evidence. The project workbench exposes the latest 20-point score, re-check action, and repair recommendations. For a low score, a recommendation becomes a controlled modification task only after the user confirms it; when that task finishes, the workbench automatically shows the fresh evaluation and the score change from the version the user approved.

## M4-1 deployment loop

The user opens the publishing center from the project workbench and publishes the latest successful version snapshot. The server copies a Vue/Vite snapshot's `dist/` delivery, or an HTML/multifile snapshot's static root delivery, into an isolated `storage/publish/{deployment-slug}/` directory, then exposes it at an absolute public URL. Every attempt is recorded with its version number, status, URL, and a readable failure reason; the editable workspace never becomes public.

## M4-2 online version management

Each project has a stable `/sites/{project-slug}/` address which resolves only to its active deployment. Publishing a new delivery makes it active; a successful historical deployment can be selected to restore that version without rebuilding. Taking the active deployment offline removes both its immutable published URL and the stable project address from public access, while retaining its record for a later restore.

## M5-1 operations overview

Administrators can open a dedicated operations dashboard from the project home. It aggregates counts for projects, users, active tasks, and online sites, then separates the underlying records into project, user, task, and deployment views. Both the route and the aggregation API require an administrator role; ordinary users remain in their own project workspace.

## M5-2 operational controls and audit trail

The operations dashboard keeps long lists readable with per-view search and pagination. Administrators can set a user's generation quota, enable or disable other accounts, and requeue a failed asset-collection job through the existing asynchronous task manager. Each successful administrator operation is written to an append-only audit record. Deployment creation, activation, and offlining are recorded in the same trail, so the platform can explain who changed an online delivery and when.

## M6-0 observability

The administration console is organised into four primary workspaces: a platform dashboard, project management, user management, and operation management. The dashboard reports API/database/queue/provider health, queue depth, success rate, actionable alerts, and only the newest twelve events. Project management separates projects, asset and task records, deployment versions, and a per-project observability view. The latter limits the selected project's execution chain to its newest twenty events, preventing an unbounded global timeline while retaining diagnosable evidence.

## 关键规则

- 生成任务和修改任务都可使用受控素材收集；图片来源失败时会降级，不阻断项目交付。
- 修改仅允许改源码；构建、源码或交互校验失败会自动恢复修改前快照。
- 每次成功生成或修改都会创建版本快照；项目可查看版本、差异并回滚。
- SSE 支持事件递增 ID 与 `Last-Event-ID` 补发；重新进入运行中的项目可恢复任务订阅与会话历史。
