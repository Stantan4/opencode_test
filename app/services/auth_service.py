"""
Auth Service
"""
from datetime import timedelta
from typing import Optional

from app.core.config import settings
from app.core.security.jwt import create_access_token, create_refresh_token, decode_token
from app.core.security.password import verify_password


class AuthService:
    """Authentication service"""

    @staticmethod
    async def authenticate(username: str, password: str) -> Optional[dict]:
        """Authenticate user"""
        # Implementation to be added
        pass

    @staticmethod
    async def create_tokens(user_id: str) -> dict:
        """Create access and refresh tokens"""
        access_token = create_access_token(
            data={"sub": user_id},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        refresh_token = create_refresh_token(data={"sub": user_id})
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }

    @staticmethod
    async def verify_token(token: str) -> Optional[dict]:
        """Verify and decode token"""
        return decode_token(token)
