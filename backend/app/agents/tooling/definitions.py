"""Single source of model-visible tool schemas."""

from copy import deepcopy


_TOOLS = {
    "list_files": {"description": "List files in the project workspace", "properties": {}, "required": []},
    "read_file": {"description": "Read a project file", "properties": {"path": {"type": "string"}}, "required": ["path"]},
    "write_file": {"description": "Write a complete project file", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]},
    "edit_file": {"description": "Replace one exact text fragment in a project file", "properties": {"path": {"type": "string"}, "old": {"type": "string"}, "new": {"type": "string"}}, "required": ["path", "old", "new"]},
    "run_command": {"description": "Run an allowed project validation command", "properties": {"command": {"oneOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}, "minItems": 1}]}}, "required": ["command"]},
    "collect_assets": {"description": "Collect a licensed icon or photo from approved sources and add the selected asset to the project manifest", "properties": {"kind": {"type": "string", "enum": ["icon", "photo", "illustration"]}, "query": {"type": "string"}, "usage_role": {"type": "string"}, "orientation": {"type": "string", "enum": ["landscape", "portrait", "square"]}}, "required": ["kind", "query"]},
    "finish": {"description": "Finish the task with a concise summary", "properties": {"summary": {"type": "string"}}, "required": ["summary"]},
}


def tool_schemas(names: set[str]) -> list[dict]:
    schemas = []
    for name in sorted(names):
        item = _TOOLS[name]
        schemas.append({"type": "function", "function": {"name": name, "description": item["description"], "parameters": {"type": "object", "properties": deepcopy(item["properties"]), "required": item["required"], "additionalProperties": False}}})
    return schemas


GENERATION_TOOL_NAMES = {"list_files", "read_file", "write_file", "edit_file", "run_command", "collect_assets", "finish"}
MODIFICATION_TOOL_NAMES = {"list_files", "read_file", "write_file", "edit_file", "collect_assets", "finish"}
