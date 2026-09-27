from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..helpers import candidate_data, record_activity, save_candidate_data
from ..models import Candidate, Resume, User
from ..schemas import CandidateUpdate
from ..security import require_roles

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.get("")
def list_candidates(search: str = "", skill: str = "", education: str = "", experience: str = "",
                    db: Session = Depends(get_db), user: User = Depends(require_roles("recruiter", "admin"))):
    query = db.query(Candidate).join(Resume, Candidate.resume_id == Resume.id)
    if search.strip():
        term = f"%{search.strip()}%"
        query = query.filter((Candidate.full_name.ilike(term)) | (Candidate.email.ilike(term)) | (Resume.filename.ilike(term)))
    candidates = query.order_by(Resume.uploaded_at.desc()).all()
    results = [candidate_data(db, item) for item in candidates]
    if skill.strip():
        results = [item for item in results if any(skill.strip().lower() in name.lower() for name in item["skills"])]
    if education.strip():
        term = education.strip().lower()
        results = [item for item in results if any(
            term in " ".join(record.get(key, "") for key in ("institution", "degree", "field")).lower()
            for record in item["education"]
        )]
    if experience.strip():
        term = experience.strip().lower()
        results = [item for item in results if any(
            term in " ".join(record.get(key, "") for key in ("company", "position", "description")).lower()
            for record in item["experience"]
        )]
    return results


@router.get("/{candidate_id}")
def get_candidate(candidate_id: int, db: Session = Depends(get_db), _user: User = Depends(require_roles("recruiter", "admin"))):
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    return candidate_data(db, candidate)


@router.put("/{candidate_id}")
def update_candidate(candidate_id: int, payload: CandidateUpdate, db: Session = Depends(get_db), user: User = Depends(require_roles("recruiter", "admin"))):
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    save_candidate_data(db, candidate, payload)
    resume = db.get(Resume, candidate.resume_id)
    record_activity(db, user.id, "Edited candidate details", resume.filename if resume else str(candidate_id))
    db.commit()
    return candidate_data(db, candidate)


@router.delete("/{candidate_id}")
def delete_candidate(candidate_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles("recruiter", "admin"))):
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    resume = db.get(Resume, candidate.resume_id)
    stored_path = resume.stored_path if resume else ""
    record_activity(db, user.id, "Deleted candidate", candidate.full_name or str(candidate_id))
    if resume:
        db.delete(resume)
    else:
        db.delete(candidate)
    db.commit()
    if stored_path:
        from pathlib import Path
        Path(stored_path).unlink(missing_ok=True)
    return {"message": "Candidate deleted."}
