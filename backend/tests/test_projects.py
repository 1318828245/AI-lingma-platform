def test_list_templates(client, admin_headers):
    resp = client.get("/api/templates", headers=admin_headers)
    assert resp.status_code == 200
    names = [t["name"] for t in resp.json()]
    assert "个人名片页" in names
    assert "任务看板" in names
    assert "管理后台模板" in names
    assert all(t["file_count"] > 0 for t in resp.json())


def test_create_project_from_template(client, admin_headers):
    resp = client.post(
        "/api/projects",
        headers=admin_headers,
        json={
            "name": "我的名片",
            "description": "测试项目",
            "template": "个人名片页",
            "tech_stack": "html",
        },
    )
    assert resp.status_code == 201, resp.text
    project = resp.json()
    assert project["template"] == "个人名片页"
    assert project["tech_stack"] == "html"
    assert len(project["slug"]) > 8

    # 工作区已落盘
    from app.core.config import get_settings

    ws = get_settings().workspace_dir / str(project["id"])
    assert (ws / "index.html").exists()
    assert (ws / "style.css").exists()
    assert (ws / "script.js").exists()


def test_create_blank_project(client, admin_headers):
    resp = client.post(
        "/api/projects",
        headers=admin_headers,
        json={"name": "空白实验", "template": "blank", "tech_stack": "vue3"},
    )
    assert resp.status_code == 201
    assert resp.json()["tech_stack"] == "vue3"


def test_create_project_with_unknown_template(client, admin_headers):
    resp = client.post(
        "/api/projects",
        headers=admin_headers,
        json={"name": "坏模板", "template": "不存在"},
    )
    assert resp.status_code == 400


def test_project_crud(client, admin_headers):
    created = client.post(
        "/api/projects",
        headers=admin_headers,
        json={"name": "看板项目", "template": "任务看板"},
    ).json()
    pid = created["id"]

    listed = client.get("/api/projects", headers=admin_headers).json()
    assert any(p["id"] == pid for p in listed)

    got = client.get(f"/api/projects/{pid}", headers=admin_headers)
    assert got.status_code == 200
    assert got.json()["name"] == "看板项目"

    patched = client.patch(
        f"/api/projects/{pid}",
        headers=admin_headers,
        json={"description": "改名后的描述"},
    )
    assert patched.status_code == 200
    assert patched.json()["description"] == "改名后的描述"

    deleted = client.delete(f"/api/projects/{pid}", headers=admin_headers)
    assert deleted.status_code == 204
    assert client.get(f"/api/projects/{pid}", headers=admin_headers).status_code == 404


def test_project_ownership_isolation(client, admin_headers, user_headers):
    created = client.post(
        "/api/projects",
        headers=admin_headers,
        json={"name": "管理员的私密项目"},
    ).json()
    resp = client.get(f"/api/projects/{created['id']}", headers=user_headers)
    assert resp.status_code == 403
