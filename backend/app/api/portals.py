from fastapi import APIRouter, Depends
from typing import Annotated

from app.api.dependencies import require_roles
from app.models import User
from app.schemas.auth import PortalResponse, Role
from app.services.auth_service import public_user

router = APIRouter(prefix="/portals", tags=["portals"])

PORTAL_MESSAGES: dict[str, str] = {
    "student": "Your personal student portal is ready.",
    "faculty": "Your faculty portal is ready.",
    "dean": "Your department portal is ready.",
    "principal": "Your institution portal is ready.",
}


def _portal_response(role: Role, user: User) -> PortalResponse:
    return PortalResponse(portal=role, message=PORTAL_MESSAGES[role], user=public_user(user))


@router.get("/student", response_model=PortalResponse)
def student_portal(
    user: Annotated[User, Depends(require_roles("student"))],
) -> PortalResponse:
    return _portal_response("student", user)


@router.get("/faculty", response_model=PortalResponse)
def faculty_portal(
    user: Annotated[User, Depends(require_roles("faculty"))],
) -> PortalResponse:
    return _portal_response("faculty", user)


@router.get("/dean", response_model=PortalResponse)
def dean_portal(
    user: Annotated[User, Depends(require_roles("dean"))],
) -> PortalResponse:
    return _portal_response("dean", user)


@router.get("/principal", response_model=PortalResponse)
def principal_portal(
    user: Annotated[User, Depends(require_roles("principal"))],
) -> PortalResponse:
    return _portal_response("principal", user)
