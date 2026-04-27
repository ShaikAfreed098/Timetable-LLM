from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class Assignment(Base):
    """Faculty-Subject-Batch assignment."""
    __tablename__ = "assignments"
    __table_args__ = (
        UniqueConstraint("institution_id", "faculty_id", "subject_id", "batch_id", name="uq_assignment"),
    )

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False, index=True)
    faculty_id = Column(Integer, ForeignKey("faculty.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=False)
    semester = Column(Integer, nullable=False)

    institution = relationship("Institution", back_populates="assignments")
    faculty = relationship("Faculty", back_populates="assignments")
    subject = relationship("Subject", back_populates="assignments")
    batch = relationship("Batch", back_populates="assignments")


class TimetableSlot(Base):
    """A single cell in the generated timetable."""
    __tablename__ = "timetable_slots"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False, index=True)
    timetable_id = Column(String, nullable=False, index=True)  # UUID string grouping a full timetable run
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=False)
    day_of_week = Column(String, nullable=False)      # "Monday" … "Friday"
    period_number = Column(Integer, nullable=False)   # 1–7 (teaching periods only)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    faculty_id = Column(Integer, ForeignKey("faculty.id"), nullable=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=True)
    slot_type = Column(String, default="class")       # "class" | "break" | "lunch"

    institution = relationship("Institution", back_populates="timetable_slots")
    batch = relationship("Batch", back_populates="timetable_slots")
    subject = relationship("Subject", back_populates="timetable_slots")
    faculty = relationship("Faculty", back_populates="timetable_slots")
    room = relationship("Room", back_populates="timetable_slots")
