import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="ailingma_test_")
os.environ["AI_LINGMA_DATABASE_URL"] = f"sqlite:///{os.path.join(_tmp, 'test.db').replace(os.sep, '/')}"
os.environ["AI_LINGMA_STORAGE_DIR"] = _tmp
os.environ["AI_LINGMA_JWT_SECRET"] = "test-secret-0123456789abcdef0123456789abcdef"
os.environ["AI_LINGMA_BUILD_MODE"] = "mock"
os.environ["AI_LINGMA_GENERATION_CONCURRENCY"] = "2"
os.environ["AI_LINGMA_TASK_TIMEOUT_SECONDS"] = "30"
os.environ["AI_LINGMA_MOCK_DELAY_SECONDS"] = "0"
os.environ["AI_LINGMA_LLM_MODEL"] = "mock"
os.environ["AI_LINGMA_LLM_BASE_URL"] = ""
os.environ["AI_LINGMA_LLM_API_KEY"] = ""
os.environ["AI_LINGMA_COMMAND_MODE"] = "shell"
os.environ["AI_LINGMA_EVAL_VISION_PROVIDER"] = "disabled"

import pytest
from fastapi.testclient import TestClient

from app.core.database import SessionLocal, init_db
from app.main import app
from app.services.seed import ensure_admin, seed_templates


@pytest.fixture(scope="session", autouse=True)
def seed():
    init_db()
    with SessionLocal() as db:
        ensure_admin(db)
        seed_templates(db)
    yield


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def admin_headers(client):
    resp = client.post(
        "/api/auth/login", json={"username": "admin", "password": "admin123"}
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def user_headers(client, seed):
    with SessionLocal() as db:
        from app.core.security import hash_password
        from app.models.user import User

        alice = db.query(User).filter(User.username == "alice").first()
        if alice is None:
            alice = User(
                username="alice",
                password_hash=hash_password("alice123"),
                email="alice@example.com",
                role="user",
                quota=10,
            )
            db.add(alice)
        else:
            # 其他用例可能改过密码，这里保持 fixture 幂等
            alice.password_hash = hash_password("alice123")
        db.commit()
    resp = client.post(
        "/api/auth/login", json={"username": "alice", "password": "alice123"}
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
