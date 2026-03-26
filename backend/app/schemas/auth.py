from pydantic import BaseModel


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str | None
    avatar_url: str | None

    model_config = {"from_attributes": True}

    @classmethod
    def from_user(cls, user):
        return cls(
            id=str(user.id),
            email=user.email,
            display_name=user.display_name,
            avatar_url=user.avatar_url,
        )


class LoginResponse(BaseModel):
    auth_url: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
