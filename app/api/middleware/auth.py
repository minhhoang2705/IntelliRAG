"""
API authentication middleware using Bearer token.

Provides API key authentication via Authorization: Bearer header.
When no API_KEY environment variable is set, operates in dev mode (no auth required).
"""

import os
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# HTTP Bearer security scheme (auto_error=False allows optional auth)
security = HTTPBearer(auto_error=False)


def get_api_key() -> Optional[str]:
    """
    Load API key from environment variable.

    Returns:
        Optional[str]: API key if configured, None otherwise
    """
    return os.getenv("API_KEY")


async def verify_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> str:
    """
    Verify API key from Authorization: Bearer header.

    This dependency can be added to any FastAPI endpoint using:
        @app.get("/protected", dependencies=[Depends(verify_api_key)])

    Args:
        credentials: HTTP Bearer credentials from request header

    Returns:
        str: Valid API key or "dev-mode"

    Raises:
        HTTPException: 401 if missing/invalid when auth is enabled
    """
    api_key = get_api_key()

    # Dev mode: no key configured = allow all
    if not api_key:
        return "dev-mode"

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Use 'Authorization: Bearer YOUR_KEY'",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if credentials.credentials != api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return credentials.credentials
