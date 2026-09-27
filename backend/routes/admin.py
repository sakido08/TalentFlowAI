from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..helpers import record_activity
from ..models import Activity, Candidate, Job, Resume, User
from ..schemas import ActiveInput, RoleInput
from ..security import require_roles

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users")
def list_users(db: Session = Depends(get_db), _admin: User = Depends(require_roles("admin"))):
    return [{"id": user.id, "name": user.name, "email": user.email, "role": user.role,
             "is_active": user.is_active, "created_at": user.created_at.isoformat() if user.created_at else None}
            for user in db.query(User).order_by(User.created_at.desc()).all()]


@router.put("/users/{user_id}/role")
def change_role(user_id: int, payload: RoleInput, db: Session = Depends(get_db), admin: User = Depends(require_roles("admin"))):
    if payload.role not in {"user", "recruiter", "admin"}:
        raise HTTPException(status_code=400, detail="Role must be user, recruiter, or admin.")
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")
    target.role = payload.role
    record_activity(db, admin.id, "Changed user role", f"{target.email}: {payload.role}")
    db.commit()
    return {"id": target.id, "role": target.role}


@router.put("/users/{user_id}/active")
def set_active(user_id: int, payload: ActiveInput, db: Session = Depends(get_db), admin: User = Depends(require_roles("admin"))):
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")
    if target.id == admin.id and not payload.is_active:
        raise HTTPException(status_code=400, detail="You cannot disable your own account.")
    target.is_active = payload.is_active
    record_activity(db, admin.id, "Changed account access", f"{target.email}: {'enabled' if target.is_active else 'disabled'}")
    db.commit()
    return {"id": target.id, "is_active": target.is_active}


@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_roles("admin"))):
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")
    if target.id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account.")
    stored_paths = [path for (path,) in db.query(Resume.stored_path).filter(Resume.user_id == target.id).all() if path]
    record_activity(db, admin.id, "Deleted user", target.email)
    db.delete(target)
    db.commit()
    for path in stored_paths:
        Path(path).unlink(missing_ok=True)
    return {"message": "User deleted."}


@router.get("/activity")
def list_activity(db: Session = Depends(get_db), _admin: User = Depends(require_roles("admin"))):
    rows = db.query(Activity).order_by(Activity.created_at.desc()).limit(100).all()
    return [{"id": row.id, "user_id": row.user_id, "action": row.action, "detail": row.detail,
             "created_at": row.created_at.isoformat() if row.created_at else None} for row in rows]


@router.get("/overview")
def overview(db: Session = Depends(get_db), _admin: User = Depends(require_roles("admin"))):
    return {"users": db.query(User).count(), "recruiters": db.query(User).filter_by(role="recruiter").count(),
            "resumes": db.query(Resume).count(), "candidates": db.query(Candidate).count(), "jobs": db.query(Job).count()}
