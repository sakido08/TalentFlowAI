from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..helpers import record_activity
from ..models import Candidate, Education, Experience, Job, Match, Resume, Skill, User
from ..schemas import MatchInput
from ..security import require_roles
from ..services.similarity import calculate_match

router = APIRouter(prefix="/matching", tags=["matching"])


@router.post("")
def match_candidate(payload: MatchInput, db: Session = Depends(get_db), user: User = Depends(require_roles("recruiter", "admin"))):
    candidate = db.get(Candidate, payload.candidate_id)
    job = db.get(Job, payload.job_id)
    if not candidate or not job or (user.role != "admin" and job.recruiter_id != user.id):
        raise HTTPException(status_code=404, detail="Candidate or job not found.")
    resume = db.get(Resume, candidate.resume_id)
    if not resume or not resume.extracted_text:
        raise HTTPException(status_code=400, detail="This resume has no extracted text to compare.")
    job_text = f"{job.title}\n{job.description}\n{job.required_skills}"
    skills = [item.skill_name for item in db.query(Skill).filter_by(candidate_id=candidate.id).all()]
    experience = [
        {"start_date": item.start_date, "end_date": item.end_date, "description": item.description}
        for item in db.query(Experience).filter_by(candidate_id=candidate.id).all()
    ]
    education = [
        {"degree": item.degree, "institution": item.institution}
        for item in db.query(Education).filter_by(candidate_id=candidate.id).all()
    ]
    result = calculate_match(resume.extracted_text, job_text, skills, job.required_skills, experience, education)
    db.add(Match(
        candidate_id=candidate.id,
        job_id=job.id,
        tfidf_score=result["tfidf_score"] / 100,
        semantic_score=result["semantic_score"] / 100 if result["semantic_score"] is not None else None,
    ))
    record_activity(db, user.id, "Matched candidate", f"{candidate.full_name or candidate.id} → {job.title}")
    db.commit()
    return {
        "candidate_id": candidate.id,
        "job_id": job.id,
        "overall_score": result["overall_score"],
        "components": result["components"],
        "formula": result["formula"],
        "tfidf_score": result["tfidf_score"],
        "semantic_score": result["semantic_score"],
        "matched_skills": result["matched_skills"],
        "missing_skills": result["missing_skills"],
        "semantic_error": result["semantic_error"],
        "notice": "Similarity is an algorithmic indicator for review, not a probability or hiring decision.",
    }
