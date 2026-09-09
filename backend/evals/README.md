# Agent 回归评测

`agent_regression_cases.json` 是 Route Agent、生成和修改提示词契约的离线确定性基线。pytest
无需外部模型即可加载它，提示词修改后应运行相应测试。

真实模型验收使用 `backend/smoke_agent.py`、`backend/smoke_route_agent.py` 和
`backend/smoke_modification.py`，用于验证工具调用与文件写入。
