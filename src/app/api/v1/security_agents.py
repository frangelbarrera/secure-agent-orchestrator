import asyncio
import uuid
from datetime import datetime, UTC
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import async_get_db
from ...crud.crud_command_task import crud_command_task
from ...crud.crud_security_agent import crud_security_agent
from ...schemas.command_task import CommandTaskCreate, CommandTaskRead
from ...schemas.security_agent import SecurityAgentRead
from ..dependencies import get_current_user

router = APIRouter(prefix="/security-agents", tags=["security-agents"])


@router.get("/", response_model=List[SecurityAgentRead], dependencies=[Depends(get_current_user)])
async def get_security_agents(db: AsyncSession = Depends(async_get_db)):
    agents = await crud_security_agent.get_multi(db)
    return agents


@router.post("/{agent_id}/execute-command", response_model=dict, dependencies=[Depends(get_current_user)])
async def execute_command(agent_id: str, command: CommandTaskCreate, db: AsyncSession = Depends(async_get_db)):
    # Validate agent exists
    agent = await crud_security_agent.get(db, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Security agent not found")

    # Generate task_id
    task_id = str(uuid.uuid4())

    # Create task
    task = await crud_command_task.create(db, command, agent_id, task_id)

    # Simulate async execution
    asyncio.create_task(simulate_command_execution(db, task_id))

    return {"task_id": task_id}


@router.get("/{agent_id}/task-status/{task_id}", response_model=CommandTaskRead, dependencies=[Depends(get_current_user)])
async def get_task_status(agent_id: str, task_id: str, db: AsyncSession = Depends(async_get_db)):
    task = await crud_command_task.get(db, task_id)
    if not task or task.agent_id != agent_id:
        raise HTTPException(status_code=404, detail="Command task not found")
    return task


async def simulate_command_execution(db: AsyncSession, task_id: str):
    # Simulate execution
    await asyncio.sleep(5)

    # Update task status
    task = await crud_command_task.get(db, task_id)
    if task:
        from ...schemas.command_task import CommandTaskUpdate
        update_data = CommandTaskUpdate(
            status="COMPLETED",
            result="Command executed successfully",
            completed_at=datetime.now(UTC).replace(tzinfo=None)
        )
        await crud_command_task.update(db, task, update_data)