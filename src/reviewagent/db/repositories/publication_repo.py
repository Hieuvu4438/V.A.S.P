from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from reviewagent.db.models.publication import Publication
from reviewagent.schemas.cms import CanonicalMetadataSchema


def _publication_values(cms: CanonicalMetadataSchema) -> dict[str, Any]:
    return {
        "doi": cms.doi,
        "title": cms.title,
        "pub_year": cms.pub_year,
        "pub_date": cms.pub_date,
        "cms": cms.model_dump(mode="json"),
        "provenance": {
            "source_api": cms.source_api,
            "source_url": str(cms.source_url),
            "fetched_at": cms.fetched_at.isoformat(),
        },
    }


async def get_publication_by_doi(session: AsyncSession, doi: str) -> Publication | None:
    result = await session.execute(select(Publication).where(Publication.doi == doi))
    return result.scalar_one_or_none()


async def upsert_publication_from_cms(session: AsyncSession, cms: CanonicalMetadataSchema) -> Publication:
    publication = await get_publication_by_doi(session, cms.doi)
    values = _publication_values(cms)

    if publication is None:
        publication = Publication(**values)
        session.add(publication)
    else:
        for key, value in values.items():
            setattr(publication, key, value)

    await session.flush()
    return publication
