
import os
from collections.abc import Generator
from uuid import UUID

from fastapi.responses import RedirectResponse
import httpx
from authlib.integrations.starlette_client import OAuth
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from database import SessionLocal
from models import GeneratedContent, User
from services.user_service import get_or_create_user
from pydantic import BaseModel, Field

from graph.creator_graph import build_creator_graph
from services.brand_voice_service import BrandVoiceService


load_dotenv()

CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET", "")
REDIRECT_URI = os.getenv(
    "LINKEDIN_REDIRECT_URI",
    "http://localhost:8000/auth/linkedin/callback",
)
SESSION_SECRET = os.getenv("SESSION_SECRET", "")

if not CLIENT_ID or not CLIENT_SECRET:
    raise RuntimeError(
        "Set LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET in .env."
    )

if not SESSION_SECRET:
    raise RuntimeError("Set SESSION_SECRET in .env.")


app = FastAPI(title="CreatorOS API")

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    session_cookie="creatoros_session",
    max_age=3600,
    same_site="lax",
    https_only=False,  # Local development only
)


oauth = OAuth()

oauth.register(
    name="linkedin",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    server_metadata_url=(
        "https://www.linkedin.com/oauth/.well-known/openid-configuration"
    ),
    token_endpoint_auth_method="client_secret_post",
    client_kwargs={"scope": "openid profile email"},
)


# Database dependency
def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as db:
        yield db


# Reusable authentication helper
def require_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
        )

    try:
        parsed_user_id = UUID(user_id)
    except (ValueError, TypeError):
        request.session.clear()
        raise HTTPException(
            status_code=401,
            detail="Invalid session. Please sign in again.",
        )

    user = db.get(User, parsed_user_id)

    if user is None:
        request.session.clear()
        raise HTTPException(
            status_code=401,
            detail="User not found. Please sign in again.",
        )

    return user

class BrandVoiceRequest(BaseModel):
    sample_posts: list[str] = Field(
        min_length=3,
        max_length=10,
    )

class ContentGenerationRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=300)


@app.get("/")
async def health_check():
    return {"application": "CreatorOS", "status": "running"}


@app.get("/auth/linkedin/login")
async def linkedin_login(request: Request):
    return await oauth.linkedin.authorize_redirect(
        request,
        REDIRECT_URI,
    )


@app.get("/auth/linkedin/callback")
async def linkedin_callback(request: Request):
    error = request.query_params.get("error")

    if error:
        raise HTTPException(
            status_code=400,
            detail="LinkedIn authorization was not completed.",
        )

    code = request.query_params.get("code")
    state = request.query_params.get("state")

    if not code or not state:
        raise HTTPException(
            status_code=400,
            detail="LinkedIn callback is missing code or state.",
        )

    # Validate OAuth state against the session.
    state_data = await oauth.linkedin.framework.get_state_data(
        request.session, state
    )

    if not state_data:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired OAuth state. Please try again.",
        )

    await oauth.linkedin.framework.clear_state_data(
        request.session, state
    )

    try:
        # Exchange the authorization code.
        token = await oauth.linkedin.fetch_access_token(
            code=code,
            redirect_uri=REDIRECT_URI,
        )

        access_token = token.get("access_token")
        if not access_token:
            raise RuntimeError("LinkedIn returned no access token.")

        # Retrieve the identity from LinkedIn's UserInfo endpoint.
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                "https://api.linkedin.com/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            userinfo = response.json()

    except Exception as exc:
        # Do not log authorization codes, tokens, or client secrets.
        print(f"LinkedIn callback failed: {type(exc).__name__}")
        raise HTTPException(
            status_code=400,
            detail="LinkedIn sign-in failed. Please try again.",
        ) from exc

    subject = userinfo.get("sub")

    if not subject:
        raise HTTPException(
            status_code=401,
            detail="LinkedIn did not return a member identifier.",
        )

    # Find or create the CreatorOS user.
    with SessionLocal() as db:
        user = get_or_create_user(db, userinfo)

        user_id = str(user.id)
        name = user.name
        email = user.email

    # Store only the internal CreatorOS user ID in the session.
    request.session.clear()
    request.session["user_id"] = user_id

    return RedirectResponse(
    url="http://localhost:5173",
    status_code=303,
)


@app.get("/auth/me")
async def get_current_user(
    current_user: User = Depends(require_current_user),
):
    return {
        "id": str(current_user.id),
        "name": current_user.name,
        "email": current_user.email,
    }


@app.post("/auth/logout")
async def logout(request: Request):
    request.session.clear()
    return {"message": "Logged out successfully"}


@app.get("/api/protected-test") # need to be removed in production, just for testing auth
async def protected_test(
    current_user: User = Depends(require_current_user),
):
    return {
        "message": "Authentication successful",
        "user_id": str(current_user.id),
    }


@app.post("/api/brand-voice")
def create_brand_voice(
    payload: BrandVoiceRequest,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    service = BrandVoiceService()

    try:
        profile = service.learn_voice(payload.sample_posts)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        # Avoid exposing provider errors or secrets to clients.
        raise HTTPException(
            status_code=502,
            detail="Brand voice generation failed. Please try again.",
        ) from exc

    voice = service.save_voice(
        db=db,
        user_id=current_user.id,
        profile=profile,
        sample_posts=payload.sample_posts,
    )

    return {
        "id": str(voice.id),
        "profile": voice.profile,
        "sample_posts": voice.sample_posts,
        "created_at": voice.created_at,
        "updated_at": voice.updated_at,
    }


@app.get("/api/brand-voice")
def get_brand_voice(
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    service = BrandVoiceService()

    voice = service.load_voice(
        db=db,
        user_id=current_user.id,
    )

    if voice is None:
        raise HTTPException(
            status_code=404,
            detail="No brand voice profile found. Please create one.",
        )

    return {
        "id": str(voice.id),
        "profile": voice.profile,
        "sample_posts": voice.sample_posts,
        "created_at": voice.created_at,
        "updated_at": voice.updated_at,
    }


@app.post("/api/content/generate")
def generate_content(
    payload: ContentGenerationRequest,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    topic = payload.topic.strip()

    if len(topic) < 3:
        raise HTTPException(
            status_code=400,
            detail="Please provide a topic with at least 3 characters.",
        )

    # Load the authenticated user's saved brand voice.
    voice_service = BrandVoiceService()
    voice = voice_service.load_voice(
        db=db,
        user_id=current_user.id,
    )

    if voice is None:
        raise HTTPException(
            status_code=400,
            detail="Please create your brand voice profile first.",
        )

    initial_state = {
        "tenant_id": str(current_user.id),
        "topic": topic,
        "brand_voice": voice.profile,
        "strategist_angle": "",
        "strategy_reason": "",
        "draft": "",
        "critique": "",
        "revision_count": 0,
        "max_revisions": 2,
        "approved": False,
        "audit_trail": [],
    }

    try:
        graph = build_creator_graph()
        result = graph.invoke(initial_state)
    
    except Exception as exc:
        import traceback

        traceback.print_exc()

        raise HTTPException(
            status_code=502,
            detail="Content generation failed. Please try again.",
        ) from exc

    
    content = GeneratedContent(
        user_id=current_user.id,
        topic=topic,
        draft=result["draft"],
        approved=result["approved"],
        strategist_angle=result["strategist_angle"],
        strategy_reason=result["strategy_reason"],
        revision_count=result["revision_count"],
        audit_trail=result["audit_trail"],
    )

    try:
        db.add(content)
        db.commit()
        db.refresh(content)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Content was generated but could not be saved.",
        ) from exc

    return {
        "id": str(content.id),
        "topic": content.topic,
        "draft": content.draft,
        "approved": content.approved,
        "strategist_angle": content.strategist_angle,
        "strategy_reason": content.strategy_reason,
        "revision_count": content.revision_count,
        "audit_trail": content.audit_trail,
        "created_at": content.created_at,
    }


@app.get("/api/content/history")
def get_content_history(
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    from sqlalchemy import select

    statement = (
        select(GeneratedContent)
        .where(GeneratedContent.user_id == current_user.id)
        .order_by(GeneratedContent.created_at.desc())
    )

    contents = db.scalars(statement).all()

    return [
        {
            "id": str(item.id),
            "topic": item.topic,
            "draft": item.draft,
            "approved": item.approved,
            "strategist_angle": item.strategist_angle,
            "strategy_reason": item.strategy_reason,
            "revision_count": item.revision_count,
            "audit_trail": item.audit_trail,
            "created_at": item.created_at,
        }
        for item in contents
    ]

