from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class OrganizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organization_id: str
    name: str
    slug: str
    is_active: bool
    created_at: datetime


class MemberAddRequest(BaseModel):
    email: EmailStr
    role: str = Field(default="viewer", min_length=1, max_length=32)


class RoleUpdateRequest(BaseModel):
    role: str = Field(min_length=1, max_length=32)


class MemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    member_id: str
    organization_id: str
    user_id: str
    role: str
    created_at: datetime
