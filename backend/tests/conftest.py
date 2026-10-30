"""Tests run against the separate `rca_test` database and the offline LLM fixture (no Groq calls)."""
import os
import re
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
env = (BACKEND / ".env").read_text(encoding="utf-8")
test_url = re.search(r"^TEST_DATABASE_URL=(.+)$", env, re.M).group(1).strip()
os.environ["DATABASE_URL"] = test_url          # must be set before importing the app
os.environ["LLM_MODE"] = "fixture"

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402


@pytest_asyncio.fixture
async def client():
    from app.db import Base, SessionLocal, engine
    from app.main import app
    from app.seed import seed

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as s:
        await seed(s)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    await engine.dispose()
