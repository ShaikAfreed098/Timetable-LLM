import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.faculty import Faculty
from app.models.subject import Subject
from app.models.room import Room, RoomType
from app.models.batch import Batch
from app.models.timetable import Assignment

def get_slots(time_str):
    mapping = {
        "8-10": [1],
        "9-11": [1, 2],
        "10-12": [2, 3],
        "12-14": [4, 5],
        "14-16": [6, 7],
    }
    slots = []
    if not time_str:
        return []
    comps = [c.strip() for c in time_str.split(",")]
    days = {"Mon": "Monday", "Tue": "Tuesday", "Wed": "Wednesday", "Thu": "Thursday", "Fri": "Friday"}
    for c in comps:
        parts = c.split(" ")
        if len(parts) == 2:
            day_short, time = parts
            day = days.get(day_short)
            periods = mapping.get(time, [])
            for p in periods:
                slots.append({"day": day, "period": p})
    return slots

def seed_data():
    db = SessionLocal()
    
    faculties_data = [
        ("Prof. Smith", "CS", "smith@college.edu", "Mon 9-11, Wed 14-16", 4),
        ("Prof. Lee", "CS", "lee@college.edu", "Tue 10-12", 3),
        ("Prof. Kumar", "Mechanical", "kumar@college.edu", "Thu 8-10", 4),
        ("Prof. Sharma", "Electrical", "sharma@college.edu", "Mon 8-10", 4),
        ("Prof. Rao", "Civil", "rao@college.edu", "Wed 9-11", 3),
        ("Prof. Iyer", "CS", "iyer@college.edu", "Tue 14-16", 3),
        ("Prof. Nair", "Mechanical", "nair@college.edu", "Thu 12-14", 4),
        ("Prof. Gupta", "Electrical", "gupta@college.edu", "Mon 10-12", 4),
        ("Prof. Banerjee", "CS", "banerjee@college.edu", "Fri 8-10", 3),
        ("Prof. Fernandes", "Civil", "fernandes@college.edu", "Tue 8-10", 4),
    ]
    fac_objs = {}
    for name, dept, email, slots_str, mx in faculties_data:
        f = Faculty(name=name, department=dept, email=email, 
                    unavailable_slots=get_slots(slots_str),
                    max_periods_per_day=mx)
        db.add(f)
        db.commit()
        db.refresh(f)
        fac_objs[name] = f

    subjects_data = [
        ("Data Structures", "CS201", "CS", 3, False),
        ("Algorithms", "CS202", "CS", 3, False),
        ("Operating Systems", "CS203", "CS", 3, False),
        ("Computer Networks", "CS204", "CS", 3, False),
        ("Software Engineering", "CS205", "CS", 3, False),
        ("Database Lab", "CS206L", "CS", 1, True),
        ("Thermodynamics", "ME301", "Mechanical", 4, False),
        ("Fluid Mechanics", "ME302", "Mechanical", 3, False),
        ("Electrical Circuits", "EE301", "Electrical", 4, False),
        ("Control Systems", "EE302", "Electrical", 3, False),
        ("Strength of Materials", "CE301", "Civil", 4, False),
        ("Survey Lab", "CE302L", "Civil", 1, True),
        ("Computer Lab", "CS207L", "CS", 1, True),
        ("Microprocessors", "EE303", "Electrical", 3, False),
        ("Machine Design", "ME303", "Mechanical", 3, False),
    ]
    sub_objs = {}
    for name, code, dept, credits, req_lab in subjects_data:
        s = Subject(name=name, code=code, department=dept, credits=credits, periods_per_week=credits, requires_lab=req_lab)
        db.add(s)
        db.commit()
        db.refresh(s)
        sub_objs[name] = s

    rooms_data = [
        ("C101", 40, "classroom"),
        ("C102", 35, "classroom"),
        ("L201", 25, "lab"),
        ("L202", 20, "lab"),
        ("L203", 30, "lab"),
        ("M301", 50, "classroom"),
        ("E401", 40, "classroom"),
        ("E402", 35, "classroom"),
        ("CE501", 50, "classroom"),
        ("CE502", 25, "lab"),
    ]
    for rn, cap, t in rooms_data:
        room_type = RoomType.classroom if t == "Classroom" else RoomType.lab
        r = Room(room_number=rn, capacity=cap, type=room_type)
        db.add(r)
    db.commit()

    batches_data = [
        ("CS Sem 3", 38, "CS", 3, 2),
        ("CS Sem 4", 40, "CS", 4, 2),
        ("ME Sem 5", 42, "Mechanical", 5, 3),
        ("ME Sem 6", 45, "Mechanical", 6, 3),
        ("EE Sem 3", 35, "Electrical", 3, 2),
        ("CE Sem 5", 40, "Civil", 5, 3),
    ]
    bat_objs = {}
    for name, count, dept, sem, year in batches_data:
        b = Batch(name=name, student_count=count, department=dept, semester=sem, year=year)
        db.add(b)
        db.commit()
        db.refresh(b)
        bat_objs[name] = b

    assignments_data = [
        ("Prof. Smith", "Data Structures", "CS Sem 3"),
        ("Prof. Lee", "Algorithms", "CS Sem 3"),
        ("Prof. Iyer", "Operating Systems", "CS Sem 4"),
        ("Prof. Banerjee", "Computer Networks", "CS Sem 4"),
        ("Prof. Smith", "Software Engineering", "CS Sem 3"),
        ("Prof. Smith", "Computer Lab", "CS Sem 3"),
        ("Prof. Kumar", "Thermodynamics", "ME Sem 5"),
        ("Prof. Nair", "Fluid Mechanics", "ME Sem 6"),
        ("Prof. Rao", "Strength of Materials", "CE Sem 5"),
        ("Prof. Fernandes", "Survey Lab", "CE Sem 5"),
        ("Prof. Sharma", "Electrical Circuits", "EE Sem 3"),
        ("Prof. Gupta", "Control Systems", "EE Sem 3"),
        ("Prof. Gupta", "Microprocessors", "EE Sem 3"),
        ("Prof. Kumar", "Machine Design", "ME Sem 5"),
        ("Prof. Smith", "Database Lab", "CS Sem 4"),
    ]
    for f_n, s_n, b_n in assignments_data:
        fac = fac_objs[f_n]
        sub = sub_objs[s_n]
        bat = bat_objs[b_n]
        a = Assignment(faculty_id=fac.id, subject_id=sub.id, batch_id=bat.id, semester=bat.semester)
        db.add(a)
    db.commit()

    print("Database seeded successfully with baseline data!")

if __name__ == "__main__":
    seed_data()
