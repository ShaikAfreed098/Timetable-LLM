"""
Tests for the constraint solver / scheduler.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.faculty import Faculty
from app.models.subject import Subject
from app.models.room import Room
from app.models.batch import Batch
from app.models.timetable import Assignment, TimetableSlot
from app.core.scheduler import generate_timetable, check_conflicts, DAYS, TEACHING_PERIODS

TEST_DB_URL = "sqlite:///./test_scheduler.db"


@pytest.fixture(scope="module")
def db():
    eng = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=eng)
    Session = sessionmaker(bind=eng)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(bind=eng)


def _seed_data(db):
    """Insert minimal data for timetable generation tests."""
    # Faculty
    f1 = Faculty(name="Dr. Alice", department="CSE", email="alice@college.edu", max_periods_per_day=5)
    f2 = Faculty(name="Dr. Bob", department="CSE", email="bob@college.edu", max_periods_per_day=5)
    db.add_all([f1, f2])
    db.flush()

    # Subjects
    s1 = Subject(name="Data Structures", code="CS301", department="CSE", credits=3, periods_per_week=3)
    s2 = Subject(name="Algorithms", code="CS302", department="CSE", credits=3, periods_per_week=3)
    db.add_all([s1, s2])
    db.flush()

    # Room
    r1 = Room(room_number="101", capacity=60, type="classroom")
    db.add(r1)
    db.flush()

    # Batch
    b1 = Batch(name="CSE-A", department="CSE", semester=3, student_count=60, year=2024)
    db.add(b1)
    db.flush()

    # Assignments
    a1 = Assignment(faculty_id=f1.id, subject_id=s1.id, batch_id=b1.id, semester=3)
    a2 = Assignment(faculty_id=f2.id, subject_id=s2.id, batch_id=b1.id, semester=3)
    db.add_all([a1, a2])
    db.commit()

    return {"batch": b1, "faculty": [f1, f2], "subjects": [s1, s2], "room": r1}


def test_generate_timetable_basic(db):
    _seed_data(db)
    result = generate_timetable(db, semester=3, department="CSE")

    assert result["timetable_id"] is not None
    assert len(result["conflicts"]) == 0
    assert result["slots_count"] > 0


def test_teaching_periods_only(db):
    """Generated slots should only use valid teaching period numbers."""
    # Get the timetable id from most recent generation
    slot = db.query(TimetableSlot).first()
    if slot is None:
        pytest.skip("No timetable generated yet")
    all_slots = db.query(TimetableSlot).filter(
        TimetableSlot.timetable_id == slot.timetable_id
    ).all()

    for s in all_slots:
        assert s.period_number in TEACHING_PERIODS, (
            f"Period {s.period_number} is not a valid teaching period"
        )
        assert s.day_of_week in DAYS, f"Day {s.day_of_week} is not a valid weekday"


def test_check_conflicts_no_conflict(db):
    slot = db.query(TimetableSlot).first()
    if slot is None:
        pytest.skip("No timetable generated yet")
    conflicts = check_conflicts(db, slot.timetable_id)
    assert isinstance(conflicts, list)
    # For a fresh generation there should be no conflicts
    assert len(conflicts) == 0


def test_generate_no_batches(db):
    """Requesting an unknown department/semester should return a graceful error."""
    result = generate_timetable(db, semester=99, department="UNKNOWN")
    assert result["timetable_id"] is None
    assert len(result["conflicts"]) > 0


def test_faculty_unavailable_slot_respected(db):
    """A faculty's unavailable slot should not appear in the generated timetable."""
    # Mark Dr. Alice as unavailable on Monday Period 1
    alice = db.query(Faculty).filter(Faculty.email == "alice@college.edu").first()
    if alice is None:
        pytest.skip("Seed data not present")
    alice.unavailable_slots = [{"day": "Monday", "period": 1}]
    db.commit()

    result = generate_timetable(db, semester=3, department="CSE")
    timetable_id = result["timetable_id"]

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
