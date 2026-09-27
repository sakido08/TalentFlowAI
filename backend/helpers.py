"""Small shared helpers used by API route modules."""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .models import Activity, Candidate, Certification, Education, Experience, Resume, Skill, User


def record_activity(db: Session, user_id: int | None, action: str, detail: str = "") -> None:
    db.add(Activity(user_id=user_id, action=action, detail=detail[:300]))


def get_resume_for_user(db: Session, resume_id: int, user: User) -> Resume:
    resume = db.get(Resume, resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")
    if user.role == "user" and resume.user_id != user.id:
        raise HTTPException(status_code=404, detail="Resume not found.")
    return resume


def candidate_data(db: Session, candidate: Candidate) -> dict:
    resume = db.get(Resume, candidate.resume_id)
    return {
        "id": candidate.id,
        "resume_id": candidate.resume_id,
        "filename": resume.filename if resume else "",
        "status": resume.status if resume else "failed",
        "error_message": resume.error_message if resume else "",
        "uploaded_at": resume.uploaded_at.isoformat() if resume and resume.uploaded_at else None,
        "full_name": candidate.full_name,
        "email": candidate.email,
        "phone": candidate.phone,
        "address": candidate.address,
        "summary": candidate.summary,
        "extracted_text": resume.extracted_text if resume else "",
        "processed_text": resume.processed_text if resume else "",
        "processing_seconds": resume.processing_seconds if resume else None,
        "skills": [item.skill_name for item in db.query(Skill).filter_by(candidate_id=candidate.id).all()],
        "education": [
            {"id": item.id, "institution": item.institution, "degree": item.degree, "field": item.field,
             "start_date": item.start_date, "end_date": item.end_date}
            for item in db.query(Education).filter_by(candidate_id=candidate.id).all()
        ],
        "experience": [
            {"id": item.id, "company": item.company, "position": item.position, "description": item.description,
             "start_date": item.start_date, "end_date": item.end_date}
            for item in db.query(Experience).filter_by(candidate_id=candidate.id).all()
        ],
        "certifications": [item.name for item in db.query(Certification).filter_by(candidate_id=candidate.id).all()],
    }


def save_candidate_data(db: Session, candidate: Candidate, data) -> None:
    candidate.full_name = data.full_name.strip()
    candidate.email = data.email.strip()
    candidate.phone = data.phone.strip()
    candidate.address = data.address.strip()
    candidate.summary = data.summary.strip()

    # Replace the editable lists as a unit so deleted chips/items are removed too.
    db.query(Skill).filter_by(candidate_id=candidate.id).delete()
    db.query(Education).filter_by(candidate_id=candidate.id).delete()
    db.query(Experience).filter_by(candidate_id=candidate.id).delete()
    db.query(Certification).filter_by(candidate_id=candidate.id).delete()
    unique_skills = list(dict.fromkeys(skill.strip() for skill in data.skills if skill.strip()))
    db.add_all(Skill(candidate_id=candidate.id, skill_name=skill) for skill in unique_skills)
    db.add_all(Education(candidate_id=candidate.id, **item.model_dump()) for item in data.education)
    db.add_all(Experience(candidate_id=candidate.id, **item.model_dump()) for item in data.experience)
    unique_certs = list(dict.fromkeys(cert.strip() for cert in data.certifications if cert.strip()))
    db.add_all(Certification(candidate_id=candidate.id, name=cert) for cert in unique_certs)
