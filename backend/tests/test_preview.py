from urllib.parse import quote


def _create_project(client, headers, name, template="blank", tech_stack="html"):
    resp = client.post(
        "/api/projects",
        headers=headers,
        json={"name": name, "template": template, "tech_stack": tech_stack},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_preview_status_and_static_serve(client, admin_headers):
    project = _create_project(
        client, admin_headers, "预览名片", template="个人名片页", tech_stack="html"
    )
    status = client.get(
        f"/api/projects/{project['id']}/preview/status", headers=admin_headers
    )
    assert status.status_code == 200
    assert status.json()["status"] == "ready"
    assert status.json()["mode"] == "static"

    token = admin_headers["Authorization"].split(" ")[1]
    resp = client.get(
        f"/preview/{project['id']}/index.html?token={token}"
    )
    assert resp.status_code == 200
    assert "<!DOCTYPE html>" in resp.text

    css = client.get(f"/preview/{project['id']}/style.css?token={token}")
    assert css.status_code == 200
    assert "body" in css.text


def test_preview_requires_valid_token(client, admin_headers, user_headers):
    project = _create_project(
        client, admin_headers, "预览权限", template="个人名片页", tech_stack="html"
    )
    resp = client.get(f"/preview/{project['id']}/index.html?token=bad")
    assert resp.status_code == 401

    other_token = user_headers["Authorization"].split(" ")[1]
    resp = client.get(f"/preview/{project['id']}/index.html?token={other_token}")
    assert resp.status_code == 403

    resp = client.get(f"/preview/{project['id']}/index.html")
    assert resp.status_code in (401, 422)


def test_preview_path_traversal_blocked(client, admin_headers):
    project = _create_project(
        client, admin_headers, "预览穿越", template="个人名片页", tech_stack="html"
    )
    token = admin_headers["Authorization"].split(" ")[1]
    # httpx/Starlette 会在路由层规范化 ..，因此直接单测服务端路径校验
    import pytest
    from fastapi import HTTPException

    from app.api.preview import preview_file
    from app.core.database import SessionLocal

    with pytest.raises(HTTPException) as exc:
        with SessionLocal() as db:
            preview_file(project["id"], "../app/main.py", token=token, db=db)
    assert exc.value.status_code == 400


def test_preview_source_project_not_generated(client, admin_headers):
    project = _create_project(
        client, admin_headers, "未构建Vue", template="任务看板", tech_stack="vue3"
    )
    status = client.get(
        f"/api/projects/{project['id']}/preview/status", headers=admin_headers
    ).json()
    assert status["status"] == "not_generated"
    assert status["mode"] == "source"


def test_project_files_list(client, admin_headers):
    project = _create_project(
        client, admin_headers, "文件树", template="个人名片页", tech_stack="html"
    )
    resp = client.get(f"/api/projects/{project['id']}/files", headers=admin_headers)
    assert resp.status_code == 200
    paths = [f["path"] for f in resp.json()]
    assert "index.html" in paths
    assert "style.css" in paths


def test_sse_accepts_query_token(client, admin_headers):
    project = _create_project(client, admin_headers, "SSE令牌")
    resp = client.post(
        f"/api/projects/{project['id']}/generations",
        headers=admin_headers,
        json={"requirement": "慢速生成页面，验证 SSE query token"},
    )
    gen_id = resp.json()["id"]
    token = admin_headers["Authorization"].split(" ")[1]
    events = []
    with client.stream(
        "GET", f"/api/generations/{gen_id}/events?token={token}"
    ) as stream:
        for line in stream.iter_lines():
            if line.startswith("data: "):
                import json

                events.append(json.loads(line[6:]))
    assert any(e["type"] == "completed" for e in events)
