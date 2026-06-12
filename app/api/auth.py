"""Auth router: register, login, refresh, logout, me."""

from fastapi import APIRouter, status

from app.core.deps import CurrentUser, DbSession
from app.models.tenant import Tenant
from app.schemas.auth import (
    AccessTokenResponse,
    AuthResponse,
    LoginRequest,
    MeResponse,
    RefreshRequest,
    RegisterRequest,
    TenantPublic,
    UserPublic,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _auth_response(result) -> AuthResponse:
    return AuthResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        user=UserPublic.model_validate(result.user),
        tenant=TenantPublic.model_validate(result.tenant),
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: DbSession) -> AuthResponse:
    result = auth_service.register(
        db,
        business_name=payload.business_name,
        owner_name=payload.owner_name,
        mobile=payload.mobile,
        email=payload.email,
        password=payload.password,
        gst_number=payload.gst_number,
    )
    return _auth_response(result)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: DbSession) -> AuthResponse:
    result = auth_service.authenticate(db, email=payload.email, password=payload.password)
    return _auth_response(result)


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh(payload: RefreshRequest, db: DbSession) -> AccessTokenResponse:
    access = auth_service.refresh_access_token(db, refresh_token=payload.refresh_token)
    return AccessTokenResponse(access_token=access)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(user: CurrentUser, db: DbSession) -> None:
    auth_service.logout(db, user=user)


@router.get("/me", response_model=MeResponse)
def me(user: CurrentUser, db: DbSession) -> MeResponse:
    tenant = db.get(Tenant, user.tenant_id)
    return MeResponse(
        user=UserPublic.model_validate(user),
        tenant=TenantPublic.model_validate(tenant),
    )
