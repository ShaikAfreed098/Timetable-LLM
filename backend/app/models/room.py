from sqlalchemy import Column, Integer, String, Enum, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class RoomType(str, enum.Enum):
    classroom = "classroom"
    lab = "lab"
    seminar = "seminar"


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False, index=True)
    room_number = Column(String, nullable=False, index=True) # Not globally unique
    capacity = Column(Integer, default=60)
    type = Column(String, default=RoomType.classroom)
    floor = Column(Integer, default=1)
    building = Column(String, default="Main")

    institution = relationship("Institution", back_populates="rooms")
    timetable_slots = relationship("TimetableSlot", back_populates="room")
