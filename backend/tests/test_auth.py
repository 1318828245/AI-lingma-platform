def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_login_success(client, admin_headers):
    resp = client.post(
        "/api/auth/login", json={"username": "admin", "password": "admin123"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["user"]["username"] == "admin"
    assert body["user"]["role"] == "admin"


def test_login_wrong_password(client):
    resp = client.post(
        "/api/auth/login", json={"username": "admin", "password": "wrong"}
    )
    assert resp.status_code == 401


def test_register_disabled_by_default(client):
    resp = client.post(
        "/api/auth/register",
        json={"username": "newbie", "password": "newbie123"},
    )
    assert resp.status_code == 403


def test_me(client, admin_headers):
    resp = client.get("/api/users/me", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == "admin"


def test_me_requires_token(client):
    resp = client.get("/api/users/me")
    assert resp.status_code in (401, 403)


def test_refresh(client):
    login = client.post(
        "/api/auth/login", json={"username": "admin", "password": "admin123"}
    ).json()
    resp = client.post("/api/auth/refresh", json={"refresh_token": login["refresh_token"]})
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_logout(client, admin_headers):
    resp = client.post("/api/auth/logout", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
