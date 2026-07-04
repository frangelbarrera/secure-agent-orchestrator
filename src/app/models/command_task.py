from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
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
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    result: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
