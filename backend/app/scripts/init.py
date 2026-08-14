"""初始化数据库、内置管理员与种子模板。

用法（在 backend 目录下）：
    python -m app.scripts.init
"""

from app.core.database import SessionLocal, init_db
from app.services.seed import ensure_admin, seed_templates


def main() -> None:
    init_db()
    with SessionLocal() as db:
        admin = ensure_admin(db)
        count = seed_templates(db)
    print(f"数据库就绪；管理员账号: {admin.username}")
    print(f"种子模板: {count} 个（已有则跳过）")


if __name__ == "__main__":
    main()
