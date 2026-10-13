"""Principal portal endpoints.

Everything under /principal is guarded by the principal role. The routes
here only return aggregate, institution-wide data. No student identifiers
are exposed.
"""

from fastapi import APIRouter, Depends

from app.api.dependencies import AuthenticatedUser, DatabaseSession, require_roles
from app.schemas.principal_portal import PrincipalDashboard
from app.services.principal_portal import get_principal_dashboard

router = APIRouter(
    prefix="/principal",
    tags=["principal portal"],
    dependencies=[Depends(require_roles("principal"))],
)


@router.get("/dashboard", response_model=PrincipalDashboard)
def principal_dashboard(
    user: AuthenticatedUser,
    db: DatabaseSession,
) -> PrincipalDashboard:
    return get_principal_dashboard(db, user)
