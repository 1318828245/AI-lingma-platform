"""P0 简化的运行时设置覆盖（内存态，重启后恢复 env 默认值）。

文档第八节要求 GET/PUT /api/admin/settings；正式持久化在 M5 管理后台里程碑补齐。
"""


class SettingsStore:
    def __init__(self) -> None:
        self._overrides: dict[str, object] = {}

    def get(self, key: str, default: object = None) -> object:
        return self._overrides.get(key, default)

    def set(self, key: str, value: object) -> None:
        self._overrides[key] = value

    def snapshot(self) -> dict[str, object]:
        return dict(self._overrides)


settings_store = SettingsStore()
