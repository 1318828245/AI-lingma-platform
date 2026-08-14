"""受限命令执行与构建校验。

本地开发为受限子进程（白名单命令 + 超时 + 工作区约束）；Docker 沙箱在 M6 补齐。
"""

import asyncio
import os
import shutil
from pathlib import Path

from app.core.config import get_settings
from app.agents.tools import list_files

ALLOWED_COMMANDS = {
    "npm": True,
    "npx": True,
    "node": True,
    "python": True,
    "python3": True,
}


class BuildError(Exception):
    pass


async def run_command(
    command: list[str],
    cwd: Path,
    timeout: int = 300,
) -> tuple[int, str]:
    if not command or command[0] not in ALLOWED_COMMANDS:
        raise BuildError(f"命令不在白名单: {command[0] if command else 'empty'}")
    exe = shutil.which(command[0])
    if exe is None:
        raise BuildError(f"找不到可执行文件: {command[0]}")
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
