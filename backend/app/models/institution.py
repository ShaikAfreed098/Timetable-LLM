from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from app.database import Base

class Institution(Base):
    __tablename__ = "institutions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=False)
    grouping_scheme = Column(String, default="batch", nullable=False)  # batch, class, or section
    is_active = Column(Boolean, default=True)

    users = relationship("User", back_populates="institution")
    faculties = relationship("Faculty", back_populates="institution")
    subjects = relationship("Subject", back_populates="institution")
    rooms = relationship("Room", back_populates="institution")
    batches = relationship("Batch", back_populates="institution")
    assignments = relationship("Assignment", back_populates="institution")
    timetable_slots = relationship("TimetableSlot", back_populates="institution")
    invites = relationship("Invite", back_populates="institution")
    schedule_config = relationship("ScheduleConfig", back_populates="institution", uselist=False)
