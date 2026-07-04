import uuid
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


@router.post("/{agent_id}/command", response_model=CommandTaskRead, status_code=201,
             dependencies=[Depends(get_current_user)])
async def register_command(
    agent_id: str,
    command: CommandTaskCreate,
    db: AsyncSession = Depends(async_get_db),
):
    """Register a command task against a security agent.

    The task is stored in PENDING state. This endpoint does NOT execute
    the command: there is no subprocess, no shell, no agent pull/push
    protocol. The recorded task is intended to be picked up by an
    external agent runner (out of scope for this control plane).

    A future revision may introduce a real execution backend with
    sandboxing, timeout and allowlist controls. Until then, this
    endpoint is a registry, not an executor.
    """
    agent = await crud_security_agent.get(db, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Security agent not found")

    task_id = str(uuid.uuid4())
    task = await crud_command_task.create(db, command, agent_id, task_id)
    return task


@router.get("/{agent_id}/task-status/{task_id}", response_model=CommandTaskRead,
            dependencies=[Depends(get_current_user)])
async def get_task_status(agent_id: str, task_id: str, db: AsyncSession = Depends(async_get_db)):
    task = await crud_command_task.get(db, task_id)
    if not task or task.agent_id != agent_id:
        raise HTTPException(status_code=404, detail="Command task not found")
    return task
