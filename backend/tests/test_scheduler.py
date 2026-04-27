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
from app.models.config import ScheduleConfig
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
