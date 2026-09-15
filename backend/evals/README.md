# Agent 回归评测

`agent_regression_cases.json` 是 Route Agent、生成和修改提示词契约的离线确定性基线；
`agent_review_cases.json` 覆盖输入评审的攻击、混淆攻击和正常需求。pytest 无需外部模型即可运行。

真实模型验收使用 `backend/smoke_agent.py`、`backend/smoke_route_agent.py` 和
`backend/smoke_modification.py`，用于验证工具调用与文件写入。

评测指标、样本准入和提示词优化流程见 [Agent 评测与护轨方案](../../docs/Agent评测与护轨方案.md)。
