def test_project_creates_initial_session(client, admin_headers):
    project = client.post(
        "/api/projects",
        headers=admin_headers,
        json={"name": "会话测试项目"},
    ).json()
    sessions = client.get(
        "/api/sessions", headers=admin_headers, params={"project_id": project["id"]}
    ).json()
    assert len(sessions) == 1
    assert sessions[0]["project_id"] == project["id"]

    messages = client.get(
        f"/api/sessions/{sessions[0]['id']}/messages", headers=admin_headers
    )
    assert messages.status_code == 200
    assert messages.json() == []


def test_session_isolation(client, admin_headers, user_headers):
    project = client.post(
        "/api/projects",
        headers=admin_headers,
        json={"name": "隔离测试"},
    ).json()
    session_id = client.get(
        "/api/sessions", headers=admin_headers, params={"project_id": project["id"]}
    ).json()[0]["id"]
    resp = client.get(f"/api/sessions/{session_id}/messages", headers=user_headers)
    assert resp.status_code == 404
