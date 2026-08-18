from typing import TypedDict


class ModificationState(TypedDict, total=False):
    modification_id: int
    project_id: int
    session_id: int
    workspace: str
    instruction: str
    element_snapshot: dict
    related_files: list[str]
    changed_files: list[str]
    token_usage: dict
