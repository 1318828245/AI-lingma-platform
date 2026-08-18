"""进程内 SSE 事件总线：按 generation/modification id 分发实时事件。"""

import asyncio
import threading


class EventBroker:
    def __init__(self) -> None:
        self._queues: dict[int, list[asyncio.Queue]] = {}
        # 使用线程锁：队列操作均为短促非阻塞操作，且避免单例锁绑定某个事件循环
        self._lock = threading.Lock()

    async def subscribe(self, key: int) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        with self._lock:
            self._queues.setdefault(key, []).append(queue)
        return queue

    async def unsubscribe(self, key: int, queue: asyncio.Queue) -> None:
        with self._lock:
            queues = self._queues.get(key)
            if queues and queue in queues:
                queues.remove(queue)
            if queues is not None and not queues:
                self._queues.pop(key, None)

    async def publish(self, key: int, event: dict) -> None:
        with self._lock:
            queues = list(self._queues.get(key, []))
        for queue in queues:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass

    async def close(self, key: int) -> None:
        with self._lock:
            queues = self._queues.pop(key, [])
        for queue in queues:
            try:
                queue.put_nowait({"type": "closed"})
            except asyncio.QueueFull:
                pass


_broker: EventBroker | None = None


def get_broker() -> EventBroker:
    global _broker
    if _broker is None:
        _broker = EventBroker()
    return _broker
