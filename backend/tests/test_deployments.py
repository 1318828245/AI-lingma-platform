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
