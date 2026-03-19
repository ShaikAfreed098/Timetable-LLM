from sqlalchemy import Column, Integer, String, Enum
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
    room_number = Column(String, unique=True, nullable=False, index=True)
    capacity = Column(Integer, default=60)
    type = Column(String, default=RoomType.classroom)
    floor = Column(Integer, default=1)
    building = Column(String, default="Main")

    timetable_slots = relationship("TimetableSlot", back_populates="room")
