"""
MedBuddy MVP-1
================

This single file contains two sections (backend and a simple prototype mobile/desktop client).

Sections:
  - ### Backend: FastAPI app (file: backend/app.py)
  - ### Mobile: Kivy prototype (file: mobile/main.py)

How to use (quickstart):
1. Backend (development, local):
   - Create and activate a Python venv: `python -m venv venv && source venv/bin/activate` (Linux/macOS) or `venv\Scripts\activate` (Windows)
   - Install deps: `pip install fastapi uvicorn sqlmodel passlib[bcrypt] python-jose[cryptography]`
   - Save the backend section below into `backend/app.py` and run: `python backend/app.py` or `uvicorn backend.app:app --reload`
   - Backend runs on http://127.0.0.1:8000 by default.

2. Mobile prototype (desktop test or Android packaging later):
   - Install deps for prototype: `pip install kivy requests plyer`
   - Save the mobile section below into `mobile/main.py` and run: `python mobile/main.py`
   - The prototype logs in (or registers) using the email/password you enter and polls `/reminders` every 60s, showing local notifications when reminders are returned.

Notes / MVP decisions for this phase:
  - Authentication: simple JWT; token expiry configurable. Passwords hashed with bcrypt.
  - Scheduling: Server returns reminders for the current day within a configurable window (default 15 minutes before, 5 after). No push-notifications yet; the app polls `/reminders`.
  - Storage: SQLite for MVP. Later switch to PostgreSQL when scaling.
  - Notification delivery: local notifications via plyer (when running on device). Later we will add FCM/APNs push notifications.

---

### backend/app.py

"""
# backend/app.py
from typing import Optional, List
from sqlmodel import SQLModel, Field, create_engine, Session, select
from datetime import date, time, datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import JWTError, jwt
import uvicorn
from fastapi import Query
from zoneinfo import ZoneInfo
from sqlalchemy import text, select, func
# --- CONFIG ---
#DATABASE_URL = "sqlite:///./meds.db"
import os

# get path to repo root (parent of backend/) for render
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # backend/
# DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'meds.db')}"

# for using postgresql in onrender
import os
from sqlmodel import create_engine
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

# Only pass SQLite-specific args if SQLite is used
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SECRET_KEY = "change-me-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7

engine = create_engine(DATABASE_URL, echo=False)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- MODELS ---

from datetime import datetime, date, time
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship


# ----------------------------
# USER
# ----------------------------
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, nullable=False, unique=True)
    hashed_password: str
    timezone: str = Field(default="Asia/Kolkata")  # ✅ NEW FIELD

    medications: List["Medication"] = Relationship(back_populates="user")

# ----------------------------
# MEDICATION
# ----------------------------
class Medication(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    name: str
    dose: Optional[str] = None
    start_date: date = Field(default_factory=date.today)
    end_date: Optional[date] = None
    quantity: Optional[int] = None

    # Relationships
    user: Optional[User] = Relationship(back_populates="medications")
    times: List["MedicationTime"] = Relationship(back_populates="medication", sa_relationship_kwargs={"cascade": "all, delete"})
    taken_records: List["Taken"] = Relationship(back_populates="medication", sa_relationship_kwargs={"cascade": "all, delete"})


# ----------------------------
# MEDICATION TIME (Fixed times per day, e.g. 08:00, 20:00)
# ----------------------------
class MedicationTime(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    medication_id: int = Field(foreign_key="medication.id")
    time: time  # not string!

    medication: Optional[Medication] = Relationship(back_populates="times")


# ----------------------------
# TAKEN (Each actual intake)
# ----------------------------
class Taken(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    medication_id: int = Field(foreign_key="medication.id")
    scheduled_for: datetime  # e.g. 2025-10-12T08:00:00
    taken_at: Optional[datetime] = None

    medication: Optional[Medication] = Relationship(back_populates="taken_records")

# Vitals model
class Vitals(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    bp: Optional[str] = None
    hr: Optional[str] = None
    temp: Optional[str] = None
    record_time: datetime = Field(default_factory=datetime.now)

# --- Pydantic schemas ---
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    timezone: Optional[str] = "Asia/Kolkata"

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email: str


class MedCreate(BaseModel):
    name: str
    dose: Optional[str] = None
    times: List[str]  # ["08:00", "20:00"]
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    quantity: Optional[int] = None

# Vitals schemas
class VitalsCreate(BaseModel):
    bp: Optional[str] = None
    hr: Optional[str] = None
    temp: Optional[str] = None
    record_time: Optional[datetime] = None

class VitalsRead(BaseModel):
    id: int
    bp: Optional[str] = None
    hr: Optional[str] = None
    temp: Optional[str] = None
    record_time: datetime

# --- Utilities ---
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_password_hash(password: str) -> str:
    # Ensure password is a string and not bytes
    if not isinstance(password, str):
        password = str(password)
    print("Password for hashing:", password, type(password))  # Debug line
    return pwd_context.hash(password[:72])

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- FastAPI app ---

app = FastAPI()


# Vitals endpoints (must be after get_user_from_token and get_session)

# Dependency
def get_session():
    with Session(engine) as session:
        yield session

# Auth helpers
def authenticate_user(session: Session, email: str, password: str):
    user = session.exec(select(User).where(User.email == email)).first()
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

from sqlmodel import SQLModel

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)

@app.get("/debug/db")
def debug_db():
    from backend.app import engine
    with Session(engine) as session:
        result = session.exec(text("SELECT version();")).first()
        return {"database_version": result}

from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@app.post("/register", response_model=Token)
def register(user_in: UserCreate, session: Session = Depends(get_session)):
    existing = session.exec(select(User).where(User.email == user_in.email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")
    user = User(email=user_in.email, hashed_password=get_password_hash(user_in.password),timezone = user_in.timezone or "Asia/Kolkata")
    session.add(user)
    session.commit()
    session.refresh(user)
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer", "email": user.email}

@app.post("/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    user = authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer", "email": user.email}

def get_user_from_token(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)):
    credentials_exception = HTTPException(status_code=401, detail="Could not validate credentials")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = session.get(User, int(user_id))
    if user is None:
        raise credentials_exception
    return user

# Vitals endpoints
@app.post("/vitals", response_model=VitalsRead)
def add_vitals(vital: VitalsCreate, user: User = Depends(get_user_from_token), session: Session = Depends(get_session)):
    v = Vitals(
        user_id=user.id,
        bp=vital.bp,
        hr=vital.hr,
        temp=vital.temp,
        record_time=vital.record_time or datetime.now()
    )
    session.add(v)
    session.commit()
    session.refresh(v)
    return VitalsRead(id=v.id, bp=v.bp, hr=v.hr, temp=v.temp, record_time=v.record_time)

@app.get("/vitals", response_model=List[VitalsRead])
def list_vitals(user: User = Depends(get_user_from_token), session: Session = Depends(get_session)):
    vitals = session.exec(select(Vitals).where(Vitals.user_id == user.id)).all()
    return [VitalsRead(id=v.id, bp=v.bp, hr=v.hr, temp=v.temp, record_time=v.record_time) for v in vitals]
    credentials_exception = HTTPException(status_code=401, detail="Could not validate credentials")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = session.get(User, int(user_id))
    if user is None:
        raise credentials_exception
    return user


@app.post("/meds")
def create_med(med: MedCreate, user: User = Depends(get_user_from_token), session: Session = Depends(get_session)):
    times_joined = ",".join(med.times)
    start = med.start_date if med.start_date else date.today()
    # Convert list of time strings (e.g. ["08:00", "20:00"]) to MedicationTime objects
    med_time_objects = [MedicationTime(time=datetime.strptime(t, "%H:%M").time()) for t in med.times]
    dose = int(med.dose) if isinstance(med.dose, str) else med.dose
    new = Medication(user_id=user.id, name=med.name, dose=med.dose, times=med_time_objects, start_date=start, end_date=med.end_date, quantity=med.quantity)
    session.add(new)
    session.commit()
    session.refresh(new)
    return {"id": new.id, "name": new.name}

@app.get("/meds")
def list_meds(user: User = Depends(get_user_from_token), session: Session = Depends(get_session)):
    meds = session.exec(select(Medication).where(Medication.user_id == user.id)).all()
    result = []
    for m in meds:
        # Count how many times this medication has been taken
        stmt = select(func.count()).where(Taken.medication_id == m.id)
        result = session.execute(stmt)
        taken_count = result.scalar()  # scalar() gives the integer
        # Convert MedicationTime objects to HH:MM strings
        times_str = [t.time.strftime("%H:%M") for t in m.times]
        result.append({
            "id": m.id,
            "name": m.name,
            "dose": m.dose,
            "times": times_str,
            "start_date": m.start_date,
            "end_date": m.end_date,
            "quantity": m.quantity,
            "quantity_left": (m.quantity - taken_count) if m.quantity is not None else None
        })
    return result

# ----------------------------
# GET REMINDERS
# ----------------------------
@app.get("/reminders")
def get_reminders(
    minutes_before: int = 15,
    minutes_after: int = 5,
    user: User = Depends(get_user_from_token),
    session: Session = Depends(get_session)
):
    user_tz = ZoneInfo(user.timezone or "Asia/Kolkata")
    now = datetime.now(user_tz)
    start_window = now - timedelta(minutes=minutes_before)
    end_window = now + timedelta(minutes=minutes_after)

    meds = session.exec(select(Medication).where(Medication.user_id == user.id)).all()
    reminders = []

    for m in meds:
        # Skip if medication is not active
        if m.start_date and date.today() < m.start_date:
            continue
        if m.end_date and date.today() > m.end_date:
            continue
        print("Processing medication:", m.name)  # Debug line
        print("before for loop")
        for t in m.times:
          #  scheduled_time = datetime.combine(date.today(), t.time)
            #Make scheduled_time timezone-aware
            scheduled_time = datetime.combine(now.date(), t.time).replace(tzinfo=user_tz)
            print("Scheduled time:", scheduled_time, type(scheduled_time))  # Debug line
            print(start_window, end_window)  # Debug line
            # Check if scheduled_time is within the reminder window
            if start_window <= scheduled_time <= end_window:
                # Check if already taken
                taken = session.exec(
                    select(Taken)
                    .where(Taken.medication_id == m.id, Taken.scheduled_for == scheduled_time)
                ).first()
                if not taken:
                    reminders.append({
                        "med_id": m.id,
                        "name": m.name,
                        "dose": m.dose,
                        "scheduled_for": scheduled_time.isoformat()
                    })

    return reminders

# @app.post("/meds/{med_id}/take")
# def mark_taken(med_id: int, scheduled_for: Optional[datetime] = None, user: User = Depends(get_user_from_token), session: Session = Depends(get_session)):
#     med = session.get(Medication, med_id)
#     if not med or med.user_id != user.id:
#         raise HTTPException(status_code=404, detail="Medication not found")
#     if scheduled_for is None:
#         scheduled_for = datetime.now()
#     taken = Taken(medication_id=med_id, scheduled_for=scheduled_for, taken_at=datetime.now())
#     session.add(taken)
#     session.commit()
#     session.refresh(taken)
#     return {"status": "ok", "taken_id": taken.id}

# Mark as taken
# --- Mark as taken ---
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select
from datetime import datetime
from typing import Optional

# ----------------------------
# Request Models
# ----------------------------
class TakeRequest(BaseModel):
    scheduled_for: Optional[datetime] = None


# ----------------------------
# Mark as Taken
# ----------------------------
@app.post("/meds/{med_id}/take")
def mark_taken(
    med_id: int,
    req: TakeRequest,
    user: User = Depends(get_user_from_token),
    session: Session = Depends(get_session)
):
    med = session.get(Medication, med_id)
    if not med or med.user_id != user.id:
        raise HTTPException(status_code=404, detail="Medication not found")

    # If scheduled_for is not provided, use current datetime
    scheduled_for = req.scheduled_for or datetime.now()

    # Round microseconds to avoid matching issues
    scheduled_for = scheduled_for.replace(microsecond=0)

    # Check if already marked
    existing = session.exec(
        select(Taken)
        .where(Taken.medication_id == med_id, Taken.scheduled_for == scheduled_for)
    ).first()

    if existing:
        return {"status": "already_marked", "taken_id": existing.id}

    taken = Taken(
        medication_id=med_id,
        scheduled_for=scheduled_for,
        taken_at=datetime.now()
    )
    session.add(taken)
    session.commit()
    session.refresh(taken)
    return {"status": "ok", "taken_id": taken.id}


# ----------------------------
# Unmark as Taken
# ----------------------------
@app.delete("/meds/{med_id}/take")
def unmark_taken(
    med_id: int,
  #  req: TakeRequest,
    scheduled_for: datetime = Query(...),  # <--- accept from query instead of body
    user: User = Depends(get_user_from_token),
    session: Session = Depends(get_session)
):
    med = session.get(Medication, med_id)
    if not med or med.user_id != user.id:
        raise HTTPException(status_code=404, detail="Medication not found")

    # if not req.scheduled_for:
    #     raise HTTPException(status_code=400, detail="scheduled_for is required")

    scheduled_for = scheduled_for.replace(microsecond=0)

    taken = session.exec(
        select(Taken)
        .where(Taken.medication_id == med_id, Taken.scheduled_for == scheduled_for)
    ).first()

    if not taken:
        raise HTTPException(status_code=404, detail="Taken record not found")

    session.delete(taken)
    session.commit()
    return {"status": "unmarked"}

@app.get("/taken")
def list_taken(date_str: Optional[str] = Query(None), user: User = Depends(get_user_from_token), session: Session = Depends(get_session)):
    q = select(Taken, Medication).where(Taken.medication_id == Medication.id, Medication.user_id == user.id)
    if date_str:
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid date format")
        start = datetime.combine(d, time.min)
        end = datetime.combine(d, time.max)
        q = q.where(Taken.scheduled_for >= start, Taken.scheduled_for <= end)
    results = session.exec(q).all()
    return [
        {
            "med_id": med.id,
            "scheduled_for": taken.scheduled_for.isoformat(),
            "taken_at": taken.taken_at.isoformat() if taken.taken_at else None
        }
        for taken, med in results
    ]

@app.get("/me")
def get_me(user: User = Depends(get_user_from_token)):
    return {"email": user.email}

@app.get("/debug_time")
def debug_time():
    return {
        "server_datetime": datetime.now(),  # local server time
        "utc_datetime": datetime.utcnow()   # UTC time
    }

# ----------------------------
# DELETE MEDICATION
# ----------------------------
@app.delete("/meds/{med_id}")
def delete_medication(
    med_id: int,
    user: User = Depends(get_user_from_token),
    session: Session = Depends(get_session)
):
    # Fetch the medication for this user
    med = session.get(Medication, med_id)
    if not med or med.user_id != user.id:
        raise HTTPException(status_code=404, detail="Medication not found")

    # Delete the medication (cascades will delete related times + taken records)
    session.delete(med)
    session.commit()

    return {"status": "deleted", "med_id": med_id}
