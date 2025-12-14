from datetime import datetime, UTC
from typing import Optional

from sqlalchemy import String, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db.database import Base


class CommandTask(Base):
    __tablename__ = "command_tasks"

    # Unique task identifier
    task_id: Mapped[str] = mapped_column(String, primary_key=True, index=True)

    # Link to the executing agent
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("security_agents.agent_id"), nullable=False)

    # Command details and execution tracking
    command: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)