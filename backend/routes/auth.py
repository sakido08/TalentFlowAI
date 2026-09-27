from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..helpers import record_activity
from ..models import User
from ..schemas import LoginInput, RegisterInput, UserOutput
from ..security import create_access_token, get_current_user, hash_password, verify_password

router = APIRouter(tags=["authentication"])


@router.post("/register", response_model=UserOutput, status_code=201)
def register(payload: RegisterInput, db: Session = Depends(get_db)):
    if db.query(User).filter_by(email=payload.email).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    # Public registration always creates a regular user; admins assign recruiter access later.
    user = User(name=payload.name.strip(), email=payload.email, password_hash=hash_password(payload.password), role="user")
    db.add(user)
    db.flush()
    record_activity(db, user.id, "Registered", "Created a user account")
    db.commit()
    db.refresh(user)
    return user


@router.post("/login")
def login(payload: LoginInput, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=payload.email.strip().lower()).first()
    if not user or not verify_password(payload.password, user.password_hash) or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    record_activity(db, user.id, "Logged in")
    db.commit()
    return {"access_token": create_access_token(user.id), "token_type": "bearer", "user": UserOutput.model_validate(user)}


@router.get("/me", response_model=UserOutput)
def me(user: User = Depends(get_current_user)):
    return user
