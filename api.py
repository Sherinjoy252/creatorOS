
import os
import re
from collections.abc import Generator
from uuid import UUID
import uuid

from fastapi.responses import RedirectResponse
import httpx
from authlib.integrations.starlette_client import OAuth
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import select, func

from database import SessionLocal
from models import GeneratedContent, LearningLesson, PostPerformance, User
from services.user_service import get_or_create_user
from pydantic import BaseModel, Field

from graph.creator_graph import build_creator_graph
from services.brand_voice_service import BrandVoiceService
from services.learning_service import LearningService


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

class PerformanceInput(BaseModel):
    impressions: int = Field(ge=0)
    likes: int = Field(ge=0)
    comments: int = Field(ge=0)
    reposts: int = Field(ge=0)
    audience_comments: list[str] = Field(
        default_factory=list,
        max_length=100,
    )
    data_source: str = "manual"


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

    approved_lessons = db.scalars(
        select(LearningLesson)
        .where(
            LearningLesson.user_id == current_user.id,
            LearningLesson.status == "approved",
        )
        .order_by(LearningLesson.created_at.desc())
        .limit(10)
    ).all()

    lesson_texts = [lesson.lesson for lesson in approved_lessons]

    initial_state = {
        "tenant_id": str(current_user.id),
        "topic": topic,
        "brand_voice": voice.profile,
        "approved_lessons": lesson_texts,
        "strategist_angle": "",
        "strategy_reason": "",
        "draft": "",
        "critique": "",
        "revision_count": 0,
        "max_revisions": 2,
        "approved": False,
        "audit_trail": [],
        "initial_evaluation": None,
        "final_evaluation": None,
        "evaluation_score_delta": None,
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
        initial_evaluation=result.get("initial_evaluation"),
        final_evaluation=result.get("final_evaluation"),
        evaluation_score_delta=result.get("evaluation_score_delta"),
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
        "initial_evaluation": content.initial_evaluation,
        "final_evaluation": content.final_evaluation,
        "evaluation_score_delta": content.evaluation_score_delta,
        "created_at": content.created_at,
    }


@app.get("/api/content/history")
def get_content_history(
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):

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
            "initial_evaluation": getattr(item, "initial_evaluation", None),
            "final_evaluation": getattr(item, "final_evaluation", None),
            "evaluation_score_delta": getattr(item, "evaluation_score_delta", None),
            "created_at": item.created_at,
        }
        for item in contents
    ]

def _normalize_lesson_text(lesson: str) -> str:
    """Normalize lesson wording for a safe exact-duplicate check."""
    return " ".join(re.sub(r"[^a-z0-9]+", " ", lesson.lower()).split())


def _save_new_learning_lessons(
    db: Session,
    content_id: uuid.UUID,
    user_id: uuid.UUID,
    lesson_texts: list[str],
) -> list[LearningLesson]:
    """
    Persist only lessons not already recorded for this post.

    Existing proposed, approved, and rejected records are all considered
    duplicates so a user's previous decision is never overwritten.
    """
    existing_lessons = db.scalars(
        select(LearningLesson).where(
            LearningLesson.content_id == content_id,
            LearningLesson.user_id == user_id,
        )
    ).all()

    existing_normalized = {
        _normalize_lesson_text(item.lesson)
        for item in existing_lessons
        if getattr(item, "lesson", None)
    }

    new_lessons = []
    for lesson_text in lesson_texts:
        if not isinstance(lesson_text, str) or not lesson_text.strip():
            continue

        cleaned = lesson_text.strip()
        normalized = _normalize_lesson_text(cleaned)

        if not normalized or normalized in existing_normalized:
            continue

        existing_normalized.add(normalized)
        new_lessons.append(
            LearningLesson(
                user_id=user_id,
                content_id=content_id,
                lesson=cleaned,
                status="proposed",
            )
        )

    if new_lessons:
        db.add_all(new_lessons)
        db.commit()
        for lesson in new_lessons:
            db.refresh(lesson)

    return new_lessons


@app.post("/api/content/{content_id}/performance")
def save_performance(
    content_id: uuid.UUID,
    payload: PerformanceInput,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    content = db.scalar(
        select(GeneratedContent).where(
            GeneratedContent.id == content_id,
            GeneratedContent.user_id == current_user.id,
        )
    )

    if content is None:
        raise HTTPException(
            status_code=404,
            detail="Content not found",
        )

    if payload.data_source not in {"manual", "simulated"}:
        raise HTTPException(
            status_code=400,
            detail="data_source must be manual or simulated",
        )

    audience_comments = [
        comment.strip()
        for comment in payload.audience_comments
        if comment.strip()
    ]

    # Avoid re-running the learning engine when the exact same snapshot
    # (metrics, comments, and source) has already been submitted for this post.
    previous_snapshots = db.scalars(
        select(PostPerformance).where(
            PostPerformance.content_id == content.id
        )
    ).all()

    normalized_comments = sorted(
        " ".join(comment.lower().split()) for comment in audience_comments
    )

    duplicate_snapshot = next(
        (
            item
            for item in previous_snapshots
            if (
                item.impressions == payload.impressions
                and item.likes == payload.likes
                and item.comments == payload.comments
                and item.reposts == payload.reposts
                and item.data_source == payload.data_source
                and sorted(
                    " ".join(comment.lower().split())
                    for comment in (item.audience_comments or [])
                ) == normalized_comments
            )
        ),
        None,
    )

    if duplicate_snapshot is not None:
        return {
            "id": str(duplicate_snapshot.id),
            "content_id": str(duplicate_snapshot.content_id),
            "impressions": duplicate_snapshot.impressions,
            "likes": duplicate_snapshot.likes,
            "comments": duplicate_snapshot.comments,
            "reposts": duplicate_snapshot.reposts,
            "data_source": duplicate_snapshot.data_source,
            "recorded_at": duplicate_snapshot.recorded_at,
            "learning_status": "skipped_duplicate",
            "lessons_created": 0,
            "audience_comments": duplicate_snapshot.audience_comments or [],
            "message": (
                "This exact performance snapshot was already submitted. "
                "Learning analysis was skipped."
            ),
        }

    snapshot = PostPerformance(
        content_id=content.id,
        impressions=payload.impressions,
        likes=payload.likes,
        comments=payload.comments,
        reposts=payload.reposts,
        audience_comments=audience_comments,
        data_source=payload.data_source,
    )

    try:
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not save performance metrics.",
        ) from exc

    # Step 2: Automatically analyze performance using LearningService.
    learning_status = "completed"
    lessons_created = 0

    try:
        service = LearningService()

        lessons = service.propose_lessons(
            db=db,
            content=content,
            user_id=current_user.id,
        )

        # Save only genuinely new lessons. Existing decisions are preserved.
        proposed_lessons = _save_new_learning_lessons(
            db=db,
            content_id=content.id,
            user_id=current_user.id,
            lesson_texts=lessons,
        )
        lessons_created = len(proposed_lessons)

    except Exception:
        # Keep the already committed performance snapshot.
        db.rollback()
        learning_status = "failed"

    # Step 4: Return the saved metrics and learning result.
    return {
        "id": str(snapshot.id),
        "content_id": str(snapshot.content_id),
        "impressions": snapshot.impressions,
        "likes": snapshot.likes,
        "comments": snapshot.comments,
        "reposts": snapshot.reposts,
        "data_source": snapshot.data_source,
        "recorded_at": snapshot.recorded_at,
        "learning_status": learning_status,
        "lessons_created": lessons_created,
        "audience_comments": snapshot.audience_comments,
    }

@app.get("/api/content/{content_id}/performance")
def get_performance_history(
    content_id: uuid.UUID,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    content = db.scalar(
        select(GeneratedContent).where(
            GeneratedContent.id == content_id,
            GeneratedContent.user_id == current_user.id,
        )
    )

    if content is None:
        raise HTTPException(
            status_code=404,
            detail="Content not found",
        )

    snapshots = db.scalars(
        select(PostPerformance)
        .where(PostPerformance.content_id == content.id)
        .order_by(PostPerformance.recorded_at.asc())
    ).all()

    return [
        {
            "id": str(item.id),
            "impressions": item.impressions,
            "likes": item.likes,
            "comments": item.comments,
            "reposts": item.reposts,
            "data_source": item.data_source,
            "recorded_at": item.recorded_at,
            "audience_comments": item.audience_comments or [],
        }
        for item in snapshots
    ]


@app.post("/api/content/{content_id}/teach")
def teach_creatoros(
    content_id: uuid.UUID,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    # Verify that the post belongs to the signed-in user.
    content = db.scalar(
        select(GeneratedContent).where(
            GeneratedContent.id == content_id,
            GeneratedContent.user_id == current_user.id,
        )
    )

    if content is None:
        raise HTTPException(status_code=404, detail="Content not found")

    # Require performance data before teaching.
    snapshots = db.scalars(
        select(PostPerformance).where(
            PostPerformance.content_id == content.id
        )
    ).all()

    if not snapshots:
        raise HTTPException(
            status_code=400,
            detail="Add performance data before teaching CreatorOS.",
        )

    # Analyze the performance through Mesh API.
    try:
        service = LearningService()
        lessons = service.propose_lessons(
            db=db,
            content=content,
            user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Could not analyze performance. Please try again.",
        ) from exc

    # Save only new lessons; never duplicate existing proposals or decisions.
    try:
        saved_lessons = _save_new_learning_lessons(
            db=db,
            content_id=content.id,
            user_id=current_user.id,
            lesson_texts=lessons,
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not save the proposed lessons.",
        ) from exc

    has_simulated_data = any(
        item.data_source == "simulated" for item in snapshots
    )

    return {
        "content_id": str(content.id),
        "lessons": [
            {
                "id": str(item.id),
                "lesson": item.lesson,
                "status": item.status,
                "demo_only": has_simulated_data,
            }
            for item in saved_lessons
        ],
        "message": (
            "No new lessons were identified. Existing lessons were retained."
            if not saved_lessons
            else "New learning lessons were saved."
        ),
    }


@app.get("/api/content/{content_id}/lessons")
def get_learning_lessons(
    content_id: uuid.UUID,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    # Verify post ownership.
    content = db.scalar(
        select(GeneratedContent).where(
            GeneratedContent.id == content_id,
            GeneratedContent.user_id == current_user.id,
        )
    )

    if content is None:
        raise HTTPException(status_code=404, detail="Content not found")

    lessons = db.scalars(
        select(LearningLesson)
        .where(
            LearningLesson.content_id == content.id,
            LearningLesson.user_id == current_user.id,
        )
        .order_by(LearningLesson.created_at.desc())
    ).all()

    return [
        {
            "id": str(item.id),
            "content_id": str(item.content_id),
            "lesson": item.lesson,
            "status": item.status,
            "created_at": item.created_at,
            "approved_at": item.approved_at,
        }
        for item in lessons
    ]


def _get_owned_lesson(
    content_id: uuid.UUID,
    lesson_id: uuid.UUID,
    current_user: User,
    db: Session,
):
    """Load a lesson only when its post and lesson belong to the user."""
    content = db.scalar(
        select(GeneratedContent).where(
            GeneratedContent.id == content_id,
            GeneratedContent.user_id == current_user.id,
        )
    )
    if content is None:
        raise HTTPException(status_code=404, detail="Content not found")

    lesson = db.scalar(
        select(LearningLesson).where(
            LearningLesson.id == lesson_id,
            LearningLesson.content_id == content.id,
            LearningLesson.user_id == current_user.id,
        )
    )
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")

    return content, lesson


@app.post("/api/content/{content_id}/lessons/{lesson_id}/approve")
def approve_learning_lesson(
    content_id: uuid.UUID,
    lesson_id: uuid.UUID,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    content, lesson = _get_owned_lesson(
        content_id, lesson_id, current_user, db
    )

    if lesson.status == "approved":
        return {
            "id": str(lesson.id),
            "lesson": lesson.lesson,
            "status": lesson.status,
            "message": "Lesson is already approved.",
        }

    if lesson.status == "rejected":
        raise HTTPException(
            status_code=409,
            detail="A rejected lesson cannot be approved.",
        )

    # Simulated performance must not become approved real-world learning.
    snapshots = db.scalars(
        select(PostPerformance).where(
            PostPerformance.content_id == content.id
        )
    ).all()
    if any(item.data_source == "simulated" for item in snapshots):
        raise HTTPException(
            status_code=400,
            detail=(
                "This post includes simulated performance data. "
                "Its lessons cannot be approved as real-performance insights."
            ),
        )

    lesson.status = "approved"
    lesson.approved_at = func.now()

    try:
        db.commit()
        db.refresh(lesson)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not approve the lesson.",
        ) from exc

    return {
        "id": str(lesson.id),
        "lesson": lesson.lesson,
        "status": lesson.status,
        "approved_at": lesson.approved_at,
    }


@app.post("/api/content/{content_id}/lessons/{lesson_id}/reject")
def reject_learning_lesson(
    content_id: uuid.UUID,
    lesson_id: uuid.UUID,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    _, lesson = _get_owned_lesson(
        content_id, lesson_id, current_user, db
    )

    if lesson.status == "rejected":
        return {
            "id": str(lesson.id),
            "lesson": lesson.lesson,
            "status": lesson.status,
            "message": "Lesson is already rejected.",
        }

    if lesson.status == "approved":
        raise HTTPException(
            status_code=409,
            detail="An approved lesson cannot be rejected.",
        )

    lesson.status = "rejected"
    lesson.approved_at = None

    try:
        db.commit()
        db.refresh(lesson)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not reject the lesson.",
        ) from exc

    return {
        "id": str(lesson.id),
        "lesson": lesson.lesson,
        "status": lesson.status,
    }
