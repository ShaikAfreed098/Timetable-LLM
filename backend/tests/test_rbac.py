from fastapi.testclient import TestClient

def test_faculty_role_cannot_create(client: TestClient, db):
    # Register and login as faculty
    client.post(
        "/api/auth/register",
        json={
            "username": "faculty_user",
            "email": "faculty@example.com",
            "password": "pw",
            "role": "faculty",
            "institution_id": 1,
            "department": "CSE"
        },
        headers={"X-Bootstrap-Token": "test-token"}
    )
    resp = client.post("/api/auth/token", data={"username": "faculty_user", "password": "pw"})
    token = resp.json().get("access_token", "")
    headers = {"Authorization": f"Bearer {token}"}

    # Try to create a room
    resp = client.post("/api/rooms", json={"room_number": "101", "capacity": 50, "type": "class"}, headers=headers)
    assert resp.status_code == 403

def test_department_admin_cannot_mutate_another_dept(client: TestClient, db):
    # Register and login as department_admin for CSE
    client.post(
        "/api/auth/register",
        json={
            "username": "dept_admin_cse",
            "email": "cse@example.com",
            "password": "pw",
            "role": "department_admin",
            "institution_id": 1,
            "department": "CSE"
        },
        headers={"X-Bootstrap-Token": "test-token"}
    )
    resp = client.post("/api/auth/token", data={"username": "dept_admin_cse", "password": "pw"})
    token = resp.json().get("access_token", "")
    headers = {"Authorization": f"Bearer {token}"}

    # Try to create a faculty in ECE
    resp = client.post(
        "/api/faculty",
        json={
            "name": "Dr. ECE",
            "department": "ECE",
            "email": "ece@example.com",
            "max_periods_per_day": 4
        },
        headers=headers
    )
    assert resp.status_code == 403

    # Successfully create in CSE
    resp = client.post(
        "/api/faculty",
        json={
            "name": "Dr. CSE",
            "department": "CSE",
            "email": "cse2@example.com",
            "max_periods_per_day": 4
        },
        headers=headers
    )
    assert resp.status_code == 201

def test_super_admin_can_do_everything(client: TestClient, db):
    # Register and login as super_admin
    client.post(
        "/api/auth/register",
        json={
            "username": "super_user",
            "email": "super@example.com",
            "password": "pw",
            "role": "super_admin",
            "institution_id": 1,
            "department": None
        },
        headers={"X-Bootstrap-Token": "test-token"}
    )
    resp = client.post("/api/auth/token", data={"username": "super_user", "password": "pw"})
    token = resp.json().get("access_token", "")
    headers = {"Authorization": f"Bearer {token}"}

    # Create faculty in any department
    resp = client.post(
        "/api/faculty",
        json={
            "name": "Dr. Any",
            "department": "ANY",
            "email": "any@example.com",
            "max_periods_per_day": 4
        },
        headers=headers
    )
    assert resp.status_code == 201
