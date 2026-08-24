"""管理员运行时配置覆盖：落库并在服务启动时恢复到 Settings 实例。"""


class SettingsStore:
    def __init__(self) -> None:
        self._overrides: dict[str, object] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        from app.core.database import SessionLocal
        from app.models.platform_setting import PlatformSetting

        with SessionLocal() as db:
            self._overrides = {row.key: row.value_json for row in db.query(PlatformSetting).all()}
        self._loaded = True

    def get(self, key: str, default: object = None) -> object:
        self._ensure_loaded()
        return self._overrides.get(key, default)

    def set(self, key: str, value: object) -> None:
        self._ensure_loaded()
        from app.core.database import SessionLocal
        from app.models.platform_setting import PlatformSetting

        self._overrides[key] = value
        with SessionLocal() as db:
            row = db.get(PlatformSetting, key)
            if row is None:
                db.add(PlatformSetting(key=key, value_json=value))
            else:
                row.value_json = value
            db.commit()

    def snapshot(self) -> dict[str, object]:
        self._ensure_loaded()
        return dict(self._overrides)

    def apply(self, settings: object, keys: object) -> None:
        self._ensure_loaded()
        for key, value in self._overrides.items():
            if key in keys:
                setattr(settings, key, value)


settings_store = SettingsStore()
