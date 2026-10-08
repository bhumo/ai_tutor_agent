from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from auth.routes import get_current_user
from database.models import User, get_db
from sessions.schemas import SessionCreate, SessionDetail, SessionSummary
from sessions.service import SessionService


router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionSummary, status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: SessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return SessionService.create(db, current_user.id, payload.title)


@router.get("", response_model=list[SessionSummary])
async def list_sessions(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return SessionService.list_for_user(db, current_user.id)


@router.get("/{session_id}", response_model=SessionDetail)
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = SessionService.get_owned(db, session_id, current_user.id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    session.messages = SessionService.recent_messages(db, session.id)
    return session


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not SessionService.delete_owned(db, session_id, current_user.id):
        raise HTTPException(status_code=404, detail="Session not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
