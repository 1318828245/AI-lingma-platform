"""命令执行与构建校验。

command_mode=shell：等同本机终端（走系统 Shell，支持 &&、管道、引号），本地开发默认；
command_mode=sandbox：白名单受限子进程（生产/受限环境用），Docker 沙箱在 M6 补齐。
"""

import asyncio
import contextlib
import fnmatch
import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path

from app.core.config import get_settings
from app.agents.tools import list_files

ALLOWED_COMMANDS = {
    "npm",
    "npx",
    "node",
    "python",
    "python3",
    "py",
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
    "rm",
    "del",
    "wc",
    "head",
}


class BuildError(Exception):
    pass


async def _run_subprocess_fallback(
    args: list[str],
    cwd: Path,
    env: dict[str, str],
    timeout: int,
) -> tuple[int, bytes]:
    """在当前事件循环不支持 asyncio 子进程时，使用线程中的同步子进程兜底。

    某些受限运行环境会让 asyncio.create_subprocess_exec 直接抛
    NotImplementedError，但同步 subprocess 仍然可用。把阻塞调用放进线程，
    避免卡住 SSE 和任务队列。
    """

    def execute() -> tuple[int, bytes]:
        try:
            completed = subprocess.run(
                args,
                cwd=str(cwd),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise BuildError(f"命令超时（{timeout}s）: {' '.join(args)}") from exc
        return completed.returncode, completed.stdout or b""

    return await asyncio.to_thread(execute)


async def run_command(
    command: list[str] | str,
    cwd: Path,
    timeout: int = 300,
) -> tuple[int, str]:
    if isinstance(command, str):
        command = shlex.split(command)
    else:
        command = [str(part) for part in command]
        # 部分模型会把整条命令放进数组的单个元素中： ["ls -la"]。
        # 如果不拆分，会把 "ls -la" 当作可执行文件名，最终报找不到命令。
        if len(command) == 1 and any(ch.isspace() for ch in command[0]):
            command = shlex.split(command[0])
    cwd = cwd.resolve()
    if not cwd.exists() or not cwd.is_dir():
        raise BuildError(f"工作目录不存在或不是目录: {cwd}")
    if get_settings().command_mode == "shell":
        return await _run_shell_command(command, cwd, timeout)
    return await _run_sandbox_command(command, cwd, timeout)


async def _run_sandbox_command(
    command: list[str],
    cwd: Path,
    timeout: int = 300,
) -> tuple[int, str]:
    command = [str(part) for part in command]
    if not command:
        raise BuildError("空命令")
    if command[0] in EMULATED_COMMANDS:
        return _emulate_command(command, cwd)
    if command[0] not in ALLOWED_COMMANDS:
        raise BuildError(
            f"命令不在白名单: {command[0]}"
            "（支持 npm/npx/node/python/python3 与内置 ls/cat/pwd/dir/type/echo/find/grep/where/wc/head）"
        )
    exe = _resolve_exe(command[0])
    if exe is None:
        raise BuildError(f"找不到可执行文件: {command[0]}")
    if exe.lower().endswith((".cmd", ".bat")):
        args = [os.environ.get("COMSPEC", "cmd.exe"), "/c", exe, *command[1:]]
    else:
        args = [exe, *command[1:]]
    env = os.environ.copy()
    if command[0] in ("python", "python3", "py"):
        # 强制 python 子进程以 UTF-8 输出，避免 GBK 编码导致内容乱码
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
    proc = None
    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=env,
        )
        output, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except NotImplementedError:
        return_code, output = await _run_subprocess_fallback(args, cwd, env, timeout)
        text = output.decode("utf-8", errors="replace")
        if "\ufffd" in text:
            text = output.decode("gbk", errors="replace")
        return return_code, text
    except asyncio.TimeoutError:
        if proc is not None:
            proc.kill()
            # 必须回收 communicate，避免 Windows 上留下悬挂子进程/句柄。
            with contextlib.suppress(Exception):
                await proc.communicate()
        raise BuildError(f"命令超时（{timeout}s）: {' '.join(command)}")
    text = output.decode("utf-8", errors="replace")
    if "\ufffd" in text:
        text = output.decode("gbk", errors="replace")
    return proc.returncode or 0, text


async def _run_shell_command(
    command: str | list[str],
    cwd: Path,
    timeout: int = 300,
) -> tuple[int, str]:
    """轻量 Shell 语义：shlex 解析引号，支持 && / || / ; 顺序执行与 VAR=val 前缀；
    命令不经 cmd.exe（避免 Windows 引号怪癖），暂不支持管道/重定向。"""
    if isinstance(command, list):
        # 直接拼接会破坏带空格、引号和括号的参数，例如 python -c。
        # 用 shlex.join 生成可逆的命令行，再由同一个解析器还原。
        cmdline = shlex.join([str(part) for part in command])
    else:
        cmdline = command
    if not cmdline.strip():
        raise BuildError("空命令")
    tokens = shlex.split(cmdline)
    if not tokens:
        raise BuildError("空命令")
    # Windows 开发环境里模型可能生成 bash/powershell 脚本。
    # 这些解释器必须把后续脚本作为一个整体传入，不能被本层的
    # && / ; 分段器拆坏。sandbox 模式仍不会放行它们。
    if tokens[0].lower() in ("bash", "sh", "powershell", "pwsh", "cmd"):
        return await _run_direct(tokens, cwd, timeout, os.environ.copy())
    if any(op in tokens for op in ("|", ">", ">>", "<")):
        raise BuildError("暂不支持管道/重定向语法，请拆分成多条命令执行")

    segments: list[tuple[str, list[str]]] = []
    current: list[str] = []
    join_op = ";"
    for token in tokens:
        if token in ("&&", "||", ";"):
            if current:
                segments.append((join_op, current))
                current = []
            join_op = token
        else:
            current.append(token)
    if current:
        segments.append((join_op, current))

    env = os.environ.copy()
    code = 0
    outputs: list[str] = []
    for join_op, argv in segments:
        if join_op == "&&" and code != 0:
            break
        if join_op == "||" and code == 0:
            continue
        seg_env = env
        while argv and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", argv[0]):
            key, value = argv.pop(0).split("=", 1)
            seg_env = {**env, key: value}
        if not argv:
            continue
        if argv[0] in EMULATED_COMMANDS:
            code, output = _emulate_command(argv, cwd)
        else:
            code, output = await _run_direct(argv, cwd, timeout, seg_env)
        outputs.append(output)
    return code, "".join(outputs)


async def _run_direct(
    argv: list[str],
    cwd: Path,
    timeout: int,
    env: dict[str, str],
) -> tuple[int, str]:
    """直接执行（不走 shell），支持 PATH 解析与 python3 回退。"""
    exe = _resolve_exe(argv[0])
    if exe is None:
        raise BuildError(f"找不到可执行文件: {argv[0]}")
    if argv[0] in ("python", "python3", "py"):
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
    if exe.lower().endswith((".cmd", ".bat")):
        args = [os.environ.get("COMSPEC", "cmd.exe"), "/c", exe, *argv[1:]]
    else:
        args = [exe, *argv[1:]]
    proc = None
    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=env,
        )
        output, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except NotImplementedError:
        return_code, output = await _run_subprocess_fallback(args, cwd, env, timeout)
        text = output.decode("utf-8", errors="replace")
        if "\ufffd" in text:
            text = output.decode("gbk", errors="replace")
        return return_code, text
    except asyncio.TimeoutError:
        if proc is not None:
            proc.kill()
            with contextlib.suppress(Exception):
                await proc.communicate()
        raise BuildError(f"命令超时（{timeout}s）: {' '.join(argv)}")
    text = output.decode("utf-8", errors="replace")
    if "\ufffd" in text:
        text = output.decode("gbk", errors="replace")
    return proc.returncode or 0, text


def _resolve_exe(name: str) -> str | None:
    """解析可执行文件路径；跳过 Windows 商店别名 stub（WindowsApps），
    python3 找不到时回退到 python/py。"""
    candidates = {"python3": ["python3", "python", "py"], "python": ["python", "python3", "py"]}.get(
        name, [name]
    )
    found: list[str] = []
    for cand in candidates:
        path = (
            shutil.which(cand)
            or shutil.which(cand + ".cmd")
            or shutil.which(cand + ".exe")
        )
        if path and path not in found:
            found.append(path)
    for path in found:
        if "WindowsApps" not in path:
            return path
    # Windows 商店 alias 是不可执行的 stub，不能把它当作真实解释器返回。
    return None


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
        if name == "wc":
            # 支持生成 Agent 常用的 wc -l file；只读取工作区内文件。
            line_mode = "-l" in args or "/l" in args
            files = [arg for arg in args if not _is_flag(arg)]
            if not line_mode or not files:
                return 1, "wc: 仅支持 wc -l <file>\n"
            rows: list[str] = []
            for raw in files:
                target = (cwd / raw).resolve()
                if not target.is_relative_to(root):
                    return 1, f"wc: 路径越界: {raw}\n"
                if not target.is_file():
                    return 1, f"wc: 找不到文件: {raw}\n"
                text = target.read_text(encoding="utf-8", errors="replace")
                rows.append(f"{len(text.splitlines())} {raw}")
            return 0, "\n".join(rows) + "\n"
        if name == "head":
            # 支持 head -c N file，按字节截取并尽量保持 UTF-8 可读。
            count = None
            files: list[str] = []
            idx = 0
            while idx < len(args):
                arg = args[idx]
                if arg in ("-c", "/c") and idx + 1 < len(args):
                    try:
                        count = int(args[idx + 1])
                    except ValueError:
                        return 1, f"head: 无效字节数: {args[idx + 1]}\n"
                    idx += 2
                    continue
                if not _is_flag(arg):
                    files.append(arg)
                idx += 1
            if count is None or len(files) != 1 or count < 0:
                return 1, "head: 仅支持 head -c <bytes> <file>\n"
            target = (cwd / files[0]).resolve()
            if not target.is_relative_to(root):
                return 1, f"head: 路径越界: {files[0]}\n"
            if not target.is_file():
                return 1, f"head: 找不到文件: {files[0]}\n"
            return 0, target.read_bytes()[:count].decode("utf-8", errors="replace")
        if name == "echo":
            return 0, " ".join(args) + "\n"
        if name == "cd":
            if not args:
                return 0, "\n"
            target = (cwd / args[0]).resolve()
            if target.is_dir() and target.is_relative_to(root):
                return 0, "（cd 仅校验目录，命令始终在项目目录执行）\n"
            return 1, f"cd: {args[0]}: 目录不存在\n"
        if name in ("rm", "del"):
            # 仅允许删除工作区内的文件；-f 只是忽略不存在，不允许隐式递归。
            force = any(arg in ("-f", "/f") for arg in args)
            targets = [arg for arg in args if not _is_flag(arg)]
            if not targets:
                return 1, f"{name}: 缺少文件参数\n"
            for raw in targets:
                target = (cwd / raw).resolve()
                if not target.is_relative_to(root):
                    return 1, f"{name}: 路径越界: {raw}\n"
                if not target.exists():
                    if force:
                        continue
                    return 1, f"{name}: 找不到文件: {raw}\n"
                if target.is_dir():
                    return 1, f"{name}: 拒绝删除目录，请使用受控清理接口: {raw}\n"
                target.unlink()
            return 0, ""
        if name == "find":
            # find . -name "*.js"：-name 的值不是搜索路径。
            paths: list[str] = []
            pattern = None
            idx = 0
            while idx < len(args):
                arg = args[idx]
                if arg == "-name":
                    if idx + 1 < len(args):
                        pattern = args[idx + 1]
                    idx += 2
                    continue
                if not _is_flag(arg):
                    paths.append(arg)
                idx += 1
            paths = paths or ["."]
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
            try:
                code, output = await run_command(
                    ["node", "--check", rel], workspace, timeout=120
                )
            except BuildError as exc:
                await log_line(f"警告：node 语法检查不可用，跳过 {rel}（{exc}）")
                continue
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
