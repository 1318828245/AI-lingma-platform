import asyncio

from app.agents.tooling.contracts import ToolCall
from app.agents.tooling.policy import validate_tool_call
from app.core.database import SessionLocal
from app.models.asset import AssetJob, ProjectAsset
from app.services import assets


def _create_project(client, headers, name="素材任务"):
    response = client.post(
        "/api/projects",
        headers=headers,
        json={"name": name, "template": "blank", "tech_stack": "html"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_asset_collection_materializes_safe_icon_and_manifest(client, admin_headers, monkeypatch):
    project = _create_project(client, admin_headers)

    async def fake_icons(query, limit):
        return [
            assets.AssetCandidate(
                source="iconify-lucide",
                kind="icon",
                title="coffee",
                source_url="https://icon-sets.iconify.design/lucide/coffee/",
                license_name="ISC (Lucide icon set)",
                attribution="Lucide Icons via Iconify",
                external_url="https://api.iconify.design/lucide/coffee.svg",
                download_url="https://api.iconify.design/lucide/coffee.svg",
            )
        ]

    monkeypatch.setattr(assets, "_iconify_candidates", fake_icons)
    monkeypatch.setattr(assets, "_request_bytes", lambda _url: b'<svg viewBox="0 0 24 24"><path d="M1 1"/></svg>')

    events = []

    async def scenario():
        return await assets.collect_assets(
            project_id=project["id"], generation_id=None, session_id=None,
            kind="icon", query="coffee", usage_role="hero", emit=events.append,
        )

    result = asyncio.run(scenario())
    assert result["degraded"] is False
    assert result["selected"]["local_path"] == "assets/icons/coffee.svg"
    assert [event["type"] for event in events] == [
        "asset_collection_started", "asset_candidate", "asset_collection_completed"
    ]

    assets_api = client.get(f"/api/projects/{project['id']}/assets", headers=admin_headers)
    assert assets_api.status_code == 200
    assert assets_api.json()["assets"][0]["license"] == "ISC (Lucide icon set)"

    with SessionLocal() as db:
        assert db.query(AssetJob).filter(AssetJob.project_id == project["id"]).one().status == "succeeded"
        assert db.query(ProjectAsset).filter(ProjectAsset.project_id == project["id"]).one().local_path == "assets/icons/coffee.svg"


def test_asset_collection_degrades_without_a_configured_source(client, admin_headers, monkeypatch):
    project = _create_project(client, admin_headers, "素材降级")

    async def no_photos(query, orientation, limit):
        return []

    monkeypatch.setattr(assets, "_pexels_candidates", no_photos)
    result = asyncio.run(
        assets.collect_assets(
            project_id=project["id"], generation_id=None, session_id=None,
            kind="photo", query="warm office", usage_role="hero",
        )
    )
    assert result["degraded"] is True
    assert result["selected"] is None


def test_asset_collection_returns_source_error_instead_of_claiming_no_result(client, admin_headers, monkeypatch):
    project = _create_project(client, admin_headers, "素材来源错误")

    async def failing_icons(query, limit):
        raise OSError("network access denied")

    monkeypatch.setattr(assets, "_iconify_candidates", failing_icons)
    events = []
    result = asyncio.run(
        assets.collect_assets(
            project_id=project["id"], generation_id=None, session_id=None,
            kind="icon", query="calendar", emit=events.append,
        )
    )
    assert result["degraded"] is True
    assert "iconify-lucide: OSError: network access denied" in result["source_errors"]
    assert "素材来源暂不可用" in events[-1]["message"]


def test_asset_tool_is_generation_only_and_validates_arguments():
    valid = ToolCall("asset-1", "collect_assets", {"kind": "icon", "query": "calendar"})
    assert validate_tool_call("generation", valid) is None
    assert validate_tool_call("modification", valid)
    assert validate_tool_call("generation", ToolCall("asset-2", "collect_assets", {"kind": "url", "query": "x"}))
    assert validate_tool_call("generation", ToolCall("asset-3", "collect_assets", {"kind": "icon", "query": " "}))
