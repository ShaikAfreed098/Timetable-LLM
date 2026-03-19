from sqlalchemy import Column, Integer, String, JSON
from app.database import Base


class Constraint(Base):
    __tablename__ = "constraints"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, nullable=False)           # "hard" | "soft"
    entity_type = Column(String, nullable=False)    # "faculty" | "room" | "batch" | "global"
    entity_id = Column(Integer, nullable=True)      # FK to the relevant entity
    description = Column(String, nullable=False)
    parameters_json = Column(JSON, default=dict)
