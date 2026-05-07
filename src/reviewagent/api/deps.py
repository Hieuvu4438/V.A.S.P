from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from reviewagent.agents.graph import ReviewPipeline
from reviewagent.config import Settings, get_settings
from reviewagent.db.session import get_async_session


async def get_db() -> AsyncIterator[AsyncSession]:
    async for session in get_async_session():
        yield session


def get_pipeline() -> ReviewPipeline:
    return ReviewPipeline()
