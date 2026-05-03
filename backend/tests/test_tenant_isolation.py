"""
Multi-tenant isolation tests.

These are the most important tests in the suite: they verify that no endpoint
leaks data from one institution to another. Every new CRUD endpoint MUST be
covered here.
"""
import pytest
from datetime import timedelta

from app.core.auth import create_access_token
from app.models.institution import Institution
from app.models.user import User
from app.models.config import ScheduleConfig
from app.models.faculty import Faculty
from app.models.subject import Subject
from app.models.room import Room
from app.models.batch import Batch
from app.models.timetable import Assignment
from app.models.audit import AuditLog


@pytest.fixture()
def two_institutions(db):
    """Create two separate institutions, each with one super_admin and seed data."""
    institutions = {}
    for slug, name in [("inst-alpha", "Alpha College"), ("inst-beta", "Beta College")]:
        inst = db.query(Institution).filter(Institution.slug == slug).first()
        if not inst:
            inst = Institution(name=name, slug=slug, grouping_scheme="batch", is_active=True)
            db.add(inst)
            db.flush()
            sc = ScheduleConfig(
                institution_id=inst.id,
                working_days=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
                periods_per_day=6,
                period_times={str(i): f"{8+i:02d}:00-{9+i:02d}:00" for i in range(1, 7)},
            )
            db.add(sc)
        email = f"admin@{slug}.example.com"
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                institution_id=inst.id,
                username=f"admin-{slug}",
                email=email,
                hashed_password="firebase-managed",
                role="super_admin",
                is_active=True,
            )
            db.add(user)
        db.commit()

        # Seed some tenant-scoped data
        if not db.query(Faculty).filter(Faculty.institution_id == inst.id).first():
            fac = Faculty(
                institution_id=inst.id,
                name=f"Prof. {slug}",
                department="CS",
                email=f"fac@{slug}.example.com",
                max_periods_per_day=4,
            )
            db.add(fac)
            subj = Subject(
                institution_id=inst.id,
                name=f"{slug} Topic",
                code=f"{slug[:3].upper()}101",
                department="CS",
                credits=3,
                periods_per_week=3,
            )
            db.add(subj)
            room = Room(
                institution_id=inst.id,
                room_number=f"R-{slug}",
                capacity=40,
                type="classroom",
            )
            db.add(room)
            batch = Batch(
                institution_id=inst.id,
                name=f"{slug}-batch",
                department="CS",
                semester=3,
                student_count=40,
                year=2024,
            )
            db.add(batch)
            db.commit()

            assignment = Assignment(
                institution_id=inst.id,
                faculty_id=fac.id,
                subject_id=subj.id,
                batch_id=batch.id,
                semester=3,
            )
            db.add(assignment)
            db.commit()

        token = create_access_token(
            data={"sub": user.email, "role": user.role},
            expires_delta=timedelta(minutes=30),
        )
        institutions[slug] = {
            "institution": inst,
            "user": user,
            "headers": {"Authorization": f"Bearer {token}"},
        }
    return institutions


def test_list_endpoints_are_tenant_scoped(client, two_institutions):
    alpha = two_institutions["inst-alpha"]
    beta = two_institutions["inst-beta"]

    for path in ["/api/faculty", "/api/subjects", "/api/rooms", "/api/batches"]:
        alpha_items = client.get(path, headers=alpha["headers"]).json()
        beta_items = client.get(path, headers=beta["headers"]).json()
        assert isinstance(alpha_items, list), f"{path} should return list"
        assert isinstance(beta_items, list), f"{path} should return list"
        alpha_ids = {item["id"] for item in alpha_items}
        beta_ids = {item["id"] for item in beta_items}
        assert alpha_ids.isdisjoint(beta_ids), (
            f"{path} leaked data: alpha={alpha_ids} beta={beta_ids}"
        )


def test_cross_tenant_get_returns_404(client, db, two_institutions):
    alpha = two_institutions["inst-alpha"]
    beta = two_institutions["inst-beta"]

    # Fetch a beta-owned faculty id, then try to read it with alpha's token.
    beta_faculty = (
        db.query(Faculty)
        .filter(Faculty.institution_id == beta["institution"].id)
        .first()
    )
    assert beta_faculty is not None
    resp = client.get(f"/api/faculty/{beta_faculty.id}", headers=alpha["headers"])
    assert resp.status_code == 404, "Alpha should not read beta's faculty"

    beta_subject = (
        db.query(Subject)
        .filter(Subject.institution_id == beta["institution"].id)
        .first()
    )
    resp = client.get(f"/api/subjects/{beta_subject.id}", headers=alpha["headers"])
    assert resp.status_code == 404

    beta_room = (
        db.query(Room)
        .filter(Room.institution_id == beta["institution"].id)
        .first()
    )
    resp = client.get(f"/api/rooms/{beta_room.id}", headers=alpha["headers"])
    assert resp.status_code == 404

    beta_batch = (
        db.query(Batch)
        .filter(Batch.institution_id == beta["institution"].id)
        .first()
    )
    resp = client.get(f"/api/batches/{beta_batch.id}", headers=alpha["headers"])
    assert resp.status_code == 404


def test_cross_tenant_update_returns_404(client, db, two_institutions):
    alpha = two_institutions["inst-alpha"]
    beta = two_institutions["inst-beta"]
    beta_faculty = (
        db.query(Faculty)
        .filter(Faculty.institution_id == beta["institution"].id)
        .first()
    )
    resp = client.put(
        f"/api/faculty/{beta_faculty.id}",
        json={"max_periods_per_day": 99},
        headers=alpha["headers"],
    )
    assert resp.status_code == 404
    # Confirm data is unchanged
    db.refresh(beta_faculty)
    assert beta_faculty.max_periods_per_day != 99


def test_cross_tenant_delete_returns_404(client, db, two_institutions):
    alpha = two_institutions["inst-alpha"]
    beta = two_institutions["inst-beta"]
    beta_room = (
        db.query(Room)
        .filter(Room.institution_id == beta["institution"].id)
        .first()
    )
    resp = client.delete(f"/api/rooms/{beta_room.id}", headers=alpha["headers"])
    assert resp.status_code == 404
    # Confirm it still exists
    assert db.query(Room).filter(Room.id == beta_room.id).first() is not None


def test_institution_export_is_scoped(client, db, two_institutions):
    alpha = two_institutions["inst-alpha"]
    resp = client.get("/api/institution/export", headers=alpha["headers"])
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/zip")
    # ZIP must contain only alpha's institution slug in the filename.
    disp = resp.headers.get("content-disposition", "")
    assert "inst-alpha" in disp
    assert "inst-beta" not in disp


def test_audit_log_isolation(client, db, two_institutions):
    alpha = two_institutions["inst-alpha"]
    beta = two_institutions["inst-beta"]
    
    # Create audit logs for each
    db.add(AuditLog(institution_id=alpha["institution"].id, action="alpha-action", user_id=alpha["user"].id))
    db.add(AuditLog(institution_id=beta["institution"].id, action="beta-action", user_id=beta["user"].id))
    db.commit()
    
    # Alpha sees only alpha
    alpha_resp = client.get("/api/audit", headers=alpha["headers"]).json()
    actions = [item["action"] for item in alpha_resp["items"]]
    assert "alpha-action" in actions
    assert "beta-action" not in actions
        
    # Beta sees only beta
    beta_resp = client.get("/api/audit", headers=beta["headers"]).json()
    actions = [item["action"] for item in beta_resp["items"]]
    assert "beta-action" in actions
    assert "alpha-action" not in actions
