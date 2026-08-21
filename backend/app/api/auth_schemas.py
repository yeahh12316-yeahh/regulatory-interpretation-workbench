from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=256)
    display_name: str = Field(min_length=1, max_length=128)
    organization_name: str = Field(min_length=1, max_length=255)
    organization_slug: str = Field(min_length=2, max_length=128, pattern=r"^[a-z0-9-]+$")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class SwitchOrganizationRequest(BaseModel):
    organization_id: str = Field(min_length=1, max_length=64)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    email: EmailStr
    display_name: str
    is_active: bool


class TokenRead(BaseModel):
    access_token: str
    token_type: str = "bearer"
    organization_id: str
    user: UserRead
