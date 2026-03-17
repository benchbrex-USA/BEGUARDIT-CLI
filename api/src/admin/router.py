# Admin domain — router
# Endpoints: GET /users, PATCH /users/:id, GET /audit-log
from fastapi import APIRouter
router = APIRouter(tags=["admin"])
