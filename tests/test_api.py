def register_and_login(client):
    response = client.post("/api/register", json={
        "name": "Morgan Lee", "email": "morgan@example.edu", "password": "StudentPass123!"
    })
    assert response.status_code == 201
    assert response.json()["role"] == "user"
    login = client.post("/api/login", json={"email": "morgan@example.edu", "password": "StudentPass123!"})
    assert login.status_code == 200
    return login.json()["access_token"]


def test_register_login_and_current_user(client):
    token = register_and_login(client)
    response = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "morgan@example.edu"


def test_invalid_password_is_rejected(client):
    register_and_login(client)
    response = client.post("/api/login", json={"email": "morgan@example.edu", "password": "wrong-pass"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


def test_registration_cannot_choose_admin_and_roles_are_enforced(client):
    token = register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    forbidden = client.get("/api/candidates", headers=headers)
    assert forbidden.status_code == 403
    # A role field is ignored because the registration schema has no role input.
    response = client.post("/api/register", json={
        "name": "Second Student", "email": "second@example.edu", "password": "StudentPass456!", "role": "admin"
    })
    assert response.status_code == 201
    assert response.json()["role"] == "user"


def test_upload_extracts_editable_profile_and_matches_job(client, tmp_path, monkeypatch):
    from io import BytesIO

    import pymupdf
    from backend.database import get_db
    from backend.main import app
    from backend.models import User
    from backend.routes import resumes as resume_routes

    token = register_and_login(client)
    # This test-only promotion stands in for an admin assigning recruiter access.
    db_generator = app.dependency_overrides[get_db]()
    test_db = next(db_generator)
    try:
        account = test_db.query(User).filter_by(email="morgan@example.edu").one()
        account.role = "recruiter"
        test_db.commit()
    finally:
        db_generator.close()
    monkeypatch.setattr(resume_routes, "UPLOAD_DIR", tmp_path)

    buffer = BytesIO()
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "Morgan Lee\nmorgan@example.edu\n+1 555 123 4567\nSUMMARY\nPython developer with SQL experience.\nSKILLS\nPython, SQL, Git\nEDUCATION\nBS Computer Science | Example University | 2022 - 2026")
    document.save(buffer)
    document.close()
    headers = {"Authorization": f"Bearer {token}"}
    uploaded = client.post("/api/resumes/upload", headers=headers,
                           files={"file": ("morgan.pdf", buffer.getvalue(), "application/pdf")})
    assert uploaded.status_code == 201
    result = uploaded.json()
    assert result["status"] == "completed"
    assert result["candidate"]["full_name"] == "Morgan Lee"
    assert result["candidate"]["email"] == "morgan@example.edu"
    assert "Python" in result["candidate"]["skills"]
    assert result["candidate"]["extracted_text"]
    assert result["candidate"]["education"][0]["institution"] == "Example University"

    update = client.put(f"/api/resumes/{result['id']}", headers=headers, json={
        "full_name": "Morgan Lee (reviewed)", "email": "morgan@example.edu", "phone": "555-123-4567",
        "address": "", "summary": "Reviewed by recruiter", "skills": ["Python", "SQL"],
        "education": [{"institution":"Example University","degree":"BS Computer Science","field":"CS","start_date":"2022","end_date":"2026"}],
        "experience": [], "certifications": [],
    })
    assert update.status_code == 200
    assert update.json()["candidate"]["full_name"] == "Morgan Lee (reviewed)"

    job = client.post("/api/jobs", headers=headers, json={
        "title": "Junior Python Developer", "description": "Build Python APIs with SQL.", "required_skills": "Python, SQL, React"
    })
    assert job.status_code == 201
    matched = client.post("/api/matching", headers=headers, json={
        "candidate_id": result["candidate"]["id"], "job_id": job.json()["id"]
    })
    assert matched.status_code == 200
    assert 0 <= matched.json()["tfidf_score"] <= 100
    assert 0 <= matched.json()["overall_score"] <= 100
    assert [item["weight"] for item in matched.json()["components"]] == [55, 30, 10, 5]
    assert matched.json()["matched_skills"] == ["Python", "SQL"]
    assert matched.json()["missing_skills"] == ["React"]


def test_rejects_unsupported_resume_file(client):
    token = register_and_login(client)
    response = client.post("/api/resumes/upload", headers={"Authorization": f"Bearer {token}"},
                           files={"file": ("notes.txt", b"not a resume", "text/plain")})
    assert response.status_code == 400
