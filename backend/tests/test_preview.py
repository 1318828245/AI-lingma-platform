import asyncio
from pathlib import Path
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


def test_preview_accepts_cookie_for_static_assets(client, admin_headers):
    project = _create_project(
        client, admin_headers, "Cookie预览", template="个人名片页", tech_stack="html"
    )
    token = admin_headers["Authorization"].split(" ")[1]
    # iframe 静态资源不会带 query token，依赖 path=/preview 的 Cookie
    resp = client.get(
        f"/preview/{project['id']}/style.css", cookies={"preview_token": token}
    )
    assert resp.status_code == 200
    assert "body" in resp.text


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


def test_screenshot_requires_auth(client):
    resp = client.get("/api/projects/1/screenshot")
    assert resp.status_code == 401


def test_screenshot_not_generated(client, admin_headers):
    project = _create_project(
        client, admin_headers, "截图未生成", template="任务看板", tech_stack="vue3"
    )
    resp = client.get(
        f"/api/projects/{project['id']}/screenshot", headers=admin_headers
    )
    assert resp.status_code == 404


def test_screenshot_generated_with_mock_capture(client, admin_headers, monkeypatch):
    project = _create_project(
        client, admin_headers, "截图成功", template="个人名片页", tech_stack="html"
    )

    async def fake_capture(url, output, timeout=None):
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"\x89PNG\r\n\x1a\nfakepng")
        return True

    monkeypatch.setattr("app.api.preview.capture_screenshot", fake_capture)
    resp = client.get(
        f"/api/projects/{project['id']}/screenshot", headers=admin_headers
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"


def test_screenshot_fallback_when_capture_fails(client, admin_headers, monkeypatch):
    project = _create_project(
        client, admin_headers, "截图失败", template="个人名片页", tech_stack="html"
    )

    async def fake_capture(url, output, timeout=None):
        return False

    monkeypatch.setattr("app.api.preview.capture_screenshot", fake_capture)
    resp = client.get(
        f"/api/projects/{project['id']}/screenshot", headers=admin_headers
    )
    assert resp.status_code == 404


def test_screenshot_uses_sync_process_when_async_subprocess_unavailable(
    tmp_path, monkeypatch
):
    import app.services.screenshot as screenshot

    monkeypatch.setattr(screenshot, "find_browser", lambda: "browser.exe")

    async def unsupported(*args, **kwargs):
        raise NotImplementedError

    def fake_run(command, **kwargs):
        output_arg = next(item for item in command if str(item).startswith("--screenshot="))
        output = Path(str(output_arg).split("=", 1)[1])
        output.write_bytes(b"\x89PNG\r\n\x1a\nimage")
        return type("Completed", (), {"returncode": 0})()

    monkeypatch.setattr(screenshot.asyncio, "create_subprocess_exec", unsupported)
    monkeypatch.setattr(screenshot.subprocess, "run", fake_run)
    output = tmp_path / "thumb.png"
    assert asyncio.run(screenshot.capture_screenshot("http://test", output))
    assert output.exists()
