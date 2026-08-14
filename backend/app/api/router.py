from fastapi import APIRouter

from app.api import admin, auth, projects, sessions, templates, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(projects.router)
api_router.include_router(sessions.router)
api_router.include_router(templates.router)
api_router.include_router(admin.router)
