import argparse
import asyncio
import os

from sqlalchemy.ext.asyncio import create_async_engine

from reviewagent.db.session import Base, engine
from reviewagent.db import models


async def upgrade(database_url: str | None = None) -> None:
    active_engine = create_async_engine(database_url, pool_pre_ping=True) if database_url else engine
    try:
        async with active_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    finally:
        await active_engine.dispose()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create Phase 1 PoC database tables.")
    parser.add_argument(
        "command",
        nargs="?",
        default="upgrade",
        choices=["upgrade"],
        help="Migration command to run.",
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE__URL"),
        help="PostgreSQL async SQLAlchemy URL. Defaults to DATABASE__URL or app settings.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(upgrade(args.database_url))
    print("Created tables:", ", ".join(sorted(Base.metadata.tables)))


if __name__ == "__main__":
    main()
