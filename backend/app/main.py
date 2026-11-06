
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api.chats import router as chats_router
from app.api.youtube import router as youtube_router
from app.api.youtube import video_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Shared clients and resources will be initialized in later steps.
    yield
    # Resources will be closed here when the application shuts down.


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(chats_router)
app.include_router(youtube_router)
app.include_router(video_router)

@app.get("/api/v1/health", tags=["Health"])
async def health_check():
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.app_env,
    }
