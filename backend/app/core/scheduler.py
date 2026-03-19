"""
Conflict-free timetable generator using Google OR-Tools CP-SAT.

College schedule:
  P1  09:10–10:00
  P2  10:00–10:50
  Break 10:50–11:00  (skipped)
  P3  11:00–11:50
  P4  11:50–12:40
  Lunch 12:40–13:30  (skipped)
  P5  13:30–14:20
  P6  14:20–15:10
  P7  15:10–16:00
"""
from __future__ import annotations

import uuid
from typing import List, Dict, Any

from ortools.sat.python import cp_model
from sqlalchemy.orm import Session

from app.models.batch import Batch
from app.models.faculty import Faculty
from app.models.subject import Subject
from app.models.room import Room, RoomType
from app.models.timetable import Assignment, TimetableSlot

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
TEACHING_PERIODS = [1, 2, 3, 4, 5, 6, 7]

PERIOD_TIMES = {
    1: "09:10–10:00",
    2: "10:00–10:50",
    3: "11:00–11:50",
    4: "11:50–12:40",
    5: "13:30–14:20",
    6: "14:20–15:10",
    7: "15:10–16:00",
}


def generate_timetable(
    db: Session,
    semester: int,
    department: str,
) -> Dict[str, Any]:
    """
    Generate a conflict-free timetable for all batches in the given
    semester/department.  Returns a dict with timetable_id and list of slot dicts.
    """
    batches: List[Batch] = (
        db.query(Batch)
        .filter(Batch.semester == semester, Batch.department == department)
        .all()
    )
    if not batches:
        return {"timetable_id": None, "slots": [], "conflicts": ["No batches found."]}

    assignments: List[Assignment] = (
        db.query(Assignment)
        .filter(Assignment.semester == semester)
        .all()
    )

    faculty_list: List[Faculty] = db.query(Faculty).filter(Faculty.is_active == True).all()
    rooms: List[Room] = db.query(Room).all()

    classrooms = [r for r in rooms if r.type != RoomType.lab]
    labs = [r for r in rooms if r.type == RoomType.lab]

    # Index helpers
    batch_ids = [b.id for b in batches]
    faculty_map = {f.id: f for f in faculty_list}
    classroom_ids = [r.id for r in classrooms]
    lab_ids = [r.id for r in labs]

    # Build (batch_id, subject_id, faculty_id, requires_lab) tuples
    # Each assignment may need multiple slots per week (periods_per_week)
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

    # Total grid cells per batch: 5 days × 7 periods = 35
    total_cells = len(DAYS) * len(TEACHING_PERIODS)
    n_slots = len(slots_needed)

    # --- CP-SAT model --------------------------------------------------
    model = cp_model.CpModel()

    # Decision variable: for each (batch, day, period) → assignment index (0-based) or -1 (free)
    # We encode "free" as n_slots (a sentinel value)
    SENTINEL = n_slots

    cell = {}  # (batch_id, day_idx, period_idx) → IntVar in [0, SENTINEL]
    for b_id in batch_ids:
        for d_idx, _ in enumerate(DAYS):
            for p_idx, _ in enumerate(TEACHING_PERIODS):
                cell[b_id, d_idx, p_idx] = model.NewIntVar(
                    0, SENTINEL, f"cell_b{b_id}_d{d_idx}_p{p_idx}"
                )

    # Room assignment variable: (batch_id, day_idx, period_idx) → room_id index or -1
    room_var = {}
    all_room_ids = [r.id for r in rooms]
    ROOM_SENTINEL = len(all_room_ids)
    for b_id in batch_ids:
        for d_idx in range(len(DAYS)):
            for p_idx in range(len(TEACHING_PERIODS)):
                room_var[b_id, d_idx, p_idx] = model.NewIntVar(
                    0, ROOM_SENTINEL, f"room_b{b_id}_d{d_idx}_p{p_idx}"
                )

    # 1. Each assignment slot must be placed exactly once
    for s_idx, s in enumerate(slots_needed):
        b_id = s["batch_id"]
        cells_for_batch = [
            cell[b_id, d_idx, p_idx]
            for d_idx in range(len(DAYS))
            for p_idx in range(len(TEACHING_PERIODS))
        ]
        # At least one cell equals s_idx
        has_slot = [model.NewBoolVar(f"has_{s_idx}_d{d}_p{p}") for d in range(len(DAYS)) for p in range(len(TEACHING_PERIODS))]
        for i, (d_idx, p_idx) in enumerate(
            (d, p) for d in range(len(DAYS)) for p in range(len(TEACHING_PERIODS))
        ):
            model.Add(cell[b_id, d_idx, p_idx] == s_idx).OnlyEnforceIf(has_slot[i])
            model.Add(cell[b_id, d_idx, p_idx] != s_idx).OnlyEnforceIf(has_slot[i].Not())
        model.AddExactlyOne(has_slot)

    # 2. Each (batch, day, period) cell holds at most one assignment (already guaranteed by
    #    the IntVar encoding since each cell has a single value).

    # 3. Faculty cannot be double-booked: no two cells with same faculty_id at same (day, period)
    for d_idx in range(len(DAYS)):
        for p_idx in range(len(TEACHING_PERIODS)):
            # Group slots by faculty
            fac_indices: Dict[int, List[int]] = {}
            for s_idx, s in enumerate(slots_needed):
                fac_id = s["faculty_id"]
                fac_indices.setdefault(fac_id, []).append(s_idx)

            for fac_id, s_indices in fac_indices.items():
                if len(s_indices) < 2:
                    continue
                # For each pair of batches, they cannot both have a slot from this faculty
                # at this (day, period)
                for b1 in batch_ids:
                    for b2 in batch_ids:
                        if b1 >= b2:
                            continue
                        b1_slots_for_fac = [i for i in s_indices if slots_needed[i]["batch_id"] == b1]
                        b2_slots_for_fac = [i for i in s_indices if slots_needed[i]["batch_id"] == b2]
                        if not b1_slots_for_fac or not b2_slots_for_fac:
                            continue
                        for i1 in b1_slots_for_fac:
                            for i2 in b2_slots_for_fac:
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

    # 4. Faculty unavailable slots
    for s_idx, s in enumerate(slots_needed):
        fac = faculty_map.get(s["faculty_id"])
        if fac is None:
            continue
        for unavail in (fac.unavailable_slots or []):
            day_name = unavail.get("day")
            period_num = unavail.get("period")
            if day_name not in DAYS:
                continue
            d_idx = DAYS.index(day_name)
            if period_num not in TEACHING_PERIODS:
                continue
            p_idx = TEACHING_PERIODS.index(period_num)
            b_id = s["batch_id"]
            model.Add(cell[b_id, d_idx, p_idx] != s_idx)

    # 5. Soft constraint: avoid same subject on the same day for a batch
    # (implemented as a minimization objective — penalize repeated subjects)
    penalty_vars = []
    for b_id in batch_ids:
        subj_ids = list({s["subject_id"] for s in slots_needed if s["batch_id"] == b_id})
        for d_idx in range(len(DAYS)):
            for subj_id in subj_ids:
                slot_indices_for_subj = [
                    s_idx for s_idx, s in enumerate(slots_needed)
                    if s["batch_id"] == b_id and s["subject_id"] == subj_id
                ]
                if len(slot_indices_for_subj) < 2:
                    continue
                # count how many periods on this day have this subject
                indicators = []
                for p_idx in range(len(TEACHING_PERIODS)):
                    ind = model.NewBoolVar(f"rep_b{b_id}_d{d_idx}_s{subj_id}_p{p_idx}")
                    # ind is true iff cell[b_id, d_idx, p_idx] matches ANY slot index for this subject
                    pos_indicators = []
                    for s_idx in slot_indices_for_subj:
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

    # --- Solve ---------------------------------------------------------
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

    # --- Extract solution ----------------------------------------------
    timetable_id = str(uuid.uuid4())
    result_slots = []

    # Delete previous slots for these batches (same semester/dept) if any
    db.query(TimetableSlot).filter(
        TimetableSlot.batch_id.in_(batch_ids)
    ).delete(synchronize_session=False)

    for b_id in batch_ids:
        for d_idx, day_name in enumerate(DAYS):
            for p_idx, period_num in enumerate(TEACHING_PERIODS):
                val = solver.Value(cell[b_id, d_idx, p_idx])
                if val == SENTINEL:
                    # Free / unassigned period
                    slot = TimetableSlot(
                        timetable_id=timetable_id,
                        batch_id=b_id,
                        day_of_week=day_name,
                        period_number=period_num,
                        slot_type="free",
                    )
                else:
                    s = slots_needed[val]
                    # Pick a room
                    if s["requires_lab"]:
                        chosen_room_id = lab_ids[0] if lab_ids else (all_room_ids[0] if all_room_ids else None)
                    else:
                        chosen_room_id = classroom_ids[0] if classroom_ids else (all_room_ids[0] if all_room_ids else None)

                    slot = TimetableSlot(
                        timetable_id=timetable_id,
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


def check_conflicts(db: Session, timetable_id: str) -> List[str]:
    """Return a list of conflict descriptions for a given timetable."""
    slots: List[TimetableSlot] = (
        db.query(TimetableSlot).filter(TimetableSlot.timetable_id == timetable_id).all()
    )
    conflicts = []

    # Check faculty double-booking
    from collections import defaultdict
    faculty_at = defaultdict(list)  # (faculty_id, day, period) → [batch_id]
    for s in slots:
        if s.faculty_id is not None and s.slot_type == "class":
            key = (s.faculty_id, s.day_of_week, s.period_number)
            faculty_at[key].append(s.batch_id)

    for (fac_id, day, period), batch_ids_list in faculty_at.items():
        if len(batch_ids_list) > 1:
            fac = db.get(Faculty, fac_id)
            fac_name = fac.name if fac else str(fac_id)
            conflicts.append(
                f"Faculty '{fac_name}' double-booked on {day} Period {period} "
                f"for batches {batch_ids_list}"
            )

    # Check room double-booking
    room_at = defaultdict(list)
    for s in slots:
        if s.room_id is not None and s.slot_type == "class":
            key = (s.room_id, s.day_of_week, s.period_number)
            room_at[key].append(s.batch_id)

    for (room_id, day, period), batch_ids_list in room_at.items():
        if len(batch_ids_list) > 1:
            room = db.get(Room, room_id)
            room_num = room.room_number if room else str(room_id)
            conflicts.append(
                f"Room '{room_num}' double-booked on {day} Period {period} "
                f"for batches {batch_ids_list}"
            )

    return conflicts
