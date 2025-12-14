from sqlalchemy.ext.asyncio import AsyncSession


class RateLimiter:
    async def is_rate_limited(self, db: AsyncSession, user_id: int, path: str, limit: int, period: int) -> bool:
        # Simplified: no rate limiting
        return False


rate_limiter = RateLimiter()
