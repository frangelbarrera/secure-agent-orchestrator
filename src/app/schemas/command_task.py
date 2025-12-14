from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CommandTaskBase(BaseModel):
    task_id: str = Field(..., description="Unique identifier for the command task")
    agent_id: str = Field(..., description="ID of the agent executing the task")
    command: str = Field(..., description="Command to execute")
    status: str = Field("PENDING", description="Status: PENDING, RUNNING, COMPLETED, ERROR")
    created_at: datetime = Field(..., description="Creation timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    result: Optional[str] = Field(None, description="Result of the command execution")


class CommandTaskCreate(BaseModel):
    command: str = Field(..., description="Command to execute")


class CommandTaskRead(CommandTaskBase):
    pass


class CommandTaskUpdate(BaseModel):
    status: Optional[str] = None
    completed_at: Optional[datetime] = None
    result: Optional[str] = None