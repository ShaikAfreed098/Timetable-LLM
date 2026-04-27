from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict

from app.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.config import ScheduleConfig

router = APIRouter(prefix="/config", tags=["config"])

class ScheduleConfigBase(BaseModel):
    working_days: List[str]
    periods_per_day: int
    period_times: Dict[str, str]

@router.get("/schedule", response_model=ScheduleConfigBase)
def get_schedule_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    config = db.query(ScheduleConfig).filter(ScheduleConfig.institution_id == current_user.institution_id).first()
    if not config:
        # Return default if not explicitly found
        return {
            "working_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
            "periods_per_day": 7,
            "period_times": {"1": "09:10-10:00", "2": "10:00-10:50", "3": "11:00-11:50", "4": "11:50-12:40", "5": "13:30-14:20", "6": "14:20-15:10", "7": "15:10-16:00"}
        }
    return {
        "working_days": config.working_days,
        "periods_per_day": config.periods_per_day,
        "period_times": config.period_times
    }

@router.post("/schedule", response_model=ScheduleConfigBase)
def update_schedule_config(
    payload: ScheduleConfigBase,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    config = db.query(ScheduleConfig).filter(ScheduleConfig.institution_id == current_user.institution_id).first()
    if not config:
        config = ScheduleConfig(
            institution_id=current_user.institution_id,
            working_days=payload.working_days,
            periods_per_day=payload.periods_per_day,
            period_times=payload.period_times
        )
        db.add(config)
    else:
        config.working_days = payload.working_days
        config.periods_per_day = payload.periods_per_day
        config.period_times = payload.period_times
    db.commit()
    db.refresh(config)
    return {
        "working_days": config.working_days,
        "periods_per_day": config.periods_per_day,
        "period_times": config.period_times
    }
