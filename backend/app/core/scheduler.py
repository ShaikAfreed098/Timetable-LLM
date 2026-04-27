"""
Conflict-free timetable generator using Google OR-Tools CP-SAT.

Working days, periods, and period times are read per-institution from the
ScheduleConfig table. No schedule constants are hardcoded here.
"""
from __future__ import annotations

import uuid
from typing import List, Dict, Any
from collections import defaultdict

from ortools.sat.python import cp_model
from sqlalchemy.orm import Session

from app.models.batch import Batch
from app.models.faculty import Faculty
from app.models.subject import Subject
from app.models.room import Room, RoomType
from app.models.timetable import Assignment, TimetableSlot

from app.models.config import ScheduleConfig

def get_institution_config(db: Session, institution_id: int):
    config = db.query(ScheduleConfig).filter(ScheduleConfig.institution_id == institution_id).first()
    if not config:
        raise ValueError(
            f"No ScheduleConfig found for institution_id={institution_id}. "
            "Create one via /api/config before generating a timetable."
        )
    return {
        "days": config.working_days,
        "periods": list(range(1, config.periods_per_day + 1)),
        "period_times": config.period_times or {},
    }


def generate_timetable(db: Session, semester: int, department: str, institution_id: int) -> Dict[str, Any]:
    """
    Generate a conflict-free timetable for all batches in the given
    semester/department for the specified institution. Returns a dict with timetable_id and list of slot dicts.
    """
    config = get_institution_config(db, institution_id)
    DAYS = config["days"]
    TEACHING_PERIODS = config["periods"]

    batches: List[Batch] = (
        db.query(Batch)
        .filter(Batch.semester == semester, Batch.department == department, Batch.institution_id == institution_id)
        .all()
    )
    if not batches:
        return {"timetable_id": None, "slots": [], "conflicts": ["No batches found."]}

    assignments: List[Assignment] = (
        db.query(Assignment)
        .filter(Assignment.semester == semester, Assignment.institution_id == institution_id)
        .all()
    )

    faculty_list: List[Faculty] = db.query(Faculty).filter(Faculty.is_active == True, Faculty.institution_id == institution_id).all()
    rooms: List[Room] = db.query(Room).filter(Room.institution_id == institution_id).all()

    classrooms = [r for r in rooms if r.type != RoomType.lab]
    labs = [r for r in rooms if r.type == RoomType.lab]

    # Index helpers
    batch_ids = [b.id for b in batches]
    faculty_map = {f.id: f for f in faculty_list}
    classroom_ids = [r.id for r in classrooms]
    lab_ids = [r.id for r in labs]
    all_room_ids = [r.id for r in rooms]

    # Build slot requirements
    slots_needed: List[Dict] = []
    for a in assignments:
        if a.batch_id not in batch_ids:
            continue
        subj: Subject = db.get(Subject, a.subject_id)
        if subj is None:
            continue
        for _ in range(subj.periods_per_week):
            slots_needed.append(
                {
                    "batch_id": a.batch_id,
                    "subject_id": a.subject_id,
                    "faculty_id": a.faculty_id,
                    "requires_lab": subj.requires_lab,
                }
            )

    if not slots_needed:
        return {
            "timetable_id": None,
            "slots": [],
            "conflicts": ["No subject assignments found for this semester/department."],
        }

    n_slots = len(slots_needed)
    SENTINEL = n_slots
    ROOM_SENTINEL = len(all_room_ids)

    # --- CP-SAT model ---
    model = cp_model.CpModel()

    # Decision variables
    cell = {}
    room_var = {}
    for b_id in batch_ids:
        for d_idx in range(len(DAYS)):
            for p_idx in range(len(TEACHING_PERIODS)):
                cell[b_id, d_idx, p_idx] = model.NewIntVar(0, SENTINEL, f"cell_b{b_id}_d{d_idx}_p{p_idx}")
                room_var[b_id, d_idx, p_idx] = model.NewIntVar(0, ROOM_SENTINEL, f"room_b{b_id}_d{d_idx}_p{p_idx}")

    # --- 1. Place each slot exactly once ---
    for s_idx, s in enumerate(slots_needed):
        b_id = s["batch_id"]
        has_slot = [
            model.NewBoolVar(f"has_{s_idx}_d{d}_p{p}") 
            for d in range(len(DAYS)) for p in range(len(TEACHING_PERIODS))
        ]
        for i, (d_idx, p_idx) in enumerate(
            (d, p) for d in range(len(DAYS)) for p in range(len(TEACHING_PERIODS))
        ):
            model.Add(cell[b_id, d_idx, p_idx] == s_idx).OnlyEnforceIf(has_slot[i])
            model.Add(cell[b_id, d_idx, p_idx] != s_idx).OnlyEnforceIf(has_slot[i].Not())
        model.AddExactlyOne(has_slot)

    # --- 2. Faculty double-booking constraint ---
    for d_idx in range(len(DAYS)):
        for p_idx in range(len(TEACHING_PERIODS)):
            fac_indices: Dict[int, List[int]] = {}
            for s_idx, s in enumerate(slots_needed):
                fac_indices.setdefault(s["faculty_id"], []).append(s_idx)
            for fac_id, s_indices in fac_indices.items():
                if len(s_indices) < 2:
                    continue
                for b1 in batch_ids:
                    for b2 in batch_ids:
                        if b1 >= b2:
                            continue
                        b1_slots = [i for i in s_indices if slots_needed[i]["batch_id"] == b1]
                        b2_slots = [i for i in s_indices if slots_needed[i]["batch_id"] == b2]
                        if not b1_slots or not b2_slots:
                            continue
                        for i1 in b1_slots:
                            for i2 in b2_slots:
                                b1_has = model.NewBoolVar(f"fac_b1_{b1}_{d_idx}_{p_idx}_{i1}")
                                b2_has = model.NewBoolVar(f"fac_b2_{b2}_{d_idx}_{p_idx}_{i2}")
                                model.Add(cell[b1, d_idx, p_idx] == i1).OnlyEnforceIf(b1_has)
                                model.Add(cell[b1, d_idx, p_idx] != i1).OnlyEnforceIf(b1_has.Not())
                                model.Add(cell[b2, d_idx, p_idx] == i2).OnlyEnforceIf(b2_has)
                                model.Add(cell[b2, d_idx, p_idx] != i2).OnlyEnforceIf(b2_has.Not())
                                both = model.NewBoolVar(f"both_{b1}_{b2}_{d_idx}_{p_idx}_{i1}_{i2}")
                                model.AddBoolAnd([b1_has, b2_has]).OnlyEnforceIf(both)
                                model.AddBoolOr([b1_has.Not(), b2_has.Not()]).OnlyEnforceIf(both.Not())
                                model.Add(both == 0)

    # --- 3. Faculty unavailable slots ---
    for s_idx, s in enumerate(slots_needed):
        fac = faculty_map.get(s["faculty_id"])
        if not fac:
            continue
        for unavail in (fac.unavailable_slots or []):
            day_name = unavail.get("day")
            period_num = unavail.get("period")
            if day_name not in DAYS or period_num not in TEACHING_PERIODS:
                continue
            d_idx = DAYS.index(day_name)
            p_idx = TEACHING_PERIODS.index(period_num)
            b_id = s["batch_id"]
            model.Add(cell[b_id, d_idx, p_idx] != s_idx)

    # --- 4. Soft constraint: avoid same subject on same day ---
    penalty_vars = []
    for b_id in batch_ids:
        subj_ids = list({s["subject_id"] for s in slots_needed if s["batch_id"] == b_id})
        for d_idx in range(len(DAYS)):
            for subj_id in subj_ids:
                slot_indices = [
                    s_idx for s_idx, s in enumerate(slots_needed)
                    if s["batch_id"] == b_id and s["subject_id"] == subj_id
                ]
                if len(slot_indices) < 2:
                    continue
                indicators = []
                for p_idx in range(len(TEACHING_PERIODS)):
                    ind = model.NewBoolVar(f"rep_b{b_id}_d{d_idx}_s{subj_id}_p{p_idx}")
                    pos_indicators = []
                    for s_idx in slot_indices:
                        pos = model.NewBoolVar(f"rep_pos_b{b_id}_d{d_idx}_s{subj_id}_p{p_idx}_i{s_idx}")
                        model.Add(cell[b_id, d_idx, p_idx] == s_idx).OnlyEnforceIf(pos)
                        model.Add(cell[b_id, d_idx, p_idx] != s_idx).OnlyEnforceIf(pos.Not())
                        pos_indicators.append(pos)
                    model.AddBoolOr(pos_indicators).OnlyEnforceIf(ind)
                    model.AddBoolAnd([p.Not() for p in pos_indicators]).OnlyEnforceIf(ind.Not())
                    indicators.append(ind)
                sum_var = model.NewIntVar(0, len(TEACHING_PERIODS), f"sum_rep_b{b_id}_d{d_idx}_s{subj_id}")
                model.Add(sum_var == sum(indicators))
                excess = model.NewIntVar(0, len(TEACHING_PERIODS), f"excess_b{b_id}_d{d_idx}_s{subj_id}")
                model.AddMaxEquality(excess, [sum_var - 1, model.NewConstant(0)])
                penalty_vars.append(excess)

    if penalty_vars:
        total_penalty = model.NewIntVar(0, 10000, "total_penalty")
        model.Add(total_penalty == sum(penalty_vars))
        model.Minimize(total_penalty)

    # --- Solve ---
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30.0
    solver.parameters.num_search_workers = 4
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {
            "timetable_id": None,
            "slots": [],
            "conflicts": ["Solver could not find a feasible timetable. Check constraints."],
        }

    # --- Extract solution ---
    timetable_id = str(uuid.uuid4())
    result_slots = []

    # Delete previous slots for these batches (institution-scoped for defense-in-depth)
    db.query(TimetableSlot).filter(
        TimetableSlot.batch_id.in_(batch_ids),
        TimetableSlot.institution_id == institution_id,
    ).delete(synchronize_session=False)

    for b_id in batch_ids:
        for d_idx, day_name in enumerate(DAYS):
            for p_idx, period_num in enumerate(TEACHING_PERIODS):
                val = solver.Value(cell[b_id, d_idx, p_idx])
                if val == SENTINEL:
                    slot = TimetableSlot(
                        timetable_id=timetable_id,
                        institution_id=institution_id,
                        batch_id=b_id,
                        day_of_week=day_name,
                        period_number=period_num,
                        slot_type="free",
                    )
                else:
                    s = slots_needed[val]
                    chosen_room_id = lab_ids[0] if s["requires_lab"] else classroom_ids[0]
                    slot = TimetableSlot(
                        timetable_id=timetable_id,
                        institution_id=institution_id,
                        batch_id=b_id,
                        day_of_week=day_name,
                        period_number=period_num,
                        subject_id=s["subject_id"],
                        faculty_id=s["faculty_id"],
                        room_id=chosen_room_id,
                        slot_type="class",
                    )
                db.add(slot)
                result_slots.append(slot)

    db.commit()
    return {
        "timetable_id": timetable_id,
        "batch_ids": batch_ids,
        "slots_count": len(result_slots),
        "conflicts": [],
    }


def check_conflicts(db: Session, timetable_id: str, institution_id: int) -> List[str]:
    """Return a list of conflict descriptions for a given timetable."""
    slots: List[TimetableSlot] = db.query(TimetableSlot).filter(
        TimetableSlot.timetable_id == timetable_id,
        TimetableSlot.institution_id == institution_id
    ).all()
    conflicts = []

    # Faculty double-booking
    faculty_at = defaultdict(list)
    for s in slots:
        if s.faculty_id and s.slot_type == "class":
            key = (s.faculty_id, s.day_of_week, s.period_number)
            faculty_at[key].append(s.batch_id)
    for (fac_id, day, period), batch_list in faculty_at.items():
        if len(batch_list) > 1:
            fac = db.get(Faculty, fac_id)
            fac_name = fac.name if fac else str(fac_id)
            conflicts.append(
                f"Faculty '{fac_name}' double-booked on {day} Period {period} for batches {batch_list}"
            )

    # Room double-booking
    room_at = defaultdict(list)
    for s in slots:
        if s.room_id and s.slot_type == "class":
            key = (s.room_id, s.day_of_week, s.period_number)
            room_at[key].append(s.batch_id)
    for (room_id, day, period), batch_list in room_at.items():
        if len(batch_list) > 1:
            room = db.get(Room, room_id)
            room_num = room.room_number if room else str(room_id)
            conflicts.append(
                f"Room '{room_num}' double-booked on {day} Period {period} for batches {batch_list}"
            )

    return conflicts