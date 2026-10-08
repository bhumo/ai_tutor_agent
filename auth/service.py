from sqlalchemy.orm import Session
from database.models import User
from auth.utils import get_password_hash, verify_password
from auth.schemas import UserCreate
from typing import Optional
import uuid

class AuthService:
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Get user by email"""
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def create_user(db: Session, user_create: UserCreate) -> User:
        """Create a new user with email/password"""
        hashed_password = get_password_hash(user_create.password)
        db_user = User(
            id=str(uuid.uuid4()),
            email=user_create.email,
            username=user_create.username,
            full_name=user_create.full_name,
            hashed_password=hashed_password,
            is_verified=False  # Email verification can be added later
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    
    @staticmethod
    def create_google_user(db: Session, email: str, full_name: str, google_id: str, profile_picture: str = None) -> User:
        """Create a new user from Google OAuth"""
        db_user = User(
            id=str(uuid.uuid4()),
            email=email,
            full_name=full_name,
            google_id=google_id,
            profile_picture=profile_picture,
            is_verified=True,  # Google users are pre-verified
            hashed_password=None  # No password for OAuth users
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    
    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password"""
        user = AuthService.get_user_by_email(db, email)
        if not user or not user.hashed_password:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user
