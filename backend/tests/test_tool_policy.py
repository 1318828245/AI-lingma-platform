from app.agents.tooling.contracts import ToolCall
from app.agents.tooling.definitions import GENERATION_TOOL_NAMES, MODIFICATION_TOOL_NAMES, tool_schemas
from app.agents.tooling.policy import validate_tool_call


def test_tool_schemas_are_shared_and_agent_specific():
    generation_names = {schema["function"]["name"] for schema in tool_schemas(GENERATION_TOOL_NAMES)}
    modification_names = {schema["function"]["name"] for schema in tool_schemas(MODIFICATION_TOOL_NAMES)}

    assert "run_command" in generation_names
    assert "run_command" not in modification_names
    assert "collect_assets" in generation_names & modification_names
    assert "edit_file" in generation_names & modification_names


def test_tool_policy_rejects_wrong_agent_and_sensitive_path():
    assert validate_tool_call("modification", ToolCall("call_1", "run_command", {"command": ["npm", "run", "build"]}))
    assert validate_tool_call("generation", ToolCall("call_2", "read_file", {"path": "../.env"}))
    assert validate_tool_call("modification", ToolCall("call_3", "edit_file", {"path": "dist/assets/app.js", "old": "a", "new": "b"}))
    assert validate_tool_call("generation", ToolCall("call_3", "read_file", {"path": "index.html"})) is None
