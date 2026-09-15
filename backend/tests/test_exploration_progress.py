from app.agents.tooling.contracts import ToolCall, ToolResult
from app.agents.tooling.presentation import display_args, display_detail, result_hint
from app.agents.tooling.progress import ExplorationProgress


def _call(name: str, arguments: dict) -> ToolCall:
    return ToolCall(id="call", name=name, arguments=arguments)


def test_new_reads_and_searches_are_valid_exploration():
    progress = ExplorationProgress()
    assert progress.observe(_call("read_file", {"path": "src/App.vue"}), ToolResult(True, {"content": "one"})) == 0
    assert progress.observe(_call("read_file", {"path": "src/main.ts"}), ToolResult(True, {"content": "two"})) == 0
    assert progress.observe(_call("search_codebase", {"query": "submit"}), ToolResult(True, {"matches": []})) == 0
    assert progress.observe(_call("search_codebase", {"query": "handleSubmit"}), ToolResult(True, {"matches": []})) == 0


def test_identical_exploration_is_detected_but_write_resets_it():
    progress = ExplorationProgress()
    search = _call("search_codebase", {"query": "submit"})
    result = ToolResult(True, {"matches": []})
    assert progress.observe(search, result) == 0
    assert progress.observe(search, result) == 1
    assert progress.observe(search, result) == 2
    assert progress.observe(_call("write_file", {"path": "src/App.vue"}), ToolResult(True, {"path": "src/App.vue"})) == 0
    assert progress.observe(search, result) == 0


def test_search_presentation_includes_query_and_match_count():
    call = _call("search_codebase", {"query": "handleSubmit"})
    result = ToolResult(True, {"matches": [{"path": "src/App.vue"}, {"path": "src/App.vue"}]})
    assert display_args(call) == {"query": "handleSubmit"}
    assert display_detail(call) == "handleSubmit"
    assert result_hint(call, result) == "找到 2 处"


def test_search_ignores_build_output(client, admin_headers):
    from app.agents.tooling.executor import ToolExecutionContext, execute_tool
    from app.core.database import SessionLocal
    from app.services.project import project_workspace, write_project_file

    project = client.post("/api/projects", headers=admin_headers, json={"name": "搜索忽略产物", "tech_stack": "vue3"}).json()
    with SessionLocal() as db:
        write_project_file(db, project["id"], "src/App.vue", "const needle = true")
        write_project_file(db, project["id"], "dist/app.js", "const needle = true")
        db.commit()
    result = __import__("asyncio").run(execute_tool(
        _call("search_codebase", {"query": "needle"}),
        ToolExecutionContext(agent="generation", project_id=project["id"], workspace=project_workspace(project["id"])),
    ))
    assert result.ok
    assert [match["path"] for match in result.data["matches"]] == ["src/App.vue"]
