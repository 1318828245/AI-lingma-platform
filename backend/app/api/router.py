from fastapi import APIRouter

from app.api import admin, auth, deployments, generations, modifications, preview, projects, sessions, templates, users, versions

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(projects.router)
api_router.include_router(sessions.router)
api_router.include_router(generations.router)
api_router.include_router(templates.router)
api_router.include_router(admin.router)
api_router.include_router(preview.router)
api_router.include_router(versions.router)
api_router.include_router(modifications.router)
api_router.include_router(deployments.router)
