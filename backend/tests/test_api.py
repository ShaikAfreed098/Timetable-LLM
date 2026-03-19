"""
API endpoint integration tests.
"""
import pytest


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_register_and_login(client):
    # Register
    resp = client.post(
        "/api/auth/register",
        json={
            "username": "apiuser",
            "email": "apiuser@example.com",
            "password": "secret123",
            "role": "department_admin",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "apiuser"

    # Login
    resp = client.post(
        "/api/auth/token",
        data={"username": "apiuser", "password": "secret123"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_register_duplicate_username(client, auth_headers):
    client.post(
        "/api/auth/register",
        json={
            "username": "dup_user",
            "email": "dup1@example.com",
            "password": "pw",
            "role": "faculty",
        },
    )
    resp = client.post(
        "/api/auth/register",
        json={
            "username": "dup_user",
            "email": "dup2@example.com",
            "password": "pw",
            "role": "faculty",
        },
    )
    assert resp.status_code == 400


# Faculty CRUD
def test_faculty_crud(client, auth_headers):
    # Create
    resp = client.post(
        "/api/faculty",
        json={
            "name": "Dr. Smith",
            "department": "CSE",
            "email": "smith@college.edu",
            "max_periods_per_day": 4,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    fid = resp.json()["id"]

    # Read
    resp = client.get(f"/api/faculty/{fid}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Dr. Smith"

    # Update
    resp = client.put(
        f"/api/faculty/{fid}",
        json={"max_periods_per_day": 5},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["max_periods_per_day"] == 5

    # Delete
    resp = client.delete(f"/api/faculty/{fid}", headers=auth_headers)
    assert resp.status_code == 204

    # Should be gone
    resp = client.get(f"/api/faculty/{fid}", headers=auth_headers)
    assert resp.status_code == 404


# Subject CRUD
def test_subject_crud(client, auth_headers):
    resp = client.post(
        "/api/subjects",
        json={
            "name": "Compiler Design",
            "code": "CS401",
            "department": "CSE",
            "credits": 4,
            "periods_per_week": 4,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    sid = resp.json()["id"]

    resp = client.get(f"/api/subjects/{sid}", headers=auth_headers)
    assert resp.status_code == 200

    resp = client.delete(f"/api/subjects/{sid}", headers=auth_headers)
    assert resp.status_code == 204


# Room CRUD
def test_room_crud(client, auth_headers):
    resp = client.post(
        "/api/rooms",
        json={"room_number": "301", "capacity": 80, "type": "classroom"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    rid = resp.json()["id"]

    resp = client.get(f"/api/rooms/{rid}", headers=auth_headers)
    assert resp.status_code == 200

    resp = client.delete(f"/api/rooms/{rid}", headers=auth_headers)
    assert resp.status_code == 204


# Batch CRUD
def test_batch_crud(client, auth_headers):
    resp = client.post(
        "/api/batches",
        json={
            "name": "ECE-A",
            "department": "ECE",
            "semester": 2,
            "student_count": 55,
            "year": 2024,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    bid = resp.json()["id"]

    resp = client.get(f"/api/batches/{bid}", headers=auth_headers)
    assert resp.status_code == 200

    resp = client.delete(f"/api/batches/{bid}", headers=auth_headers)
    assert resp.status_code == 204


def test_unauthorized_access(client):
    resp = client.get("/api/faculty")
    assert resp.status_code == 401


def test_generate_timetable_no_data(client, auth_headers):
    """Generate with no data should return error details."""
    resp = client.post(
        "/api/timetable/generate?semester=99&department=UNKNOWN",
        headers=auth_headers,
    )
    assert resp.status_code == 422
