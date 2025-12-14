from datetime import datetime, UTC

from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db.database import Base


class SecurityAgent(Base):
    __tablename__ = "security_agents"

    # Primary identifier for the security agent
    agent_id: Mapped[str] = mapped_column(String, primary_key=True, index=True)

    # Network details
    hostname: Mapped[str] = mapped_column(String, nullable=False)
    ip_address: Mapped[str] = mapped_column(String, nullable=False)

    # Operational status and monitoring
    status: Mapped[str] = mapped_column(String, nullable=False, default="offline")
    last_checkin: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))