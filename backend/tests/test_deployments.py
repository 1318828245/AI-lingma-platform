from app.core.database import SessionLocal
from app.services.project import write_project_file
from app.services.version import snapshot_project


def _project_with_build(client, headers):
    project = client.post(
        "/api/projects",
        headers=headers,
        json={"name": "Deployment demo", "template": "blank", "tech_stack": "html"},
    ).json()
    with SessionLocal() as db:
        write_project_file(db, project["id"], "dist/index.html", "<h1>Published delivery</h1>")
        write_project_file(db, project["id"], "dist/assets/app.js", "console.log('ready')")
        version = snapshot_project(db, project["id"], source_type="test", summary="ready to publish")
        db.commit()
    return project, version.id


def test_publish_snapshot_and_serve_public_site(client, admin_headers):
    project, version_id = _project_with_build(client, admin_headers)
    response = client.post(
        f"/api/projects/{project['id']}/deployments",
        headers=admin_headers,
        json={"version_id": version_id},
    )
    assert response.status_code == 200, response.text
    deployment = response.json()
    assert deployment["status"] == "ready"
    assert deployment["url"].endswith(f"/published/{deployment['slug']}/")
    assert deployment["is_active"] is True
    assert deployment["site_url"].endswith(f"/sites/{project['slug']}/")
    assert deployment["version"] == 1

    public_page = client.get(deployment["url"])
    assert public_page.status_code == 200
    assert "Published delivery" in public_page.text
    asset = client.get(f"/published/{deployment['slug']}/assets/app.js")
    assert asset.status_code == 200
    assert asset.headers["cache-control"] == "public, max-age=31536000, immutable"

    records = client.get(f"/api/projects/{project['id']}/deployments", headers=admin_headers)
    assert records.status_code == 200
    assert records.json()[0]["id"] == deployment["id"]


def test_publish_plain_html_multifile_project(client, admin_headers):
    project = client.post(
        "/api/projects",
        headers=admin_headers,
        json={"name": "Static delivery", "template": "blank", "tech_stack": "html"},
    ).json()
    with SessionLocal() as db:
        write_project_file(db, project["id"], "index.html", '<link rel="stylesheet" href="styles.css"><h1>Static delivery</h1>')
        write_project_file(db, project["id"], "styles.css", "h1 { color: green; }")
        snapshot_project(db, project["id"], source_type="test")
        db.commit()

    response = client.post(f"/api/projects/{project['id']}/deployments", headers=admin_headers, json={})
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "ready"
    page = client.get(response.json()["url"])
    assert page.status_code == 200
    assert "Static delivery" in page.text
    stylesheet = client.get(f"/published/{response.json()['slug']}/styles.css")
    assert stylesheet.status_code == 200


def test_switch_active_deployment_and_take_offline(client, admin_headers):
    project, first_version_id = _project_with_build(client, admin_headers)
    first = client.post(
        f"/api/projects/{project['id']}/deployments", headers=admin_headers, json={"version_id": first_version_id}
    ).json()
    with SessionLocal() as db:
        write_project_file(db, project["id"], "dist/index.html", "<h1>Second delivery</h1>")
        second_version = snapshot_project(db, project["id"], source_type="test", summary="second")
        db.commit()
        second_version_id = second_version.id
    second = client.post(
        f"/api/projects/{project['id']}/deployments", headers=admin_headers, json={"version_id": second_version_id}
    ).json()
    assert second["is_active"] is True
    assert "Second delivery" in client.get(second["site_url"]).text

    switched = client.post(
        f"/api/projects/{project['id']}/deployments/{first['id']}/activate", headers=admin_headers
    )
    assert switched.status_code == 200, switched.text
    assert switched.json()["is_active"] is True
    assert "Published delivery" in client.get(switched.json()["site_url"]).text

    offline = client.post(
        f"/api/projects/{project['id']}/deployments/{first['id']}/offline", headers=admin_headers
    )
    assert offline.status_code == 200, offline.text
    assert offline.json()["status"] == "offline"
    assert offline.json()["is_active"] is False
    assert client.get(first["url"]).status_code == 404
    assert client.get(switched.json()["site_url"]).status_code == 404

    restored = client.post(
        f"/api/projects/{project['id']}/deployments/{first['id']}/activate", headers=admin_headers
    )
    assert restored.status_code == 200, restored.text
    assert restored.json()["status"] == "ready"
    assert restored.json()["is_active"] is True
    assert "Published delivery" in client.get(restored.json()["site_url"]).text
