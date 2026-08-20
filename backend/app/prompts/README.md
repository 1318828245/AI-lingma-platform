# Prompt catalog

每个文件都是独立、可审阅的模型提示词。`app.prompts` 以 UTF-8 加载，并仅在需要时替换
命名变量 `{{placeholder}}`。提示词统一以 Markdown 标题组织角色、边界、流程、失败策略与输出契约；
修改提示词时应保持调用方所需的 JSON 或模板变量不变。

| File | Consumer | Dynamic placeholders |
| --- | --- | --- |
| `route_agent.md` | 路由 Agent：技术栈建议 | None |
| `generation_agent.md` | 生成 Agent | `tech_stack`, `parsed_requirement`, `plan` |
| `modification_agent.md` | 修改 Agent | `element_snapshot`, `related_files` |
| `generation_tasks/requirement_parser.md` | 生成工作流：需求解析 | None |
| `generation_tasks/implementation_plan.md` | 生成工作流：实施计划 | None |
| `generation_tasks/delivery_summary.md` | 生成工作流：交付总结 | None |

不要把用户输入直接拼接进提示词文件。保留为命名变量，并在调用方通过 `render_prompt` 注入。

真实模型验收脚本位于 `backend/smoke_agent.py`、`backend/smoke_route_agent.py` 和
`backend/smoke_modification.py`。
