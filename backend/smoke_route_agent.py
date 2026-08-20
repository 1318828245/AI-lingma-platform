"""Real-model smoke test for Route Agent stack recommendations."""

from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.main import app
from app.services.project import project_workspace
from app.services.seed import ensure_admin, seed_templates


def create_project(client: TestClient, headers: dict, name: str, stack: str) -> dict:
    response = client.post(
        "/api/projects",
        headers=headers,
        json={"name": name, "template": "blank", "tech_stack": stack},
    )
    assert response.status_code == 201, response.text
    return response.json()


def route(client: TestClient, headers: dict, project_id: int, requirement: str) -> dict:
    response = client.post(
        f"/api/projects/{project_id}/stack-advice",
        headers=headers,
        json={"requirement": requirement},
    )
    assert response.status_code == 200, response.text
    return response.json()


def main() -> None:
    with TestClient(app) as client:
        with SessionLocal() as db:
            ensure_admin(db)
            seed_templates(db)
        login = client.post(
            "/api/auth/login", json={"username": "admin", "password": "admin123"}
        ).json()
        headers = {"Authorization": f"Bearer {login['access_token']}"}

        landing = create_project(client, headers, "Route Smoke Landing", "html")
        landing_advice = route(
            client, headers, landing["id"], "做一个展示个人介绍、作品和联系方式的单页名片"
        )
        assert landing_advice["recommended_stack"] == "html", landing_advice
        assert landing_advice["needs_confirmation"] is False, landing_advice

        dashboard = create_project(client, headers, "Route Smoke Dashboard", "html")
        dashboard_advice = route(
            client,
            headers,
            dashboard["id"],
            "做一个带登录、路由、任务筛选和分页编辑的后台管理仪表盘",
        )
        assert dashboard_advice["recommended_stack"] == "vue3", dashboard_advice
        assert dashboard_advice["needs_confirmation"] is True, dashboard_advice
        updated = client.patch(
            f"/api/projects/{dashboard['id']}",
            headers=headers,
            json={"tech_stack": "vue3"},
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["tech_stack"] == "vue3"
        assert project_workspace(dashboard["id"]).parent.name == "vue"

        keep_html = create_project(client, headers, "Route Smoke Keep Html", "html")
        keep_advice = route(
            client,
            headers,
            keep_html["id"],
            "做一个带登录、路由、任务筛选和分页编辑的后台管理仪表盘",
        )
        assert keep_advice["needs_confirmation"] is True, keep_advice
        unchanged = client.get(f"/api/projects/{keep_html['id']}", headers=headers).json()
        assert unchanged["tech_stack"] == "html"

        print("landing:", landing_advice)
        print("switch_to_vue:", dashboard_advice)
        print("keep_html:", keep_advice)


if __name__ == "__main__":
    main()
