from app.core.database import SessionLocal
from app.services.project import write_project_file
from app.services.version import snapshot_project


def test_project_version_list_diff_and_rollback(client, admin_headers):
    created = client.post(
        "/api/projects",
        headers=admin_headers,
        json={"name": "版本测试项目", "template": "blank", "tech_stack": "html"},
    ).json()
    project_id = created["id"]

    with SessionLocal() as db:
        write_project_file(db, project_id, "index.html", "<h1>第一版</h1>")
        version = snapshot_project(
            db, project_id, source_type="test", summary="第一版快照"
        )
        db.commit()
        version_id = version.id
        storage_paths = [metadata["storage_path"] for metadata in version.snapshot_manifest_json.values()]
        assert storage_paths
        storage_parts = storage_paths[0].split("/")
        assert storage_parts[0] == created["slug"]
        assert all(part.isascii() for part in storage_parts[:2])
        assert storage_parts[1].count("-") == 6
        write_project_file(db, project_id, "index.html", "<h1>第二版</h1>")
        write_project_file(db, project_id, "extra.txt", "临时文件")
        db.commit()

    versions = client.get(f"/api/projects/{project_id}/versions", headers=admin_headers)
    assert versions.status_code == 200, versions.text
    assert versions.json()[0]["file_count"] == 1

    diff = client.get(
        f"/api/projects/{project_id}/versions/{version_id}/diff",
        headers=admin_headers,
    )
    assert diff.status_code == 200, diff.text
    changes = {item["path"]: item for item in diff.json()["files"]}
    assert changes["index.html"]["status"] == "modified"
    assert changes["extra.txt"]["status"] == "deleted"

    rollback = client.post(
        f"/api/projects/{project_id}/versions/{version_id}/rollback",
        headers=admin_headers,
    )
    assert rollback.status_code == 200, rollback.text
    assert rollback.json()["restored_files"] == ["index.html"]

    with SessionLocal() as db:
        from app.core.config import get_settings

        from app.services.project import project_workspace

        workspace = project_workspace(project_id)
        assert (workspace / "index.html").read_text(encoding="utf-8") == "<h1>第一版</h1>"
        assert not (workspace / "extra.txt").exists()


def test_project_version_undo_restores_previous_snapshot(client, admin_headers):
    created = client.post(
        "/api/projects",
        headers=admin_headers,
        json={"name": "Undo version project", "template": "blank", "tech_stack": "html"},
    ).json()
    project_id = created["id"]

    with SessionLocal() as db:
        write_project_file(db, project_id, "index.html", "<h1>before</h1>")
        snapshot_project(db, project_id, source_type="test", summary="before")
        db.commit()
        write_project_file(db, project_id, "index.html", "<h1>after</h1>")
        changed = snapshot_project(db, project_id, source_type="modification", summary="after")
        db.commit()
        changed_id = changed.id

    response = client.post(
        f"/api/projects/{project_id}/versions/{changed_id}/undo",
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["version"]["summary"] == "before"

    with SessionLocal() as db:
        from app.services.project import project_workspace

        workspace = project_workspace(project_id)
        assert (workspace / "index.html").read_text(encoding="utf-8") == "<h1>before</h1>"


def test_project_version_excludes_dependency_and_build_directories(client, admin_headers):
    created = client.post(
        "/api/projects",
        headers=admin_headers,
        json={"name": "忽略依赖目录", "template": "blank", "tech_stack": "vue3"},
    ).json()

    with SessionLocal() as db:
        project_id = created["id"]
        write_project_file(db, project_id, "index.html", "<div />")
        write_project_file(db, project_id, "node_modules/.bin/vite", "binary")
        write_project_file(db, project_id, "dist/index.html", "built")
        version = snapshot_project(db, project_id, source_type="test", summary="忽略生成目录")
        db.commit()

    assert set(version.snapshot_manifest_json) == {"index.html"}
