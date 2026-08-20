# Agent regression evaluation

`agent_regression_cases.json` is the offline, deterministic baseline for the
Route Agent and the generation/modification prompt contracts. The pytest suite
loads this file without an external model connection, so prompt edits can be
checked on every change.

Real-model acceptance remains in `backend/smoke_agent.py`,
`backend/smoke_route_agent.py`, and `backend/smoke_modification.py` because it
validates tool calls and file writes rather than only text classification.
