from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    code = Column(String, nullable=False, index=True) # Not unique globally now
    department = Column(String, nullable=False)
    credits = Column(Integer, default=3)
    periods_per_week = Column(Integer, default=3)
    requires_lab = Column(Boolean, default=False)

    institution = relationship("Institution", back_populates="subjects")
    assignments = relationship("Assignment", back_populates="subject", cascade="all, delete-orphan")
    timetable_slots = relationship("TimetableSlot", back_populates="subject")
