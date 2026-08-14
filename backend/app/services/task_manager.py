"""进程内任务队列：并发上限 + FIFO + 超时。

状态机：pending → running → succeeded / failed / cancelled / timed_out / interrupted。
服务重启时遗留任务由 recover_interrupted_tasks 置为 interrupted。
"""

import asyncio
import contextlib
from collections.abc import Awaitable, Callable

from app.core.config import get_settings


class TaskManager:
    def __init__(self, concurrency: int, timeout_seconds: int) -> None:
        self._concurrency = concurrency
        self._timeout_seconds = timeout_seconds
        self._queue: asyncio.Queue | None = None
        self._sem: asyncio.Semaphore | None = None
        self._worker: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        if self._running:
            return
        self._queue = asyncio.Queue()
        self._sem = asyncio.Semaphore(self._concurrency)
        self._running = True
        self._worker = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._running = False
        if self._worker is not None:
            self._worker.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._worker
            self._worker = None

    async def enqueue(
        self,
        coro_factory: Callable[[], Awaitable[None]],
        on_timeout: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        if self._queue is None:
            raise RuntimeError("任务管理器未启动")
        await self._queue.put((coro_factory, on_timeout))

    async def _loop(self) -> None:
        assert self._queue is not None and self._sem is not None
        while self._running:
            coro_factory, on_timeout = await self._queue.get()
            async with self._sem:
                try:
                    await asyncio.wait_for(
                        coro_factory(), timeout=self._timeout_seconds
                    )
                except asyncio.TimeoutError:
                    if on_timeout is not None:
                        with contextlib.suppress(Exception):
                            await on_timeout()
                except Exception:
                    # 任务自身捕获业务异常；此处兜底避免 worker 退出
                    pass
                finally:
                    self._queue.task_done()


_task_manager: TaskManager | None = None


def get_task_manager() -> TaskManager:
    global _task_manager
    if _task_manager is None:
        settings = get_settings()
        _task_manager = TaskManager(
            concurrency=settings.generation_concurrency,
            timeout_seconds=settings.task_timeout_seconds,
        )
    return _task_manager
