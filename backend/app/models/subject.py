from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from app.database import Base


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    code = Column(String, unique=True, nullable=False, index=True)
    department = Column(String, nullable=False)
    credits = Column(Integer, default=3)
    periods_per_week = Column(Integer, default=3)
    requires_lab = Column(Boolean, default=False)

    assignments = relationship("Assignment", back_populates="subject", cascade="all, delete-orphan")
    timetable_slots = relationship("TimetableSlot", back_populates="subject")
