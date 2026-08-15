"""首页项目截图：用本机无头浏览器（Edge/Chrome）截取预览页。"""

import asyncio
import shutil
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


async def capture_screenshot(url: str, output: Path, timeout: int | None = None) -> bool:
    browser = find_browser()
    if browser is None:
        return False
    settings = get_settings()
    timeout = timeout or settings.screenshot_timeout_seconds
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        browser,
        "--headless",
        "--disable-gpu",
        "--hide-scrollbars",
        "--no-first-run",
        "--disable-extensions",
        "--window-size=1280,800",
        "--virtual-time-budget=5000",
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
            return False
    except (NotImplementedError, OSError):
        return False
    if not output.exists() or output.stat().st_size == 0:
        return False
    return True
