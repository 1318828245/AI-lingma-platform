"""首页项目截图：用本机无头浏览器（Edge/Chrome）截取预览页。"""

import asyncio
import shutil
import tempfile
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


_capture_lock: asyncio.Lock | None = None


def _get_lock() -> asyncio.Lock:
    global _capture_lock
    if _capture_lock is None:
        _capture_lock = asyncio.Lock()
    return _capture_lock


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
                "--virtual-time-budget=5000",
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
            except (NotImplementedError, OSError):
                pass
            finally:
                shutil.rmtree(user_dir, ignore_errors=True)
            if output.exists() and output.stat().st_size > 0:
                return True
    return False
