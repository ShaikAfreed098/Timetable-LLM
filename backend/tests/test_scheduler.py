"""
Tests for the constraint solver / scheduler.
Uses the shared conftest.py fixtures (which set up SQLite).
"""
import pytest

from app.models.faculty import Faculty
from app.models.subject import Subject
from app.models.room import Room
from app.models.batch import Batch
from app.models.timetable import Assignment, TimetableSlot
from app.models.institution import Institution
from app.core.scheduler import generate_timetable, check_conflicts, get_institution_config


@pytest.fixture()
def scheduler_data(db):
    """Seed data for scheduler tests within a clean transaction."""
    inst = db.query(Institution).first()

    # Faculty
    f1 = Faculty(name="Dr. Alice", department="CSE", email="alice_sched@college.edu",
                 max_periods_per_day=5, institution_id=inst.id)
    f2 = Faculty(name="Dr. Bob", department="CSE", email="bob_sched@college.edu",
                 max_periods_per_day=5, institution_id=inst.id)
    db.add_all([f1, f2])
    db.flush()

    # Subjects
    s1 = Subject(name="Data Structures", code="CS301S", department="CSE",
                 credits=3, periods_per_week=3, institution_id=inst.id)
    s2 = Subject(name="Algorithms", code="CS302S", department="CSE",
                 credits=3, periods_per_week=3, institution_id=inst.id)
    db.add_all([s1, s2])
    db.flush()

    # Room
    r1 = Room(room_number="SCHED-101", capacity=60, type="classroom", institution_id=inst.id)
    db.add(r1)
    db.flush()

    # Batch
    b1 = Batch(name="CSE-SCHED-A", department="CSE", semester=3,
               student_count=60, year=2024, institution_id=inst.id)
    db.add(b1)
    db.flush()

    # Assignments
    a1 = Assignment(faculty_id=f1.id, subject_id=s1.id, batch_id=b1.id,
                    semester=3, institution_id=inst.id)
    a2 = Assignment(faculty_id=f2.id, subject_id=s2.id, batch_id=b1.id,
                    semester=3, institution_id=inst.id)
    db.add_all([a1, a2])
    db.commit()

    return {"institution": inst, "batch": b1, "faculty": [f1, f2],
            "subjects": [s1, s2], "room": r1}


def test_generate_timetable_basic(db, scheduler_data):
    inst = scheduler_data["institution"]
    result = generate_timetable(db, semester=3, department="CSE", institution_id=inst.id)

    assert result["timetable_id"] is not None
    assert len(result["conflicts"]) == 0
    assert result["slots_count"] > 0


def test_teaching_periods_only(db, scheduler_data):
    """Generated slots should only use valid teaching period numbers."""
    inst = scheduler_data["institution"]
    # Generate first
    result = generate_timetable(db, semester=3, department="CSE", institution_id=inst.id)
    tid = result["timetable_id"]
    if tid is None:
        pytest.skip("No timetable generated")

    config = get_institution_config(db, inst.id)
    DAYS = config["days"]
    TEACHING_PERIODS = config["periods"]

    all_slots = db.query(TimetableSlot).filter(
        TimetableSlot.timetable_id == tid
    ).all()

    for s in all_slots:
        assert s.period_number in TEACHING_PERIODS, (
            f"Period {s.period_number} is not a valid teaching period"
        )
        assert s.day_of_week in DAYS, f"Day {s.day_of_week} is not a valid weekday"


def test_check_conflicts_returns_list(db, scheduler_data):
    """check_conflicts should return a list of strings."""
    inst = scheduler_data["institution"]
    result = generate_timetable(db, semester=3, department="CSE", institution_id=inst.id)
    tid = result["timetable_id"]
    if tid is None:
        pytest.skip("No timetable generated")
    conflicts = check_conflicts(db, tid, inst.id)
    assert isinstance(conflicts, list)
    # Each conflict should be a descriptive string
    for c in conflicts:
        assert isinstance(c, str)


def test_generate_no_batches(db, scheduler_data):
    """Requesting an unknown department/semester should return a graceful error."""
    inst = scheduler_data["institution"]
    result = generate_timetable(db, semester=99, department="UNKNOWN", institution_id=inst.id)
    assert result["timetable_id"] is None
    assert len(result["conflicts"]) > 0


def test_faculty_unavailable_slot_respected(db, scheduler_data):
    """A faculty's unavailable slot should not appear in the generated timetable."""
    inst = scheduler_data["institution"]
    alice = scheduler_data["faculty"][0]
    alice.unavailable_slots = [{"day": "Monday", "period": 1}]
    db.commit()

    result = generate_timetable(db, semester=3, department="CSE", institution_id=inst.id)
    timetable_id = result["timetable_id"]
    if timetable_id is None:
        pytest.skip("No timetable generated")

    monday_p1_slots = (
        db.query(TimetableSlot)
        .filter(
            TimetableSlot.timetable_id == timetable_id,
            TimetableSlot.day_of_week == "Monday",
            TimetableSlot.period_number == 1,
            TimetableSlot.faculty_id == alice.id,
        )
        .all()
    )
    assert len(monday_p1_slots) == 0, "Faculty should not be scheduled during unavailable slot"


def test_capacity_mismatch_aborts(db, scheduler_data):
    """If no room is big enough for a batch, generation should abort."""
    inst = scheduler_data["institution"]
    # Create a NEW batch that is too big for our 60-seat room
    # Use a completely unique department to avoid picking up other batches
    b_huge = Batch(name="HUGE-BATCH", department="HUGE-DEPT", semester=1,
                   student_count=100, year=2024, institution_id=inst.id)
    db.add(b_huge)
    # Subject that requires classroom
    s_huge = Subject(name="Huge Subject", code="HUGE101", department="HUGE-DEPT",
                     credits=3, periods_per_week=1, institution_id=inst.id)
    db.add(s_huge)
    db.flush()
    # Assignment for huge batch
    a_huge = Assignment(faculty_id=scheduler_data["faculty"][0].id, 
                        subject_id=s_huge.id, 
                        batch_id=b_huge.id,
                        semester=1, institution_id=inst.id)
    db.add(a_huge)
    db.commit()

    result = generate_timetable(db, semester=1, department="HUGE-DEPT", institution_id=inst.id)
    assert result["timetable_id"] is None
    assert any("Batch 'HUGE-BATCH'" in c for c in result["conflicts"])
    assert any("no suitable classroom" in c for c in result["conflicts"])
    # In the seeded data, we have one 60-seat room. 
    # Let's verify that's the max_cap reported.
    assert any("largest available capacity is 60" in c for c in result["conflicts"])


def test_capacity_picks_eligible_room(db, scheduler_data):
    """A batch should be assigned to an eligible room (capacity >= students)."""
    inst = scheduler_data["institution"]
    # Use a new department to isolate
    b_pick = Batch(name="PICK-BATCH", department="PICK-DEPT", semester=1,
                   student_count=70, year=2024, institution_id=inst.id)
    db.add(b_pick)
    # Add a small room and a big room
    r_small = Room(room_number="SMALL", capacity=30, type="classroom", institution_id=inst.id)
    r_big = Room(room_number="BIG", capacity=80, type="classroom", institution_id=inst.id)
    db.add_all([r_small, r_big])
    # Subject
    s_pick = Subject(name="Pick Subject", code="PICK101", department="PICK-DEPT",
                     credits=3, periods_per_week=1, institution_id=inst.id)
    db.add(s_pick)
    db.flush()
    # Assignment
    a_pick = Assignment(faculty_id=scheduler_data["faculty"][0].id, 
                        subject_id=s_pick.id, 
                        batch_id=b_pick.id,
                        semester=1, institution_id=inst.id)
    db.add(a_pick)
    db.commit()

    # Batch has 60 students, should pick BIG (60 fits in 80, not 30)
    result = generate_timetable(db, semester=1, department="PICK-DEPT", institution_id=inst.id)
    assert result["timetable_id"] is not None
    
    slots = db.query(TimetableSlot).filter(
        TimetableSlot.timetable_id == result["timetable_id"], 
        TimetableSlot.slot_type == "class"
    ).all()
    assert len(slots) > 0
    for s in slots:
        room = db.get(Room, s.room_id)
        assert room.room_number == "BIG"


def test_weekly_workload_exceeded(db, scheduler_data):
    """If a faculty member's total periods per week exceed the cap, generation should abort."""
    inst = scheduler_data["institution"]
    # Alice already has 3 periods (from DS). Add a subject with 20 periods to exceed the cap of 18.
    s_heavy = Subject(name="Heavy Subject", code="HVY101", department="CSE",
                      credits=10, periods_per_week=20, institution_id=inst.id)
    db.add(s_heavy)
    db.flush()
    
    # New batch and assignment for heavy subject
    b_heavy = Batch(name="HEAVY-BATCH", department="HEAVY-CSE", semester=3,
                    student_count=20, year=2024, institution_id=inst.id)
    db.add(b_heavy)
    db.flush()
    a_heavy = Assignment(faculty_id=scheduler_data["faculty"][0].id, # Alice
                         subject_id=s_heavy.id, 
                         batch_id=b_heavy.id,
                         semester=3, institution_id=inst.id)
    db.add(a_heavy)
    db.commit()

    result = generate_timetable(db, semester=3, department="CSE", institution_id=inst.id)
    assert result["timetable_id"] is None
    assert any("exceeds weekly workload cap" in c for c in result["conflicts"])
    assert any("assigned 23" in c for c in result["conflicts"]) # 3 from DS + 20 from heavy
