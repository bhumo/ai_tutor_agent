from __future__ import annotations

import json
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from database.models import ChatMessage, ChatSession
from rag.schemas import TutorAnswer


class SessionService:
    @staticmethod
    def create(db: Session, user_id: str, title: str = "New tutoring session") -> ChatSession:
        session = ChatSession(id=str(uuid.uuid4()), user_id=user_id, title=title.strip())
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    @staticmethod
    def list_for_user(db: Session, user_id: str, limit: int = 50) -> list[ChatSession]:
        return (
            db.query(ChatSession)
            .filter(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
            .limit(min(max(limit, 1), 100))
            .all()
        )

    @staticmethod
    def get_owned(db: Session, session_id: str, user_id: str) -> ChatSession | None:
        return db.query(ChatSession).filter(
            ChatSession.id == session_id, ChatSession.user_id == user_id
        ).first()

    @staticmethod
    def delete_owned(db: Session, session_id: str, user_id: str) -> bool:
        session = SessionService.get_owned(db, session_id, user_id)
        if session is None:
            return False
        db.delete(session)
        db.commit()
        return True

    @staticmethod
    def add_exchange(
        db: Session, session: ChatSession, user_message: str, answer: TutorAnswer
    ) -> None:
        if session.title == "New tutoring session":
            session.title = user_message[:117] + ("..." if len(user_message) > 117 else "")
        session.updated_at = datetime.utcnow()
        serialized = answer.model_dump(mode="json")
        citations = getattr(answer, "citations", None)
        if citations is None:
            citations_data = serialized.get("citations", [])
        else:
            citations_data = [
                citation.model_dump(mode="json") for citation in citations
            ]
        db.add_all([
            ChatMessage(
                id=str(uuid.uuid4()), session_id=session.id, role="user", content=user_message
            ),
            ChatMessage(
                id=str(uuid.uuid4()),
                session_id=session.id,
                role="assistant",
                content=answer.answer,
                route=getattr(answer, "route", serialized.get("route")),
                citations_json=json.dumps(citations_data),
                trace_id=getattr(answer, "trace_id", serialized.get("trace_id")),
            ),
        ])
        db.commit()

    @staticmethod
    def recent_messages(
        db: Session, session_id: str, limit: int = 100
    ) -> list[ChatMessage]:
        bounded = min(max(limit, 1), 100)
        messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .limit(bounded)
            .all()
        )
        return list(reversed(messages))
