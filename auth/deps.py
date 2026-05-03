"""FastAPI dependencies for authentication and authorization."""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

from auth.utils import decode_token
from auth.redis_blocklist import is_blocked
from errors.exceptions import UnauthorizedException, ForbiddenException

security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> dict:
    """Validate JWT access token and return payload."""
    token = credentials.credentials
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise UnauthorizedException(detail="Token has expired")
    except jwt.InvalidTokenError:
        raise UnauthorizedException(detail="Invalid token")

    if payload.get("type") != "access":
        raise UnauthorizedException(detail="Invalid token type")

    # Check Redis blocklist
    jti = payload.get("jti") or token[-16:]
    if await is_blocked(jti):
        raise UnauthorizedException(detail="Token has been revoked")

    return payload


def require_role(*allowed_roles: str):
    """Return a dependency that checks the current user has one of the allowed roles."""

    async def _check_role(
        current_user: Annotated[dict, Depends(get_current_user)],
    ) -> dict:
        user_role = current_user.get("role", "user")
        if user_role not in allowed_roles:
            raise ForbiddenException(
                detail=f"Role '{user_role}' is not authorized. Required: {', '.join(allowed_roles)}"
            )
        return current_user

    return _check_role
