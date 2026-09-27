import os
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..database import get_db
from ..helpers import candidate_data, get_resume_for_user, record_activity, save_candidate_data
from ..models import Candidate, Resume, User
from ..schemas import CandidateUpdate
from ..security import get_current_user
from ..services.extraction import extract_information
from ..services.preprocessing import preprocess_text
from ..services.resume_parser import extract_text

router = APIRouter(prefix="/resumes", tags=["resumes"])
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
MAX_FILE_BYTES = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".docx"}


def _process(db: Session, resume: Resume, candidate: Candidate, file_bytes: bytes | None = None) -> None:
    """Extract text, preserve both versions, and update candidate fields."""
    started = time.perf_counter()
    resume.status = "processing"
    try:
        if file_bytes is None:
            file_bytes = Path(resume.stored_path).read_bytes()
        original = extract_text(file_bytes, resume.filename)
        if not original.strip():
            resume.error_message = "No selectable text was found. Scanned PDFs need OCR."
            raise ValueError(resume.error_message)
        processed = preprocess_text(original)
        fields = extract_information(processed)
    except Exception as error:
        # Store a readable failure status. Never return parser stack traces to the browser.
        resume.status = "failed"
        resume.extracted_text = resume.extracted_text or ""
        resume.processed_text = resume.processed_text or ""
        resume.error_message = resume.error_message or "Unable to extract text from this file. Check that the document is valid."
    else:
        from ..schemas import CandidateUpdate
        resume.extracted_text = original
        resume.processed_text = processed
        resume.status = "completed"
        resume.error_message = ""
        candidate.full_name = fields["full_name"]
        candidate.email = fields["email"]
        candidate.phone = fields["phone"]
        candidate.address = fields["address"]
        candidate.summary = fields["summary"]
        save_candidate_data(db, candidate, CandidateUpdate(**fields))
    finally:
        resume.processing_seconds = round(time.perf_counter() - started, 3)


def _resume_data(db: Session, resume: Resume) -> dict:
    candidate = db.query(Candidate).filter_by(resume_id=resume.id).first()
    return {
        "id": resume.id,
        "filename": resume.filename,
        "status": resume.status,
        "error_message": resume.error_message,
        "uploaded_at": resume.uploaded_at.isoformat() if resume.uploaded_at else None,
        "processing_seconds": resume.processing_seconds,
        "candidate": candidate_data(db, candidate) if candidate else None,
    }


@router.post("/upload", status_code=201)
async def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    extension = Path(file.filename or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Please upload a PDF or DOCX file.")
    content = await file.read(MAX_FILE_BYTES + 1)
    if not content:
        raise HTTPException(status_code=400, detail="The selected file is empty.")
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="The resume must be smaller than 10 MB.")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename).name[:200]
    stored_path = UPLOAD_DIR / f"{uuid.uuid4().hex}{extension}"
    stored_path.write_bytes(content)
    resume = Resume(user_id=user.id, filename=safe_name, stored_path=str(stored_path), status="processing")
    db.add(resume)
    db.flush()
    candidate = Candidate(resume_id=resume.id)
    db.add(candidate)
    db.flush()
    _process(db, resume, candidate, content)
    record_activity(db, user.id, "Uploaded resume", safe_name)
    db.commit()
    db.refresh(resume)
    return _resume_data(db, resume)


@router.get("")
def list_resumes(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = db.query(Resume).order_by(Resume.uploaded_at.desc())
    if user.role == "user":
        query = query.filter(Resume.user_id == user.id)
    return [_resume_data(db, resume) for resume in query.all()]


@router.get("/{resume_id}")
def get_resume(resume_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _resume_data(db, get_resume_for_user(db, resume_id, user))


@router.post("/{resume_id}/extract")
def reprocess_resume(resume_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    resume = get_resume_for_user(db, resume_id, user)
    candidate = db.query(Candidate).filter_by(resume_id=resume.id).first()
    if not candidate:
        candidate = Candidate(resume_id=resume.id)
        db.add(candidate)
        db.flush()
    _process(db, resume, candidate)
    record_activity(db, user.id, "Reprocessed resume", resume.filename)
    db.commit()
    db.refresh(resume)
    return _resume_data(db, resume)


@router.put("/{resume_id}")
def update_resume(resume_id: int, payload: CandidateUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    resume = get_resume_for_user(db, resume_id, user)
    candidate = db.query(Candidate).filter_by(resume_id=resume.id).first()
    if not candidate:
        candidate = Candidate(resume_id=resume.id)
        db.add(candidate)
        db.flush()
    save_candidate_data(db, candidate, payload)
    record_activity(db, user.id, "Edited candidate details", resume.filename)
    db.commit()
    return _resume_data(db, resume)


@router.delete("/{resume_id}")
def delete_resume(resume_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    resume = get_resume_for_user(db, resume_id, user)
    stored_path = resume.stored_path
    record_activity(db, user.id, "Deleted resume", resume.filename)
    db.delete(resume)
    db.commit()
    if stored_path:
        Path(stored_path).unlink(missing_ok=True)
    return {"message": "Resume deleted."}
