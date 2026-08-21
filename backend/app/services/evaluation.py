"""Deterministic project quality checks persisted for generation and edit deliveries."""

import re
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token
from app.models.evaluation import Evaluation
from app.models.file import File
from app.services.screenshot import capture_screenshot
from app.services.vision_evaluation import QwenVisionEvaluationProvider, VisionEvaluationUnavailable


_SOURCE_IGNORES = {"node_modules", "dist", "build", ".git", ".vite", "__pycache__"}
_RISK_RULES = (
    ("destructive_command", re.compile(r"\brm\s+-[a-z]*r[a-z]*f|\bdrop\s+table\b", re.I), "发现可能删除文件或数据库表的命令"),
    ("shell_execution", re.compile(r"\bos\.system\s*\("), "发现绕开受控执行器的系统命令调用"),
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"), "发现私钥内容"),
    ("api_secret", re.compile(r"\b(?:api[_-]?key|secret|access[_-]?token)\s*[:=]\s*['\"]?(?:sk-|AKIA)[A-Za-z0-9_\-]{12,}", re.I), "发现疑似明文密钥或令牌"),
)
_DIMENSION_LABELS = {
    "executable": "可正常运行",
    "structure": "项目结构完整",
    "intent": "需求与使用体验",
    "safety": "安全检查",
}


def evaluation_wire(row: Evaluation) -> dict:
    dimensions = row.dimensions_json or {}
    # Existing projects may contain the pre-M3-2 five-dimension /100 result.
    # Normalize it at the API boundary so a user never sees two score systems.
    if "executable" not in dimensions and "build" in dimensions:
        def legacy_score(key: str) -> int:
            value = float((dimensions.get(key) or {}).get("score") or 0)
            return min(5, max(1, round(value / 20)))

        dimensions = {
            "executable": {"label": _DIMENSION_LABELS["executable"], "score": legacy_score("build"), "detail": "已按新的交付检查规则换算"},
            "structure": {"label": _DIMENSION_LABELS["structure"], "score": legacy_score("structure"), "detail": "已按新的交付检查规则换算"},
            "intent": {"label": _DIMENSION_LABELS["intent"], "score": legacy_score("coverage"), "detail": "已按新的交付检查规则换算"},
            "safety": {"label": _DIMENSION_LABELS["safety"], "score": legacy_score("safety"), "detail": "已按新的交付检查规则换算"},
        }
    score = sum(float(item.get("score") or 0) for item in dimensions.values())
    return {
        "id": row.id,
        "ref_type": row.ref_type,
        "ref_id": row.ref_id,
        "project_id": row.project_id,
        "score": round(score, 1),
        "pass": score >= 18,
        "dimensions": dimensions,
        "issues": row.issues_json or [],
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def latest_project_evaluation(db: Session, project_id: int) -> Evaluation | None:
    return (
        db.query(Evaluation)
        .filter(Evaluation.project_id == project_id)
        .order_by(Evaluation.created_at.desc(), Evaluation.id.desc())
        .first()
    )


def _source_files(workspace: Path):
    if not workspace.exists():
        return []
    return [
        path for path in workspace.rglob("*")
        if path.is_file() and path.stat().st_size <= 1_000_000
        and not any(part in _SOURCE_IGNORES for part in path.relative_to(workspace).parts)
    ]


def _safety_findings(workspace: Path) -> list[dict]:
    findings: list[dict] = []
    for path in _source_files(workspace):
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for line_no, line in enumerate(lines, 1):
            for rule, pattern, message in _RISK_RULES:
                if pattern.search(line):
                    findings.append({"rule": rule, "path": str(path.relative_to(workspace)).replace("\\", "/"), "line": line_no, "message": message})
    return findings


def evaluate_delivery(
    db: Session,
    *,
    project_id: int,
    ref_type: str,
    ref_id: int,
    succeeded: bool,
    requirement: str,
    workspace: Path,
    changed_files: list[str] | None = None,
) -> Evaluation:
    """Score stable signals; this is deliberately auditable instead of an opaque LLM grade."""
    files = db.query(File).filter(File.project_id == project_id).all()
    file_count = len(files)

    dimensions: dict[str, dict] = {}
    issues: list[dict] = []

    def add(key: str, score: float, detail: str, recommendation: str | None = None):
        dimensions[key] = {"label": _DIMENSION_LABELS[key], "score": round(score, 1), "detail": detail}
        if recommendation:
            issues.append({"dimension": key, "label": _DIMENSION_LABELS[key], "message": detail, "recommendation": recommendation})

    add("executable", 5 if succeeded else 1, "页面已构建并可打开预览" if succeeded else "本次交付未能成功构建或打开预览", None if succeeded else "先处理构建日志中的第一个错误，再重新生成预览。")

    structure = min(5, max(1, file_count))
    if workspace.exists() and any(workspace.iterdir()):
        structure = min(5, structure + 1)
    add("structure", structure, f"已识别 {file_count} 个项目文件", None if structure >= 4 else "补齐入口页、样式或组件文件，避免交付空壳页面。")

    intent = 3
    add("intent", intent, "等待视觉评审：将根据预览截图、核心功能和交互证据评分", "完成视觉评审后再决定是否需要补充页面、功能或交互。")

    findings = _safety_findings(workspace)
    safety = max(1, 5 - min(4, len(findings)))
    detail = "未发现明文密钥、危险删除命令或绕开受控执行器的调用" if not findings else f"发现 {len(findings)} 项需要确认的安全问题"
    recommendation = None if not findings else "检查下方命中文件；删除敏感值，并改用受控工具或环境变量。"
    add("safety", safety, detail, recommendation)
    for finding in findings:
        issues.append({"dimension": "safety", "label": _DIMENSION_LABELS["safety"], "message": f"{finding['path']} 第 {finding['line']} 行：{finding['message']}", "recommendation": "查看并处理该处代码或配置。", "evidence": finding})

    score = sum(item["score"] for item in dimensions.values())
    db.query(Evaluation).filter(Evaluation.ref_type == ref_type, Evaluation.ref_id == ref_id).delete(synchronize_session=False)
    row = Evaluation(project_id=project_id, ref_type=ref_type, ref_id=ref_id, score=score, dimensions_json=dimensions, issues_json=issues, pass_=score >= 18)
    db.add(row)
    db.flush()
    return row


async def apply_visual_evaluation(
    db: Session, evaluation: Evaluation, *, user_id: int, requirement: str, workspace: Path
) -> Evaluation:
    """Use the configured vision provider to replace the provisional intent score."""
    provider = QwenVisionEvaluationProvider()
    dimensions = dict(evaluation.dimensions_json or {})
    intent = dict(dimensions.get("intent") or {})
    if not provider.enabled:
        intent["detail"] = "视觉评审未启用；当前分数仅代表等待人工或视觉模型复核"
        dimensions["intent"] = intent
        evaluation.dimensions_json = dimensions
        evaluation.issues_json = [issue for issue in (evaluation.issues_json or []) if issue.get("dimension") != "intent"] + [{
            "dimension": "intent", "label": _DIMENSION_LABELS["intent"],
            "message": intent["detail"],
            "recommendation": "配置视觉模型后，点击“重新检查”。",
        }]
        return evaluation
    shot = get_settings().storage_dir / "evaluations" / str(evaluation.project_id) / f"{evaluation.ref_type}-{evaluation.ref_id}.png"
    token = create_access_token(user_id)
    url = f"{get_settings().backend_url.rstrip('/')}/preview/{evaluation.project_id}/?token={token}"
    try:
        if not await capture_screenshot(url, shot):
            raise VisionEvaluationUnavailable("预览截图采集失败")
        result = await provider.evaluate(shot, {
            "requirement": requirement[:8000],
            "files": [str(path.relative_to(workspace)).replace("\\", "/") for path in _source_files(workspace)[:120]],
        })
        reviewed = result.get("user_intent_accuracy") or {}
        score = int(reviewed.get("score"))
        if score < 1 or score > 5:
            raise VisionEvaluationUnavailable("视觉评估分数不在 1 到 5 的范围内")
        findings = [str(item)[:240] for item in reviewed.get("findings") or []]
        suggestions = [str(item)[:240] for item in reviewed.get("suggestions") or []]
        intent.update({"score": score, "detail": "；".join(findings) or "视觉评审已完成"})
        dimensions["intent"] = intent
        # Replace the provisional “waiting for vision review” issue rather
        # than leaving a contradictory recommendation in the UI.
        issues = [issue for issue in (evaluation.issues_json or []) if issue.get("dimension") != "intent"]
        if score < 5:
            issues.append({"dimension": "intent", "label": _DIMENSION_LABELS["intent"], "message": "；".join(findings) or "视觉评审发现可改进项", "recommendation": "；".join(suggestions) or "根据预览截图补充核心功能、视觉层级或交互反馈。"})
        evaluation.dimensions_json = dimensions
        evaluation.issues_json = issues
    except VisionEvaluationUnavailable as exc:
        intent["detail"] = f"视觉评审未完成：{exc}"
        dimensions["intent"] = intent
        evaluation.dimensions_json = dimensions
        issues = [issue for issue in (evaluation.issues_json or []) if issue.get("dimension") != "intent"]
        issues.append({
            "dimension": "intent", "label": _DIMENSION_LABELS["intent"],
            "message": intent["detail"],
            "recommendation": "确认预览服务与视觉模型配置后，点击“重新检查”。",
        })
        evaluation.issues_json = issues
    evaluation.score = sum(float(item.get("score") or 0) for item in dimensions.values())
    evaluation.pass_ = evaluation.score >= 18
    db.flush()
    return evaluation
