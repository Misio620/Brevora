from pydantic import BaseModel, Field


class LoginCodeExchange(BaseModel):
    # secrets.token_urlsafe(32) is 43 characters; the cap only rejects junk input
    code: str = Field(min_length=1, max_length=100)


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


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
