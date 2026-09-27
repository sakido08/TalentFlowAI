from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Candidate, Job, Resume, User
from ..security import get_current_user
from .resumes import _resume_data

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role == "user":
        resumes = db.query(Resume).filter_by(user_id=user.id).order_by(Resume.uploaded_at.desc()).all()
        return {"role": "user", "my_resumes": len(resumes),
                "processed_resumes": sum(item.status == "completed" for item in resumes),
                "recent": [_resume_data(db, item) for item in resumes[:5]]}
    if user.role == "admin":
        return {"role": "admin", "total_users": db.query(User).count(),
                "total_recruiters": db.query(User).filter_by(role="recruiter").count(),
                "total_resumes": db.query(Resume).count(), "total_candidates": db.query(Candidate).count()}
    recent = db.query(Candidate).join(Resume, Candidate.resume_id == Resume.id).order_by(Resume.uploaded_at.desc()).limit(5).all()
    return {"role": "recruiter", "total_candidates": db.query(Candidate).count(),
            "total_resumes": db.query(Resume).count(), "total_jobs": db.query(Job).filter_by(recruiter_id=user.id).count(),
            "recent": [{"id": item.id, "full_name": item.full_name, "email": item.email} for item in recent]}


@router.get("/history")
def history(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = db.query(Resume).order_by(Resume.uploaded_at.desc())
    if user.role == "user":
        query = query.filter(Resume.user_id == user.id)
    return [{"id": item.id, "filename": item.filename, "status": item.status,
             "error_message": item.error_message,
             "uploaded_at": item.uploaded_at.isoformat() if item.uploaded_at else None,
             "processing_seconds": item.processing_seconds} for item in query.all()]
