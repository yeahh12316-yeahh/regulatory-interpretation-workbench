from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.api.organization_schemas import MemberAddRequest, MemberRead, OrganizationRead, RoleUpdateRequest
from backend.app.db.models import Organization, OrganizationMember, User
from backend.app.db.session import get_db
from backend.app.security import AuthContext, CurrentContext, require_roles


router = APIRouter(prefix="/api/organizations", tags=["organizations"])
VALID_ROLES = {"viewer", "reviewer", "editor", "admin"}


@router.get("/current", response_model=OrganizationRead)
def current_organization(context: CurrentContext) -> Organization:
    return context.organization


@router.get("/current/members", response_model=list[MemberRead])
def list_members(context: CurrentContext, db: Session = Depends(get_db)) -> list[OrganizationMember]:
    return list(
        db.scalars(
            select(OrganizationMember)
            .where(OrganizationMember.organization_id == context.organization.organization_id)
            .order_by(OrganizationMember.created_at)
        )
    )


@router.post("/current/members", response_model=MemberRead, status_code=status.HTTP_201_CREATED)
def add_member(
    payload: MemberAddRequest,
    context: AuthContext = Depends(require_roles("owner", "admin")),
    db: Session = Depends(get_db),
) -> OrganizationMember:
    if payload.role not in VALID_ROLES:
        raise HTTPException(status_code=422, detail="unsupported organization role")
    user = db.scalar(select(User).where(User.email == payload.email.strip().lower()))
    if user is None:
        raise HTTPException(status_code=404, detail="user not found; user must register first")
    existing = db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == context.organization.organization_id,
            OrganizationMember.user_id == user.user_id,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="user is already a member")
    member = OrganizationMember(
        member_id=f"MEM_{uuid4().hex}",
        organization_id=context.organization.organization_id,
        user_id=user.user_id,
        role=payload.role,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.patch("/current/members/{member_id}", response_model=MemberRead)
def update_member_role(
    member_id: str,
    payload: RoleUpdateRequest,
    context: AuthContext = Depends(require_roles("owner", "admin")),
    db: Session = Depends(get_db),
) -> OrganizationMember:
    if payload.role not in VALID_ROLES:
        raise HTTPException(status_code=422, detail="unsupported organization role")
    member = db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.member_id == member_id,
            OrganizationMember.organization_id == context.organization.organization_id,
        )
    )
    if member is None:
        raise HTTPException(status_code=404, detail="member not found")
    if member.role == "owner" and payload.role != "owner":
        owner_count = db.scalar(
            select(func.count()).select_from(OrganizationMember).where(
                OrganizationMember.organization_id == context.organization.organization_id,
                OrganizationMember.role == "owner",
            )
        )
        if owner_count <= 1:
            raise HTTPException(status_code=409, detail="organization must retain an owner")
    member.role = payload.role
    db.commit()
    db.refresh(member)
    return member
