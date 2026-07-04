"""Create the first tier in the database, idempotently.

Run with:
    ENVIRONMENT=local SECRET_KEY=$(python -c "import secrets;print(secrets.token_urlsafe(32))") \
    ADMIN_PASSWORD="StrongTestAdminPass123!" \
    venv/bin/python -m src.scripts.create_first_tier
"""
import asyncio
import logging

from sqlalchemy import select

from ..app.core.config import settings
from ..app.core.db.database import AsyncSession, Base, async_engine, local_session
from ..app.models.tier import Tier  # noqa: F401  (register model with Base.metadata)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_first_tier(session: AsyncSession, tier_name: str = "free") -> None:
    try:
        query = select(Tier).where(Tier.name == tier_name)
        result = await session.execute(query)
        tier = result.scalar_one_or_none()

        if tier is None:
            session.add(Tier(name=tier_name))
            await session.commit()
            logger.info("Tier '%s' created successfully.", tier_name)
        else:
            logger.info("Tier '%s' already exists.", tier_name)

    except Exception as e:
        logger.error("Error creating tier: %s", e)
        raise


async def main() -> None:
    # Ensure the schema exists before inserting. The app's lifespan normally
    # does this, but standalone scripts do not run the lifespan.
    async with async_engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, checkfirst=True))

    async with local_session() as session:
        await create_first_tier(session, tier_name="free")


if __name__ == "__main__":
    asyncio.run(main())
