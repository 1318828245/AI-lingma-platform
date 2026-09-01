"""Single source of model-visible tool schemas."""

from copy import deepcopy


_TOOLS = {
    "list_files": {"description": "List files in the project workspace", "properties": {}, "required": []},
    "read_file": {"description": "Read a project file", "properties": {"path": {"type": "string"}}, "required": ["path"]},
    "read_files": {"description": "Read several related project files in one call", "properties": {"paths": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 12}}, "required": ["paths"]},
    "search_codebase": {"description": "Find relevant source lines across the project", "properties": {"query": {"type": "string"}, "max_results": {"type": "integer", "minimum": 1, "maximum": 80}}, "required": ["query"]},
    "write_file": {"description": "Write a complete project file", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]},
    "write_files": {"description": "Atomically write several complete related project files", "properties": {"files": {"type": "array", "items": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}, "minItems": 1, "maxItems": 12}}, "required": ["files"]},
    "edit_file": {"description": "Replace one exact text fragment in a project file", "properties": {"path": {"type": "string"}, "old": {"type": "string"}, "new": {"type": "string"}}, "required": ["path", "old", "new"]},
    "run_command": {"description": "Run an allowed project validation command", "properties": {"command": {"oneOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}, "minItems": 1}]}}, "required": ["command"]},
    "collect_assets": {"description": "Queue a licensed asset collection job from approved sources", "properties": {"kind": {"type": "string", "enum": ["icon", "photo", "illustration"]}, "query": {"type": "string"}, "usage_role": {"type": "string"}, "orientation": {"type": "string", "enum": ["landscape", "portrait", "square"]}, "target_path": {"type": "string"}, "placeholder": {"type": "string"}}, "required": ["kind", "query"]},
    "finish": {"description": "Finish the task with a concise summary", "properties": {"summary": {"type": "string"}}, "required": ["summary"]},
}


def tool_schemas(names: set[str]) -> list[dict]:
    schemas = []
    for name in sorted(names):
        item = _TOOLS[name]
        schemas.append({"type": "function", "function": {"name": name, "description": item["description"], "parameters": {"type": "object", "properties": deepcopy(item["properties"]), "required": item["required"], "additionalProperties": False}}})
    return schemas


GENERATION_TOOL_NAMES = {"list_files", "read_file", "read_files", "search_codebase", "write_file", "write_files", "edit_file", "run_command", "collect_assets", "finish"}
MODIFICATION_TOOL_NAMES = {"list_files", "read_file", "read_files", "search_codebase", "write_file", "write_files", "edit_file", "collect_assets", "finish"}
