from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class Faculty(Base):
    __tablename__ = "faculty"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    department = Column(String, nullable=False)
    email = Column(String, nullable=False) # Not unique globally now
    max_periods_per_day = Column(Integer, default=5)
    preferred_days = Column(JSON, default=list)        # e.g. ["Monday", "Tuesday"]
    unavailable_slots = Column(JSON, default=list)     # e.g. [{"day": "Friday", "period": 5}]
    is_active = Column(Boolean, default=True)

    institution = relationship("Institution", back_populates="faculties")
    assignments = relationship("Assignment", back_populates="faculty", cascade="all, delete-orphan")
    timetable_slots = relationship("TimetableSlot", back_populates="faculty")
