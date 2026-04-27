from sqlalchemy import Column, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.database import Base


class ScheduleConfig(Base):
    __tablename__ = "schedule_configs"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), unique=True, nullable=False, index=True)
    
    # E.g. ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    working_days = Column(JSON, nullable=False, default=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
    
    # E.g. 7
    periods_per_day = Column(Integer, nullable=False, default=7)
    
    # Dict mapping period number to time range e.g. {"1": "09:10-10:00", "2": "10:00-10:50"}
    period_times = Column(JSON, nullable=False, default={})

    institution = relationship("Institution", back_populates="schedule_config")
