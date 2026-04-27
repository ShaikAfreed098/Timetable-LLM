from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class AuditLog(Base):
    """Tracks important actions for compliance and debugging."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String, nullable=False, index=True)  # e.g. "timetable.generate", "faculty.create"
    entity_type = Column(String, nullable=True)           # e.g. "faculty", "timetable"
    entity_id = Column(String, nullable=True)             # ID of the affected entity
    details = Column(JSON, default=dict)                  # Additional context
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    institution = relationship("Institution")
    user = relationship("User")
