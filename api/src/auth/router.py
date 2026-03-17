# Auth domain — router
# Endpoints: POST /register, POST /login, POST /logout, GET /me, POST /switch-tenant
from fastapi import APIRouter

router = APIRouter(tags=["auth"])
