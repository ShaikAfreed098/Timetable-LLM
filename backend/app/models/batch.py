from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base


class Batch(Base):
    __tablename__ = "batches"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)          # e.g. "CSE-A"
    department = Column(String, nullable=False)
    semester = Column(Integer, nullable=False)
    student_count = Column(Integer, default=60)
    year = Column(Integer, nullable=False)

    assignments = relationship("Assignment", back_populates="batch", cascade="all, delete-orphan")
    timetable_slots = relationship("TimetableSlot", back_populates="batch")
