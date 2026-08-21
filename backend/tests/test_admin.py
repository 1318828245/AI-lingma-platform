def test_non_admin_forbidden(client, user_headers):
    resp = client.get("/api/admin/users", headers=user_headers)
    assert resp.status_code == 403


def test_admin_overview_returns_operational_sections(client, admin_headers):
    response = client.get("/api/admin/overview", headers=admin_headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert set(data) == {"metrics", "projects", "users", "tasks", "deployments", "audits"}
    assert {"projects", "users", "running_tasks", "online_sites"} <= set(data["metrics"])


def test_admin_observability_returns_health_metrics_and_timeline(client, admin_headers):
    response = client.get("/api/admin/observability", headers=admin_headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert {"health", "metrics", "alerts", "timeline"} == set(data)
    assert any(item["name"] == "数据库" for item in data["health"])


def test_admin_lists_users(client, admin_headers, user_headers):
    resp = client.get("/api/admin/users", headers=admin_headers)
    assert resp.status_code == 200
    usernames = [u["username"] for u in resp.json()]
    assert "admin" in usernames
    assert "alice" in usernames


def test_admin_updates_quota_and_resets_password(client, admin_headers, user_headers):
    users = client.get("/api/admin/users", headers=admin_headers).json()
    alice = next(u for u in users if u["username"] == "alice")

    resp = client.patch(
        f"/api/admin/users/{alice['id']}",
        headers=admin_headers,
        json={"quota": 50, "role": "user"},
    )
    assert resp.status_code == 200
    assert resp.json()["quota"] == 50

    overview = client.get("/api/admin/overview", headers=admin_headers).json()
    assert any(item["action"] == "user.updated" and item["target_id"] == str(alice["id"]) for item in overview["audits"])

    resp = client.post(
        f"/api/admin/users/{alice['id']}/reset-password",
        headers=admin_headers,
        json={"new_password": "newpass123"},
    )
    assert resp.status_code == 200

    login = client.post(
        "/api/auth/login", json={"username": "alice", "password": "newpass123"}
    )
    assert login.status_code == 200


def test_admin_cannot_demote_self(client, admin_headers):
    me = client.get("/api/users/me", headers=admin_headers).json()
    resp = client.patch(
        f"/api/admin/users/{me['id']}",
        headers=admin_headers,
        json={"role": "user"},
    )
    assert resp.status_code == 400


def test_admin_settings_roundtrip(client, admin_headers):
    resp = client.get("/api/admin/settings", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["register_enabled"] is False

    resp = client.put(
        "/api/admin/settings",
        headers=admin_headers,
        json={"register_enabled": True, "default_user_quota": 30},
    )
    assert resp.status_code == 200
    assert resp.json()["register_enabled"] is True
    assert resp.json()["default_user_quota"] == 30

    # 打开注册后可以注册
    resp = client.post(
        "/api/auth/register",
        json={"username": "bob", "password": "bob12345"},
    )
    assert resp.status_code == 201

    # 恢复默认，避免影响依赖默认值的其他用例
    resp = client.put(
        "/api/admin/settings",
        headers=admin_headers,
        json={"register_enabled": False},
    )
    assert resp.status_code == 200
    assert resp.json()["register_enabled"] is False
    resp = client.post(
        "/api/auth/register",
        json={"username": "carol", "password": "carol12345"},
    )
    assert resp.status_code == 403
