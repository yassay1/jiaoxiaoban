"""API dependencies for identity extraction and permission boundaries.

Phase 5 / D1: extracts external_user_id from X-User-Id header (standard for
API gateways/auth proxies). Falls back to query param for local dev.
Documents the limitation that this is NOT production auth.
"""

import logging
from typing import Annotated

from fastapi import Depends, Header, Query, HTTPException

logger = logging.getLogger(__name__)

# Default identity for development/demo without auth infrastructure.
# In production, this should ALWAYS come from a verified token/header.
_DEMO_USER_ID = "demo_user"
_DEMO_USER_NAME = "演示同学"


def extract_user_identity(
    x_user_id: Annotated[str | None, Header(description="User identity from auth proxy")] = None,
    external_user_id: Annotated[str | None, Query(description="User ID (dev fallback)")] = None,
) -> tuple[str, str]:
    """Extract user identity from header (preferred) or query param (dev fallback).

    Phase 5 D1: header-based identity is the standard pattern for API gateways.
    Query param fallback exists only for local development convenience.

    Returns (external_user_id, display_name).
    """
    uid = x_user_id or external_user_id or _DEMO_USER_ID
    # Normalize: trim and reject empty strings
    uid = uid.strip() if uid else _DEMO_USER_ID
    if not uid:
        raise HTTPException(status_code=401, detail="Missing user identity")

    # Display name can come from a separate header in production
    name = _DEMO_USER_NAME
    return uid, name


# FastAPI dependency annotation
UserIdentity = Annotated[tuple[str, str], Depends(extract_user_identity)]


def get_user_id(identity: UserIdentity) -> str:
    """Convenience: extract just the user ID."""
    return identity[0]


def get_user_name(identity: UserIdentity) -> str:
    """Convenience: extract just the user name."""
    return identity[1]
