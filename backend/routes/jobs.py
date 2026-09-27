from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..helpers import record_activity
from ..models import Job, User
from ..schemas import JobInput
from ..security import require_roles

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _job_data(job: Job) -> dict:
    return {"id": job.id, "title": job.title, "description": job.description,
            "required_skills": job.required_skills, "created_at": job.created_at.isoformat() if job.created_at else None}


def _get_job(db: Session, job_id: int, user: User) -> Job:
    job = db.get(Job, job_id)
    if not job or (user.role != "admin" and job.recruiter_id != user.id):
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@router.get("")
def list_jobs(db: Session = Depends(get_db), user: User = Depends(require_roles("recruiter", "admin"))):
    query = db.query(Job)
    if user.role != "admin":
        query = query.filter(Job.recruiter_id == user.id)
    return [_job_data(job) for job in query.order_by(Job.created_at.desc()).all()]


@router.post("", status_code=201)
def create_job(payload: JobInput, db: Session = Depends(get_db), user: User = Depends(require_roles("recruiter", "admin"))):
    job = Job(recruiter_id=user.id, title=payload.title.strip(), description=payload.description.strip(), required_skills=payload.required_skills.strip())
    db.add(job)
    db.flush()
    record_activity(db, user.id, "Created job", job.title)
    db.commit()
    db.refresh(job)
    return _job_data(job)


@router.put("/{job_id}")
def update_job(job_id: int, payload: JobInput, db: Session = Depends(get_db), user: User = Depends(require_roles("recruiter", "admin"))):
    job = _get_job(db, job_id, user)
    job.title, job.description, job.required_skills = payload.title.strip(), payload.description.strip(), payload.required_skills.strip()
    record_activity(db, user.id, "Updated job", job.title)
    db.commit()
    return _job_data(job)


@router.delete("/{job_id}")
def delete_job(job_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles("recruiter", "admin"))):
    job = _get_job(db, job_id, user)
    record_activity(db, user.id, "Deleted job", job.title)
    db.delete(job)
    db.commit()
    return {"message": "Job deleted."}
