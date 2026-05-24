from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from reviewagent.api.routers import decisions, health, submissions
from reviewagent.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    app.state.settings = settings
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app.name,
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.app.env == "development" else None,
    )

    app.include_router(health.router)
    app.include_router(submissions.router)
    app.include_router(decisions.router)

    return app


app = create_app()
