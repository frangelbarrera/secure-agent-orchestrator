from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..models.command_task import CommandTask
from ..schemas.command_task import CommandTaskCreate, CommandTaskUpdate


class CRUDCommandTask:
    async def create(self, db: AsyncSession, obj_in: CommandTaskCreate, agent_id: str, task_id: str) -> CommandTask:
        db_obj = CommandTask(task_id=task_id, agent_id=agent_id, **obj_in.model_dump())
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get(self, db: AsyncSession, task_id: str) -> CommandTask | None:
        result = await db.execute(select(CommandTask).where(CommandTask.task_id == task_id))
        return result.scalars().first()

    async def get_by_agent(self, db: AsyncSession, agent_id: str) -> List[CommandTask]:
        result = await db.execute(select(CommandTask).where(CommandTask.agent_id == agent_id))
        return list(result.scalars().all())

    async def update(self, db: AsyncSession, db_obj: CommandTask, obj_in: CommandTaskUpdate) -> CommandTask:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def remove(self, db: AsyncSession, task_id: str) -> CommandTask | None:
        result = await db.execute(select(CommandTask).where(CommandTask.task_id == task_id))
        db_obj = result.scalars().first()
        if db_obj:
            await db.delete(db_obj)
            await db.commit()
        return db_obj


crud_command_task = CRUDCommandTask()