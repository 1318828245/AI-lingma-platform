"""首页项目截图：用本机无头浏览器（Edge/Chrome）截取预览页。"""

import asyncio
import shutil
import subprocess
import tempfile
from contextlib import suppress
from pathlib import Path

from app.core.config import get_settings

BROWSER_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def find_browser() -> str | None:
    for candidate in BROWSER_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    for name in ("msedge", "chrome", "chromium", "google-chrome"):
        path = shutil.which(name)
        if path:
            return path
    return None


_capture_locks: dict[asyncio.AbstractEventLoop, asyncio.Lock] = {}


def _get_lock() -> asyncio.Lock:
    # TestClient/重载开发环境可能反复创建事件循环，不能复用绑定到旧循环的 Lock。
    loop = asyncio.get_running_loop()
    lock = _capture_locks.get(loop)
    if lock is None:
        lock = asyncio.Lock()
        _capture_locks[loop] = lock
    return lock


async def _capture_with_sync_fallback(
    command: list[str], timeout: int
) -> None:
    """asyncio 子进程不可用时在线程中运行同步浏览器进程。"""

    def run() -> None:
        try:
            subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            # run 已经负责终止超时子进程；截图文件存在性由调用方判断。
            return

    await asyncio.to_thread(run)


async def capture_screenshot(url: str, output: Path, timeout: int | None = None) -> bool:
    browser = find_browser()
    if browser is None:
        return False
    settings = get_settings()
    timeout = timeout or settings.screenshot_timeout_seconds
    output.parent.mkdir(parents=True, exist_ok=True)
    # 串行截图：避免多个无头 Edge/Chrome 并发时互相冲突
    async with _get_lock():
        for _ in range(2):
            user_dir = tempfile.mkdtemp(prefix="ailingma_shot_")
            command = [
                browser,
                "--headless",
                "--disable-gpu",
                "--hide-scrollbars",
                "--no-first-run",
                "--disable-extensions",
                "--window-size=1280,800",
                f"--virtual-time-budget={settings.screenshot_virtual_time_budget_ms}",
                f"--user-data-dir={user_dir}",
                f"--screenshot={output}",
                url,
            ]
            try:
                proc = await asyncio.create_subprocess_exec(
                    *command,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                try:
                    await asyncio.wait_for(proc.wait(), timeout=timeout)
                except asyncio.TimeoutError:
                    try:
                        proc.kill()
                    except Exception:
                        pass
            except NotImplementedError:
                with suppress(Exception):
                    await _capture_with_sync_fallback(command, timeout)
            except OSError:
                pass
            finally:
                shutil.rmtree(user_dir, ignore_errors=True)
            if output.exists() and output.stat().st_size > 0:
                return True
    return False
