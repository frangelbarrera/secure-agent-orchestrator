"""Create the first superuser in the database, idempotently.

Reads ADMIN_NAME, ADMIN_EMAIL, ADMIN_USERNAME and ADMIN_PASSWORD from
settings (env vars or .env file) and inserts a superuser row if one
with that email does not already exist.

Run with:
    ENVIRONMENT=local SECRET_KEY=$(python -c "import secrets;print(secrets.token_urlsafe(32))") \
    ADMIN_PASSWORD="StrongTestAdminPass123!" \
    venv/bin/python -m src.scripts.create_first_superuser
"""

import asyncio
import logging

from sqlalchemy import select

from ..app.core.config import settings
from ..app.core.db.database import AsyncSession, Base, async_engine, local_session
from ..app.core.security import get_password_hash_async
from ..app.models.user import User  # noqa: F401  (register model with Base.metadata)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_first_user(session: AsyncSession) -> None:
    try:
        name = settings.ADMIN_NAME
        email = settings.ADMIN_EMAIL
        username = settings.ADMIN_USERNAME
        hashed_password = await get_password_hash_async(settings.ADMIN_PASSWORD)

        query = select(User).where(User.email == email)
        result = await session.execute(query)
        user = result.scalar_one_or_none()

        if user is None:
            new_user = User(
                name=name,
                email=email,
                username=username,
                hashed_password=hashed_password,
                is_superuser=True,
            )
            session.add(new_user)
            await session.commit()
            logger.info("Admin user '%s' created successfully.", username)
        else:
            logger.info("Admin user '%s' already exists.", username)

    except Exception as e:
        logger.error("Error creating admin user: %s", e)
        raise


async def main() -> None:
    # Ensure the schema exists before inserting. The app's lifespan normally
    # does this, but standalone scripts do not run the lifespan.
    async with async_engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, checkfirst=True))

    async with local_session() as session:
        await create_first_user(session)


if __name__ == "__main__":
    asyncio.run(main())
