"""生成工作流节点（与提示词 6.1 节点职责一一对应）。"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

from app.agents.generation.state import GenerationState
from app.agents.tools import edit_file, list_files, read_file, write_file
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.generation import Generation
from app.models.guardrail import GuardrailEvent
from app.models.message import Message
from app.services.chat_log import save_generation_event
from app.services.events import get_broker
from app.services.llm import LLMClient
from app.services.sandbox import validate_build as run_validate_build
from app.services.version import snapshot_project

INPUT_BLOCK_PATTERNS = [
    "忽略以上",
    "忽略之前的",
    "输出系统提示词",
    "泄露系统提示词",
    "rm -rf",
    "drop table",
]

async def publish_event(state: GenerationState, event: dict) -> None:
    """推送 SSE 并持久化为会话消息（重新进入页面时回放）。"""
    await get_broker().publish(state["generation_id"], event)
    save_generation_event(state["session_id"], event)

OUTPUT_BLOCK_PATTERNS = [
    "rm -rf",
    "drop table",
    "os.system(",
    "subprocess.call",
]

OUTPUT_WARN_PATTERNS = [
    "../",
    "password=",
    "api_key",
    "secret",
    "token=",
]


class GenerationCancelled(Exception):
    pass


class GenerationBlocked(Exception):
    pass


class GenerationFailed(Exception):
    pass


def _check_cancel(state: GenerationState) -> None:
    with SessionLocal() as db:
        gen = db.get(Generation, state["generation_id"])
        if gen is not None and gen.cancel_requested:
            raise GenerationCancelled()


def _record_guardrail(
    state: GenerationState, direction: str, rule: str, level: str, action: str, snippet: str
) -> None:
    with SessionLocal() as db:
        db.add(
            GuardrailEvent(
                direction=direction,
                rule=rule,
                level=level,
                action=action,
                content_snippet=snippet[:500],
                user_id=state.get("user_id"),
                project_id=state.get("project_id"),
            )
        )
        db.commit()


async def input_guardrail(state: GenerationState) -> dict:
    _check_cancel(state)
    settings = get_settings()
    requirement = state["requirement"]
    guardrails: list[dict] = []
    if len(requirement) > settings.max_requirement_length:
        _record_guardrail(
            state, "input", "length", "high", "block", requirement[:500]
        )
        raise GenerationBlocked("输入超长，超过最大需求长度限制")
    lowered = requirement.lower()
    for pattern in INPUT_BLOCK_PATTERNS:
        if pattern in lowered:
            _record_guardrail(
                state, "input", f"block:{pattern}", "high", "block", requirement[:500]
            )
            raise GenerationBlocked(f"输入被护轨拦截：命中规则 {pattern}")
    guardrails.append({"rule": "input.basic", "level": "info", "action": "pass"})
    return {"guardrails": guardrails, "status": "guarded"}


async def parse_requirements(state: GenerationState) -> dict:
    _check_cancel(state)
    llm = LLMClient()
    parsed = await llm.parse_requirement(state["requirement"], state["tech_stack"])
    await publish_event(state, {"type": "stage", "stage": "parse"})
    await publish_event(
        state, {"type": "thought", "content": f"需求解析完成：{parsed['goal']}"}
    )
    return {"parsed_requirement": parsed, "status": "parsed"}


async def create_plan(state: GenerationState) -> dict:
    _check_cancel(state)
    llm = LLMClient()
    plan = await llm.create_plan(state["parsed_requirement"], state["tech_stack"])
    with SessionLocal() as db:
        gen = db.get(Generation, state["generation_id"])
        if gen is not None:
            gen.plan_json = plan
            db.commit()
    await publish_event(state, {"type": "stage", "stage": "plan"})
    steps_text = "；".join(
        f"{idx + 1}. {step.get('step', '')}" for idx, step in enumerate(plan[:8])
    )
    await publish_event(
        state, {"type": "thought", "content": f"实施计划：{steps_text}"}
    )
    return {"plan": plan, "status": "planned"}


def _ai_section(state: GenerationState) -> str:
    goal = state.get("parsed_requirement", {}).get("goal", state["requirement"])[:120]
    features = state.get("parsed_requirement", {}).get("features", [])[:5]
    items = "".join(f"<li>{f}</li>" for f in features)
    return (
        '<section id="ai-generated" style="margin-top:24px;padding:16px;'
        'border:1px dashed #334155;border-radius:12px">'
        f"<h2>AI 生成摘要</h2><p>{goal}</p><ul>{items}</ul></section>"
    )


def _vue_note(state: GenerationState) -> str:
    goal = state.get("parsed_requirement", {}).get("goal", state["requirement"])[:80]
    return (
        '<p class="ai-note" style="padding:8px 12px;background:#eef2ff;'
        'border-radius:8px;font-size:14px;color:#3730a3">'
        f"AI 生成需求：{goal}</p>"
    )


def _html_scaffold(goal: str) -> dict[str, str]:
    return {
        "index.html": f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{goal[:40]}</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <main class="page">
    <h1>{goal[:60]}</h1>
    <p class="desc">由 AI 灵码平台生成的前端工程。</p>
    <button onclick="greet()">点击体验</button>
    <p id="tip" class="tip"></p>
  </main>
  <script src="script.js"></script>
</body>
</html>
""",
        "style.css": """* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: "Segoe UI", "Microsoft YaHei", sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 24px; }
.page { max-width: 520px; text-align: center; }
h1 { font-size: 28px; margin-bottom: 12px; }
.desc { color: #94a3b8; margin-bottom: 24px; }
button { padding: 10px 22px; border: none; border-radius: 10px; background: #2563eb; color: #fff; cursor: pointer; font-size: 15px; }
.tip { margin-top: 16px; color: #38bdf8; min-height: 20px; }
""",
        "script.js": """function greet() {
  document.getElementById("tip").textContent = "你好，这是 AI 灵码平台生成的页面！";
}
""",
    }


def _vue_scaffold(goal: str) -> dict[str, str]:
    app_vue = """<template>
  <div class="card">
    <h1>__GOAL__</h1>
    <p class="desc">由 AI 灵码平台生成的 Vue 3 工程。</p>
    <button @click="clicked = true">点击体验</button>
    <p v-if="clicked" class="tip">你好，这是 AI 灵码平台生成的页面！</p>
  </div>
</template>

<script setup>
import { ref } from "vue";
const clicked = ref(false);
</script>

<style scoped>
.card { max-width: 520px; text-align: center; background: #fff; border-radius: 16px; padding: 40px; box-shadow: 0 10px 30px rgba(0,0,0,.08); }
h1 { margin-bottom: 12px; }
.desc { color: #64748b; margin-bottom: 24px; }
button { padding: 10px 22px; border: none; border-radius: 10px; background: #2563eb; color: #fff; cursor: pointer; }
.tip { margin-top: 16px; color: #2563eb; }
</style>
""".replace("__GOAL__", goal[:60])
    return {
        "package.json": """{
  "name": "ai-generated-app",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": { "vue": "^3.4.21" },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.4",
    "vite": "^5.2.8"
  }
}
""",
        "vite.config.js": """import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  server: { port: 5173 },
});
""",
        "index.html": """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI 生成应用</title>
</head>
<body>
  <div id="app"></div>
  <script type="module" src="/src/main.js"></script>
</body>
</html>
""",
        "src/main.js": """import { createApp } from "vue";
import App from "./App.vue";
import "./style.css";

createApp(App).mount("#app");
""",
        "src/style.css": """* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: "Segoe UI", "Microsoft YaHei", sans-serif; background: #f1f5f9; color: #334155; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
""",
        "src/App.vue": app_vue,
    }


def _output_guardrail_check(state: GenerationState, rel_path: str, content: str) -> None:
    lowered = content.lower()
    for pattern in OUTPUT_BLOCK_PATTERNS:
        if pattern in lowered:
            _record_guardrail(
                state, "output", f"block:{pattern}", "high", "block",
                f"{rel_path}: {content[:300]}",
            )
            raise GenerationBlocked(f"输出护轨拦截：{rel_path} 命中规则 {pattern}")
    for pattern in OUTPUT_WARN_PATTERNS:
        if pattern in lowered:
            _record_guardrail(
                state, "output", f"warn:{pattern}", "warn", "warn",
                f"{rel_path}: {content[:300]}",
            )


async def _write_with_guardrail(
    state: GenerationState,
    workspace: Path,
    rel_path: str,
    content: str,
    broker,
    written: list[str],
) -> None:
    _output_guardrail_check(state, rel_path, content)
    with SessionLocal() as db:
        write_file(db, state["project_id"], workspace, rel_path, content)
    await publish_event(
        state, {"type": "tool_call", "tool": "write_file", "args": {"path": rel_path}}
    )
    await publish_event(
        state,
        {"type": "file_written", "path": rel_path, "content": content[:16000]},
    )
    written.append(rel_path)


async def _edit_with_guardrail(
    state: GenerationState,
    workspace: Path,
    rel_path: str,
    old: str,
    new: str,
    broker,
    written: list[str],
) -> None:
    _output_guardrail_check(state, rel_path, new)
    with SessionLocal() as db:
        edit_file(db, state["project_id"], workspace, rel_path, old, new)
    await publish_event(
        state, {"type": "tool_call", "tool": "edit_file", "args": {"path": rel_path}}
    )
    updated = read_file(workspace, rel_path)
    await publish_event(
        state,
        {"type": "file_written", "path": rel_path, "content": updated[:16000]},
    )
    written.append(rel_path)


async def _mock_generate(state: GenerationState, workspace: Path, broker) -> list[str]:
    written: list[str] = []
    files = list_files(workspace)
    parsed = state.get("parsed_requirement", {})
    goal = parsed.get("goal", state["requirement"])

    if not files:
        scaffold = (
            _html_scaffold(goal)
            if state["tech_stack"] in ("html", "static")
            else _vue_scaffold(goal)
        )
        for rel_path, content in scaffold.items():
            await _write_with_guardrail(state, workspace, rel_path, content, broker, written)
    else:
        index = workspace / "index.html"
        if index.exists():
            content = read_file(workspace, "index.html")
            if "ai-generated" not in content:
                section = _ai_section(state)
                if "</body>" in content:
                    new_content = content.replace("</body>", section + "\n</body>", 1)
                else:
                    new_content = content + "\n" + section
                await _edit_with_guardrail(
                    state, workspace, "index.html", content, new_content, broker, written
                )
        appvue = workspace / "src" / "App.vue"
        if appvue.exists():
            content = read_file(workspace, "src/App.vue")
            if "ai-note" not in content and "<template>" in content:
                note = _vue_note(state)
                new_content = content.replace("<template>", "<template>\n  " + note, 1)
                await _edit_with_guardrail(
                    state, workspace, "src/App.vue", content, new_content, broker, written
                )

    if "ai-generation.json" not in written:
        meta = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "mode": get_settings().llm_model,
            "goal": parsed.get("goal", ""),
            "requirement": state["requirement"][:500],
            "files": list_files(workspace),
        }
        await _write_with_guardrail(
            state,
            workspace,
            "ai-generation.json",
            json.dumps(meta, ensure_ascii=False, indent=2),
            broker,
            written,
        )
    return written


async def _mock_repair(state: GenerationState, workspace: Path, broker) -> list[str]:
    written: list[str] = []
    marker = workspace / ".mock-build-fail"
    if marker.exists():
        marker.unlink()
    index = workspace / "index.html"
    if index.exists():
        content = read_file(workspace, "index.html")
        if "mock-repaired" not in content and "</body>" in content:
            new_content = content.replace(
                "</body>", "<!-- mock-repaired -->\n</body>", 1
            )
            await _edit_with_guardrail(
                state, workspace, "index.html", content, new_content, broker, written
            )
    await publish_event(
        state,
        {"type": "thought", "content": "修复完成：已清理构建失败标记并做局部修正"},
    )
    return written


async def generate_code(state: GenerationState) -> dict:
    _check_cancel(state)
    broker = get_broker()
    gen_id = state["generation_id"]
    settings = get_settings()
    await publish_event(state, {"type": "stage", "stage": "generate"})

    llm_real = (
        settings.llm_model != "mock"
        and settings.llm_base_url
        and settings.llm_api_key
    )
    if llm_real and not state.get("repair_mode"):
        from app.agents.generation.agent import run_generation_agent

        result = await run_generation_agent(state)
        return {
            "files": list(dict.fromkeys([*state.get("files", []), *result["files"]])),
            "summary": result["summary"],
            "token_usage": result["token_usage"],
            "status": "generating",
        }

    if "慢速" in state["requirement"]:
        await asyncio.sleep(1.0)
    elif settings.mock_delay_seconds > 0:
        await asyncio.sleep(settings.mock_delay_seconds)
    workspace = Path(state["workspace"])
    workspace.mkdir(parents=True, exist_ok=True)
    if state.get("repair_mode"):
        written = await _mock_repair(state, workspace, broker)
        return {"files": list(dict.fromkeys([*state.get("files", []), *written])), "status": "repairing"}
    written = await _mock_generate(state, workspace, broker)
    await publish_event(
        state, {"type": "thought", "content": f"生成完成：写入/修改 {len(written)} 个文件"}
    )
    return {"files": list(dict.fromkeys([*state.get("files", []), *written])), "status": "generating"}


async def output_guardrail(state: GenerationState) -> dict:
    _check_cancel(state)
    workspace = Path(state["workspace"])
    guardrails = list(state.get("guardrails", []))
    for rel in state.get("files", []):
        try:
            content = read_file(workspace, rel)
        except Exception:
            continue
        _output_guardrail_check(state, rel, content)
        guardrails.append({"rule": "output.recheck", "level": "info", "action": "pass", "path": rel})
    return {"guardrails": guardrails}


async def validate_build(state: GenerationState) -> dict:
    _check_cancel(state)
    gen_id = state["generation_id"]
    broker = get_broker()
    with SessionLocal() as db:
        gen = db.get(Generation, gen_id)
        if gen is not None:
            gen.build_attempt += 1
            db.commit()
            attempt = gen.build_attempt
        else:
            attempt = state.get("build_attempt", 0) + 1
    state["build_attempt"] = attempt

    await publish_event(state, {"type": "stage", "stage": "build"})

    async def emit(line: str) -> None:
        state["build_log"].append(line)
        await publish_event(state, {"type": "build_log", "line": line})

    ok, log, errors = await run_validate_build(
        Path(state["workspace"]), state["tech_stack"], emit=emit
    )
    state["build_log"] = log
    if ok:
        return {"build_attempt": attempt, "status": "build_ok", "errors": []}
    if attempt < state["max_build_attempts"]:
        await publish_event(state, {"type": "stage", "stage": "repair"})
        await publish_event(
            state,
            {
                "type": "thought",
                "content": f"构建失败（第 {attempt} 次），进入修复：{errors[0][:120]}",
            },
        )
        return {
            "build_attempt": attempt,
            "status": "repair",
            "errors": errors,
            "build_log": state["build_log"],
            "repair_mode": True,
        }
    raise GenerationFailed(f"构建失败且达到最大尝试次数：{errors[0] if errors else '未知错误'}")


async def summarize(state: GenerationState) -> dict:
    llm = LLMClient()
    summary = state.get("summary") or await llm.summarize(state)
    state["summary"] = summary
    with SessionLocal() as db:
        gen = db.get(Generation, state["generation_id"])
        if gen is not None:
            gen.status = "succeeded"
            gen.finished_at = datetime.now()
            gen.llm_model = state.get("llm_model") or get_settings().llm_model
            gen.prompt_tokens = state["token_usage"]["prompt_tokens"]
            gen.completion_tokens = state["token_usage"]["completion_tokens"]
            snapshot_project(
                db,
                gen.project_id,
                source_type="generation",
                source_id=gen.id,
                summary=summary[:500],
            )
        db.add(
            Message(
                session_id=state["session_id"],
                role="assistant",
                content=summary,
                msg_type="summary",
            )
        )
        db.commit()
    await publish_event(
        state,
        {
            "type": "completed",
            "generation_id": state["generation_id"],
            "summary": summary,
            "build_attempt": state["build_attempt"],
        },
    )
    return {"status": "succeeded", "summary": summary}
