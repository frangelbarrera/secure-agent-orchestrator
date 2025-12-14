from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SecurityAgentBase(BaseModel):
    agent_id: str = Field(..., description="Unique identifier for the security agent")
    hostname: str = Field(..., description="Hostname of the agent server")
    ip_address: str = Field(..., description="IP address of the agent server")
    status: str = Field("offline", description="Status of the agent: online or offline")
    last_checkin: datetime = Field(..., description="Last check-in timestamp")


class SecurityAgentCreate(SecurityAgentBase):
    pass


class SecurityAgentRead(SecurityAgentBase):
    pass


class SecurityAgentUpdate(BaseModel):
    hostname: Optional[str] = None
    ip_address: Optional[str] = None
    status: Optional[str] = None
    last_checkin: Optional[datetime] = None