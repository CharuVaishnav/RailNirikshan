from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Department, Location, User
from ..schemas import DepartmentOut, LocationOut, LoginIn, TokenOut, UserOut
from ..security import create_token, current_user, verify_password

router = APIRouter(tags=["auth & master data"])


@router.post("/auth/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == body.username))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Wrong username or password")
    return TokenOut(access_token=create_token(user), role=user.role, full_name=user.full_name)


@router.get("/auth/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


@router.get("/departments", response_model=list[DepartmentOut])
def departments(db: Session = Depends(get_db), _: User = Depends(current_user)):
    return db.scalars(select(Department).order_by(Department.name)).all()


@router.get("/locations", response_model=list[LocationOut])
def locations(db: Session = Depends(get_db), _: User = Depends(current_user)):
    return db.scalars(select(Location).order_by(Location.name)).all()
