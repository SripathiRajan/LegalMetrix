import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Officer
from app.auth.schemas import OfficerRegister, OfficerLogin, OfficerProfile, Token
from app.auth.security import get_password_hash, verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from app.auth.dependencies import get_current_active_officer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication & Officer Management"])


@router.post(
    "/register",
    response_model=OfficerProfile,
    status_code=status.HTTP_201_CREATED,
    summary="Register New Inspector / Officer Account",
    description="Creates a new officer credentials record with hashed password and role assignment."
)
def register_officer(
    payload: OfficerRegister,
    db: Session = Depends(get_db)
):
    # Check if username already taken
    existing_user = db.query(Officer).filter(Officer.username == payload.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{payload.username}' is already registered."
        )

    # Check email uniqueness if email provided
    if payload.email:
        existing_email = db.query(Officer).filter(Officer.email == payload.email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email '{payload.email}' is already in use."
            )

    hashed_pwd = get_password_hash(payload.password)

    officer = Officer(
        username=payload.username,
        email=payload.email,
        hashed_password=hashed_pwd,
        badge_number=payload.badge_number,
        role=payload.role.lower(),
        is_active=True
    )

    db.add(officer)
    db.commit()
    db.refresh(officer)
    logger.info(f"Registered new officer #{officer.id} '{officer.username}' (role={officer.role})")
    return officer


@router.post(
    "/login",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="Officer Login & JWT Token Generation",
    description="Authenticates officer credentials and issues a signed JWT Bearer access token."
)
def login_officer(
    payload: OfficerLogin,
    db: Session = Depends(get_db)
):
    officer = db.query(Officer).filter(Officer.username == payload.username).first()
    if not officer or not officer.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(payload.password, officer.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not officer.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Officer account is currently inactive."
        )

    # Generate JWT
    token_claims = {
        "sub": officer.username,
        "officer_id": officer.id,
        "role": officer.role
    }
    access_token = create_access_token(data=token_claims)

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in_minutes=ACCESS_TOKEN_EXPIRE_MINUTES,
        officer=OfficerProfile.model_validate(officer)
    )


@router.get(
    "/me",
    response_model=OfficerProfile,
    status_code=status.HTTP_200_OK,
    summary="Get Current Authenticated Officer Profile",
    description="Returns the profile details of the currently authenticated officer."
)
def get_my_profile(
    current_officer: Officer = Depends(get_current_active_officer)
):
    return current_officer
