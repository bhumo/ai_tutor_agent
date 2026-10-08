import os

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database.models import get_db, User
from auth.schemas import UserCreate, UserLogin, UserResponse, Token
from auth.service import AuthService
from auth.utils import create_access_token, verify_token
from datetime import timedelta

from utils.rate_limit import SlidingWindowRateLimiter

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()
auth_rate_limiter = SlidingWindowRateLimiter()
LOGIN_LIMIT = int(os.getenv("LOGIN_RATE_LIMIT", "5"))
REGISTER_LIMIT = int(os.getenv("REGISTER_RATE_LIMIT", "3"))
AUTH_WINDOW_SECONDS = int(os.getenv("AUTH_RATE_WINDOW_SECONDS", "900"))


def _client_ip(request: Request) -> str:
    # Do not trust X-Forwarded-For unless a trusted-proxy layer validates it.
    return request.client.host if request.client else "unknown"


def _enforce_auth_limit(key: str, limit: int) -> None:
    decision = auth_rate_limiter.check(key, limit, AUTH_WINDOW_SECONDS)
    if not decision.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts. Please try again later.",
            headers={"Retry-After": str(decision.retry_after)},
        )

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    token = credentials.credentials
    email = verify_token(token)
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = AuthService.get_user_by_email(db, email=email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return user

@router.post("/register", response_model=UserResponse)
async def register(request: Request, user_create: UserCreate, db: Session = Depends(get_db)):
    """Register a new user with email and password"""
    _enforce_auth_limit(f"register:{_client_ip(request)}", REGISTER_LIMIT)
    # Check if user already exists
    existing_user = AuthService.get_user_by_email(db, email=user_create.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user = AuthService.create_user(db=db, user_create=user_create)
    return user

@router.post("/login", response_model=Token)
async def login(request: Request, user_login: UserLogin, db: Session = Depends(get_db)):
    """Login with email and password"""
    key = f"login:{_client_ip(request)}:{user_login.email.lower()}"
    _enforce_auth_limit(key, LOGIN_LIMIT)
    user = AuthService.authenticate_user(db, user_login.email, user_login.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return current_user

@router.get("/logout")
async def logout():
    """Logout endpoint (client should delete the token)"""
    return {"message": "Successfully logged out. Please delete your token on the client side."}
