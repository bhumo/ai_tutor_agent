import logging
import os

from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from graph.workflow import TutorWorkflow
from auth.routes import router as auth_router
from auth.routes import get_current_user
from database.models import create_tables, User
from database.models import get_db
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from utils.security_config import get_allowed_origins
from utils.rate_limit import (
    ConcurrencyLimiter,
    ConcurrencyLimitExceeded,
    SlidingWindowRateLimiter,
)
from utils.request_limits import RequestBodyLimitMiddleware
from sessions.routes import router as sessions_router
from sessions.service import SessionService


logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: str = Field(max_length=4_000)
    session_id: str | None = Field(default=None, min_length=1, max_length=64)


chat_rate_limiter = SlidingWindowRateLimiter()
chat_concurrency_limiter = ConcurrencyLimiter()
CHAT_RATE_LIMIT = int(os.getenv("CHAT_RATE_LIMIT", "15"))
CHAT_RATE_WINDOW_SECONDS = int(os.getenv("CHAT_RATE_WINDOW_SECONDS", "60"))
CHAT_CONCURRENCY_LIMIT = int(os.getenv("CHAT_CONCURRENCY_LIMIT", "2"))

app = FastAPI(title="AI Tutor Agent with Authentication")
app.add_middleware(RequestBodyLimitMiddleware, max_bytes=16_384)

# Add CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Create database tables
create_tables()

api_key = os.environ["GEMINI_API_KEY"] 
workflow = TutorWorkflow(api_key)

# Include authentication routes
app.include_router(auth_router)
app.include_router(sessions_router)
# Mount the frontend folder
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# Serve the HTML page at root
@app.get("/", response_class=HTMLResponse)
async def serve_home():
    return FileResponse("frontend/index.html")

# Serve the login page
@app.get("/login", response_class=HTMLResponse)
async def serve_login():
    return FileResponse("frontend/login.html")

@app.get("/health")
async def health_check():
    return {"status": "ok"}

# API endpoint for authenticated chat
@app.post("/chat")
async def chat(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="A non-empty message is required")
    decision = chat_rate_limiter.check(
        f"chat:{current_user.id}", CHAT_RATE_LIMIT, CHAT_RATE_WINDOW_SECONDS
    )
    if not decision.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Chat rate limit exceeded. Please try again later.",
            headers={"Retry-After": str(decision.retry_after)},
        )
    if payload.session_id:
        chat_session = SessionService.get_owned(db, payload.session_id, current_user.id)
        if chat_session is None:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        chat_session = None
    try:
        with chat_concurrency_limiter.acquire(
            f"chat:{current_user.id}", CHAT_CONCURRENCY_LIMIT
        ):
            result = workflow.process(message)
    except ConcurrencyLimitExceeded:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many concurrent tutor requests.",
            headers={"Retry-After": "1"},
        ) from None
    except Exception:
        logger.exception("Tutor workflow failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The tutor is temporarily unavailable. Please try again.",
        ) from None
    # Do not leave empty sessions behind when the provider fails.
    if chat_session is None:
        chat_session = SessionService.create(db, current_user.id)
    SessionService.add_exchange(db, chat_session, message, result)
    return {
        "response": result.answer,
        "rag": result.model_dump(mode="json"),
        "session_id": chat_session.id,
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name
        }
    }
