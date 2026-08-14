"""受限命令执行与构建校验。

本地开发为受限子进程（白名单命令 + 超时 + 工作区约束）；Docker 沙箱在 M6 补齐。
"""

import asyncio
import fnmatch
import os
import shutil
from pathlib import Path

from app.core.config import get_settings
from app.agents.tools import list_files

ALLOWED_COMMANDS = {
    "npm",
    "npx",
    "node",
    "python",
    "python3",
}
# 由 Python 内置模拟的只读/检查命令（不依赖外部二进制，Windows 下同样可用）
EMULATED_COMMANDS = {
    "ls",
    "cat",
    "pwd",
    "find",
    "grep",
    "where",
    "dir",
    "type",
    "echo",
    "cd",
}


class BuildError(Exception):
    pass


async def run_command(
    command: list[str],
    cwd: Path,
    timeout: int = 300,
) -> tuple[int, str]:
    if not command:
        raise BuildError("空命令")
    if command[0] in EMULATED_COMMANDS:
        return _emulate_command(command, cwd)
    if command[0] not in ALLOWED_COMMANDS:
        raise BuildError(
            f"命令不在白名单: {command[0]}"
            "（支持 npm/npx/node/python/python3 与内置 ls/cat/pwd/dir/type/echo/find/grep/where）"
        )
    exe = shutil.which(command[0])
    if exe is None:
        exe = shutil.which(command[0] + ".cmd") or shutil.which(command[0] + ".exe")
    if exe is None:
        raise BuildError(f"找不到可执行文件: {command[0]}")
    if exe.lower().endswith((".cmd", ".bat")):
        args = [os.environ.get("COMSPEC", "cmd.exe"), "/c", exe, *command[1:]]
    else:
        args = [exe, *command[1:]]
    env = os.environ.copy()
    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=env,
        )
        output, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except Exception:
            pass
        raise BuildError(f"命令超时（{timeout}s）: {' '.join(command)}")
    text = output.decode("utf-8", errors="replace")
    return proc.returncode or 0, text


def _is_flag(arg: str) -> bool:
    return arg.startswith("-") or arg.startswith("/")


def _emulate_command(command: list[str], cwd: Path) -> tuple[int, str]:
    """内置模拟只读命令，返回 (exit_code, output)。"""
    name = command[0]
    args = command[1:]
    root = cwd.resolve()
    try:
        if name == "pwd":
            return 0, str(root) + "\n"
        if name in ("ls", "dir"):
            paths = [a for a in args if not _is_flag(a)] or ["."]
            lines: list[str] = []
            for raw in paths:
                target = (cwd / raw).resolve()
                if not target.is_relative_to(root):
                    return 1, f"{name}: 路径越界: {raw}\n"
                if target.is_dir():
                    entries = sorted(target.iterdir(), key=lambda x: x.name.lower())
                    lines.extend(
                        e.name + ("/" if e.is_dir() else "") for e in entries
                    )
                elif target.exists():
                    lines.append(target.name)
                else:
                    return 1, f"{name}: 无法访问 '{raw}': 不存在\n"
            return 0, "\n".join(lines[:1000]) + ("\n" if lines else "")
        if name in ("cat", "type"):
            if not args:
                return 1, f"{name}: 缺少文件参数\n"
            chunks: list[str] = []
            for raw in args:
                target = (cwd / raw).resolve()
                if not target.is_relative_to(root):
                    return 1, f"{name}: 路径越界: {raw}\n"
                if not target.is_file():
                    return 1, f"{name}: {raw}: 不存在\n"
                chunks.append(
                    target.read_text(encoding="utf-8", errors="replace")
                )
            return 0, "\n".join(chunks)[:8000] + "\n"
        if name == "echo":
            return 0, " ".join(args) + "\n"
        if name == "cd":
            if not args:
                return 0, "\n"
            target = (cwd / args[0]).resolve()
            if target.is_dir() and target.is_relative_to(root):
                return 0, "（cd 仅校验目录，命令始终在项目目录执行）\n"
            return 1, f"cd: {args[0]}: 目录不存在\n"
        if name == "find":
            paths = [a for a in args if not _is_flag(a)] or ["."]
            pattern = None
            if "-name" in args:
                idx = args.index("-name")
                pattern = args[idx + 1] if idx + 1 < len(args) else None
            found: list[str] = []
            for raw in paths:
                base = (cwd / raw).resolve()
                if not base.is_relative_to(root) or not base.is_dir():
                    continue
                for f in sorted(base.rglob("*")):
                    if f.is_file() and (
                        pattern is None or fnmatch.fnmatch(f.name, pattern)
                    ):
                        found.append(f.relative_to(root).as_posix())
            return 0, "\n".join(found[:500]) + ("\n" if found else "")
        if name == "grep":
            if not args:
                return 1, "grep: 缺少搜索模式\n"
            pattern = args[0]
            files = [a for a in args[1:] if not _is_flag(a)] or list_files(cwd)
            hits: list[str] = []
            for raw in files[:100]:
                target = (cwd / raw).resolve()
                if not target.is_relative_to(root) or not target.is_file():
                    continue
                try:
                    text = target.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue
                for line_no, line in enumerate(text.splitlines(), 1):
                    if pattern in line:
                        hits.append(f"{raw}:{line_no}:{line[:200]}")
            return 0, "\n".join(hits[:300]) + ("\n" if hits else "")
        if name == "where":
            hits = []
            for arg in args:
                hits.append(shutil.which(arg) or f"找不到: {arg}")
            return 0, "\n".join(hits) + "\n"
    except Exception as exc:
        return 1, f"{name}: {type(exc).__name__}: {exc}\n"
    return 1, f"未知命令: {name}\n"


async def _real_build(
    workspace: Path,
    emit,
) -> tuple[bool, list[str], list[str]]:
    log: list[str] = []
    errors: list[str] = []

    async def log_line(line: str) -> None:
        log.append(line)
        if emit is not None:
            await emit(line)

    if (workspace / "package.json").exists():
        await log_line("real: 检测到 package.json，开始 npm 构建")
        if not (workspace / "node_modules").exists():
            await log_line("real: node_modules 缺失，执行 npm install --ignore-scripts")
            code, output = await run_command(
                ["npm", "install", "--ignore-scripts"], workspace, timeout=600
            )
            for line in output.splitlines():
                await log_line(line)
            if code != 0:
                errors.append("npm install 失败")
                return False, log, errors
        await log_line("real: npm run build")
        code, output = await run_command(["npm", "run", "build"], workspace, timeout=600)
        for line in output.splitlines():
            await log_line(line)
        if code != 0:
            errors.append("npm run build 失败")
            return False, log, errors
        await log_line("real: 构建通过")
        return True, log, errors

    # 静态 HTML/CSS/JS：对 .js 做 node --check 语法检查
    js_files = [
        rel
        for rel in list_files(workspace)
        if rel.endswith(".js") and not rel.startswith("node_modules")
    ]
    if js_files:
        await log_line(f"real: 语法检查 {len(js_files)} 个 JS 文件")
        for rel in js_files:
            code, output = await run_command(["node", "--check", rel], workspace, timeout=120)
            if code != 0:
                errors.append(f"{rel}: {output.strip()[:300]}")
            for line in output.splitlines():
                await log_line(line)
        if errors:
            return False, log, errors
    else:
        await log_line("real: 无 JS/package.json，静态校验通过")
    return True, log, errors


async def _mock_build(
    workspace: Path,
    emit,
) -> tuple[bool, list[str], list[str]]:
    log: list[str] = []
    errors: list[str] = []

    async def log_line(line: str) -> None:
        log.append(line)
        if emit is not None:
            await emit(line)

    await log_line("mock: 使用离线模拟构建")
    marker = workspace / ".mock-build-fail"
    if marker.exists():
        marker.unlink()
        await log_line("mock: 检测到构建失败标记 .mock-build-fail")
        errors.append("mock build failed (marker)")
        return False, log, errors
    if (workspace / "package.json").exists():
        if not (workspace / "index.html").exists():
            errors.append("缺少 index.html 入口")
            return False, log, errors
        await log_line("mock: package.json 与 index.html 存在，构建通过")
    else:
        await log_line("mock: 静态工程结构检查通过")
    return True, log, errors


async def validate_build(
    workspace: Path,
    tech_stack: str,
    emit=None,
) -> tuple[bool, list[str], list[str]]:
    mode = get_settings().build_mode
    if mode == "mock":
        return await _mock_build(workspace, emit)
    return await _real_build(workspace, emit)
