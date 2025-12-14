from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..models.security_agent import SecurityAgent
from ..schemas.security_agent import SecurityAgentCreate, SecurityAgentUpdate


class CRUDSecurityAgent:
    async def create(self, db: AsyncSession, obj_in: SecurityAgentCreate) -> SecurityAgent:
        db_obj = SecurityAgent(**obj_in.model_dump())
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get(self, db: AsyncSession, agent_id: str) -> SecurityAgent | None:
        result = await db.execute(select(SecurityAgent).where(SecurityAgent.agent_id == agent_id))
        return result.scalars().first()

    async def get_multi(self, db: AsyncSession) -> List[SecurityAgent]:
        result = await db.execute(select(SecurityAgent))
        return list(result.scalars().all())

    async def update(self, db: AsyncSession, db_obj: SecurityAgent, obj_in: SecurityAgentUpdate) -> SecurityAgent:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def remove(self, db: AsyncSession, agent_id: str) -> SecurityAgent | None:
        result = await db.execute(select(SecurityAgent).where(SecurityAgent.agent_id == agent_id))
        db_obj = result.scalars().first()
        if db_obj:
            await db.delete(db_obj)
            await db.commit()
        return db_obj


crud_security_agent = CRUDSecurityAgent()