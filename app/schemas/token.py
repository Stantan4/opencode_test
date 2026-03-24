"""
Token Schemas
"""
from pydantic import BaseModel


class Token(BaseModel):
    """Token response schema"""
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Token payload schema"""
    sub: str  # user_id
    exp: int
    type: str  # access or refresh
