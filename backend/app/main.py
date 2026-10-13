from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.data_integration import router as data_integration_router
from app.api.faculty_portal import router as faculty_portal_router
from app.api.portals import router as portals_router
from app.api.principal_portal import router as principal_portal_router
from app.api.student_portal import router as student_portal_router
from app.core.config import settings

app = FastAPI(title="Student Success Platform API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth_router)
app.include_router(portals_router)
app.include_router(student_portal_router)
app.include_router(faculty_portal_router)
app.include_router(principal_portal_router)
app.include_router(data_integration_router)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
