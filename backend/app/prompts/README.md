# Agent 提示词目录

每个文件都是运行时加载的独立提示词。`app.prompts` 以 UTF-8 加载，并只替换命名变量
`{{placeholder}}`；修改时必须保持调用方的变量和输出契约不变。

| File | Consumer | Dynamic placeholders |
| --- | --- | --- |
| `route_agent.md` | 路由 Agent：技术栈建议 | None |
| `generation_agent.md` | 生成 Agent | `tech_stack`, `parsed_requirement`, `plan` |
| `modification_agent.md` | 修改 Agent | `element_snapshot`, `related_files` |
| `generation_tasks/requirement_parser.md` | 生成工作流：需求解析 | None |
| `generation_tasks/implementation_plan.md` | 生成工作流：实施计划 | None |
| `generation_tasks/delivery_summary.md` | 生成工作流：交付总结 | None |

不要把用户输入直接拼入提示词文件，应通过 `render_prompt` 注入。真实模型验收脚本位于
`backend/smoke_agent.py`、`backend/smoke_route_agent.py` 与 `backend/smoke_modification.py`。
