from fastapi import FastAPI
from src.auth.router import router as auth_router
from src.tenants.router import router as tenants_router
from src.assessments.router import router as assessments_router
from src.reports.router import router as reports_router
from src.upload.router import router as upload_router
from src.admin.router import router as admin_router
from src.core.middleware import TenantScopingMiddleware, RequestLoggingMiddleware
from src.core.exceptions import register_exception_handlers
from fastapi.middleware.cors import CORSMiddleware


def create_app() -> FastAPI:
    app = FastAPI(title="BeGuardit API", version="1.0")

    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(CORSMiddleware, allow_origins=[], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
    app.add_middleware(TenantScopingMiddleware)

    app.include_router(auth_router, prefix="/api/v1/auth")
    app.include_router(tenants_router, prefix="/api/v1/tenants")
    app.include_router(assessments_router, prefix="/api/v1/assessments")
    app.include_router(reports_router, prefix="/api/v1/reports")
    app.include_router(upload_router, prefix="/api/v1/upload")
    app.include_router(admin_router, prefix="/api/v1/admin")

    register_exception_handlers(app)
    return app
