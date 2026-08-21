from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.api.auth_schemas import LoginRequest, RegisterRequest, SwitchOrganizationRequest, TokenRead, UserRead
from backend.app.api.organization_schemas import OrganizationRead
from backend.app.db.models import Organization, OrganizationMember, User
from backend.app.db.session import get_db
from backend.app.security import CurrentContext, create_access_token, hash_password, verify_password


router = APIRouter(prefix="/api/auth", tags=["auth"])


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


@router.post("/register", response_model=TokenRead, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenRead:
    email = payload.email.strip().lower()
    if db.scalar(select(User).where(User.email == email)) is not None:
        raise HTTPException(status_code=409, detail="email already registered")
    organization = Organization(
        organization_id=_id("ORG"),
        name=payload.organization_name.strip(),
        slug=f"{payload.organization_slug.strip().lower()}-{uuid4().hex[:8]}",
    )
    user = User(
        user_id=_id("USR"),
        email=email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name.strip(),
    )
    membership = OrganizationMember(
        member_id=_id("MEM"),
        organization=organization,
        user=user,
        role="owner",
    )
    db.add_all([organization, user, membership])
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="registration conflict") from exc
    return TokenRead(
        access_token=create_access_token(user.user_id, organization.organization_id),
        user=UserRead.model_validate(user),
        organization_id=organization.organization_id,
    )


@router.post("/login", response_model=TokenRead)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenRead:
    user = db.scalar(select(User).where(User.email == payload.email.strip().lower()))
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid email or password", headers={"WWW-Authenticate": "Bearer"})
    membership = db.scalar(
        select(OrganizationMember).where(OrganizationMember.user_id == user.user_id).order_by(OrganizationMember.created_at)
    )
    if membership is None:
        raise HTTPException(status_code=403, detail="user has no active organization membership")
    return TokenRead(
        access_token=create_access_token(user.user_id, membership.organization_id),
        user=UserRead.model_validate(user),
        organization_id=membership.organization_id,
    )


@router.get("/me", response_model=UserRead)
def me(context: CurrentContext) -> User:
    return context.user


@router.get("/organizations", response_model=list[OrganizationRead])
def my_organizations(context: CurrentContext, db: Session = Depends(get_db)) -> list[Organization]:
    return list(
        db.scalars(
            select(Organization)
            .join(OrganizationMember, OrganizationMember.organization_id == Organization.organization_id)
            .where(OrganizationMember.user_id == context.user.user_id, Organization.is_active.is_(True))
            .order_by(Organization.created_at)
        )
    )


@router.post("/switch-organization", response_model=TokenRead)
def switch_organization(
    payload: SwitchOrganizationRequest,
    context: CurrentContext,
    db: Session = Depends(get_db),
) -> TokenRead:
    membership = db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.user_id == context.user.user_id,
            OrganizationMember.organization_id == payload.organization_id,
        )
    )
    if membership is None:
        raise HTTPException(status_code=403, detail="user is not a member of this organization")
    organization = db.get(Organization, payload.organization_id)
    if organization is None or not organization.is_active:
        raise HTTPException(status_code=404, detail="organization not found")
    return TokenRead(
        access_token=create_access_token(context.user.user_id, organization.organization_id),
        user=UserRead.model_validate(context.user),
        organization_id=organization.organization_id,
    )
