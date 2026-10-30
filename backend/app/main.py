from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import ai, documents, investigations, samples
from .config import settings
from .db import Base, SessionLocal, engine
from .seed import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as session:
        await seed(session)
    yield
    await engine.dispose()


app = FastAPI(
    title="RCA Copilot API", version="0.1.0", lifespan=lifespan,
    description="GMP-inspired AI-assisted Root Cause Analysis prototype for API manufacturing. Not a validated GMP / Part 11 system.",
)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["*"], allow_headers=["*"])
app.include_router(investigations.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(samples.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {
        "status": "ok", "llm_mode": settings.llm_mode, "groq_key_set": bool(settings.groq_api_key),
        "models": {"analysis": settings.model_analysis, "fast": settings.model_fast, "fallback": settings.model_fallback},
    }
