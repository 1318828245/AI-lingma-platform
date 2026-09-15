"""Deterministic review of instructions before an Agent receives them.

This is intentionally a narrow, auditable gate.  It detects high-confidence
attempts to override instruction hierarchy and reach a protected sink; a word
such as "提示词" by itself is not a reason to reject a product requirement.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata


@dataclass(frozen=True)
class InstructionReview:
    action: str  # pass | warn | block
    rule: str
    reason: str


_OVERRIDE = re.compile(
    r"(?:ignore\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions?|rules?|prompts?)"
    r"|忽略\s*(?:之前|先前|以上|前面).{0,12}(?:指令|规则|提示(?:词)?|要求))",
    re.I,
)
_PROTECTED_SINK = re.compile(
    r"(?:system\s*prompt|系统\s*(?:提示词|指令)|api[\s_-]*key|password|secret|token|"
    r"\.env|环境变量|泄露|输出|显示|读取|发送|上传|reveal|leak|exfiltrat|print|send|upload)",
    re.I,
)
_DESTRUCTIVE = re.compile(r"(?:\brm\s+-[a-z]*r[a-z]*f\b|\bdrop\s+table\b)", re.I)


def normalize_review_text(text: str) -> str:
    """Fold common obfuscation without changing the original audited snippet."""
    folded = unicodedata.normalize("NFKC", text or "")
    folded = "".join(char for char in folded if unicodedata.category(char) != "Cf")
    return re.sub(r"\s+", " ", folded).strip().lower()


def review_instruction(text: str) -> InstructionReview:
    """Classify a user instruction with conservative block semantics.

    A bare override phrase is retained as an auditable warning.  Blocking needs
    either a destructive command or an override phrase combined with a request
    to disclose protected data / execute a privileged action.
    """
    normalized = normalize_review_text(text)
    if _DESTRUCTIVE.search(normalized):
        return InstructionReview("block", "destructive-command", "包含破坏性命令")
    if _OVERRIDE.search(normalized) and _PROTECTED_SINK.search(normalized):
        return InstructionReview("block", "instruction-override-protected-sink", "试图覆盖指令优先级并访问受保护内容")
    if _OVERRIDE.search(normalized):
        return InstructionReview("warn", "instruction-override-signal", "检测到可能的指令覆盖语句；未命中受保护动作")
    return InstructionReview("pass", "input-reviewed", "未发现高置信度越权信号")
