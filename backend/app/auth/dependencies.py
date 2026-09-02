import logging
from typing import Optional, List, Callable
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError

from app.db.session import get_db
from app.db.models import Officer
from app.auth.security import decode_access_token
from app.auth.schemas import TokenPayload

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login",
    description="JWT Bearer token obtained from /api/auth/login"
)


def get_current_officer(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Officer:
    """
    Extracts and validates the JWT Bearer token, retrieving the authenticated Officer record.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        username: Optional[str] = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        raise credentials_exception

    officer = db.query(Officer).filter(Officer.username == username).first()
    if officer is None:
        raise credentials_exception

    return officer


def get_current_active_officer(
    current_officer: Officer = Depends(get_current_officer)
) -> Officer:
    """
    Ensures that the authenticated officer's account is active.
    """
    if not current_officer.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive officer account. Please contact administrator."
        )
    return current_officer


def require_roles(allowed_roles: List[str]) -> Callable:
    """
    Dependency factory ensuring the authenticated officer has one of the allowed roles.
    """
    def role_checker(
        current_officer: Officer = Depends(get_current_active_officer)
    ) -> Officer:
        if current_officer.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: requires one of roles {allowed_roles}"
            )
        return current_officer
    return role_checker


require_admin = require_roles(["admin"])


oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login",
    auto_error=False,
    description="Optional JWT Bearer token"
)


def get_optional_current_officer(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db)
) -> Optional[Officer]:
    """
    Returns the authenticated Officer if a valid Bearer token is provided, or None if anonymous.
    """
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        username: Optional[str] = payload.get("sub")
        if username is None:
            return None
        return db.query(Officer).filter(Officer.username == username, Officer.is_active == True).first()
    except Exception:
        return None

