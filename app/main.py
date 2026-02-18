from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
import os
import shutil

try:
    from . import models, schemas, database, auth_utils, ai_service
except ImportError:
    import models
    import schemas
    import database
    import auth_utils
    import ai_service

# Initialize database
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Job Portal Pro: Day 14 AI PDF Parser 🤖")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- AUTHENTICATION ENDPOINTS ---

@app.post("/register", response_model=schemas.UserOut)
def register(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    """Register a new user as a 'candidate' by default."""
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email is already registered!")
    
    new_user = models.User(
        email=user.email, 
        hashed_password=auth_utils.hash_password(user.password),
        role="candidate"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    """Authenticate user and return JWT token."""
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not auth_utils.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=403, detail="Invalid credentials!")
    
    access_token = auth_utils.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

# --- ADMIN CONTROL PANEL ---

@app.get("/admin/users", response_model=List[schemas.UserOut])
def list_users(
    db: Session = Depends(database.get_db), 
    current_admin: models.User = Depends(auth_utils.admin_required)
):
    """Fetch all registered users. Admin only."""
    return db.query(models.User).all()

# --- JOB ROUTES ---

@app.post("/jobs/", response_model=schemas.JobResponse)
def create_job(
    job: schemas.JobCreate, 
    db: Session = Depends(database.get_db), 
    current_user: models.User = Depends(auth_utils.get_current_user)
):
    """Create a new job posting."""
    new_job = models.Job(**job.dict(), owner_id=current_user.id)
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    return new_job

@app.get("/jobs/", response_model=List[schemas.JobResponse])
def get_jobs(db: Session = Depends(database.get_db)):
    """Public route to list all jobs."""
    return db.query(models.Job).all()

# --- AI ENDPOINTS ---

@app.post("/ai/match-resume")
async def match_resume(
    job_description: str, 
    resume_text: str, 
    current_user: models.User = Depends(auth_utils.get_current_user)
):
    """Day 9 Feature: Analyze resume vs job description"""
    try:
        if not job_description or not resume_text:
            raise HTTPException(
                status_code=400, 
                detail="Both Job Description and Resume Text are required."
            )
        
        analysis = await ai_service.match_resume_with_ai(job_description, resume_text)
        
        return {
            "candidate": current_user.email,
            "matching_analysis": analysis,
            "model": "Gemini 2.5 Flash AI"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ai/generate-description")
async def get_ai_description(
    job_title: str,
    current_user: models.User = Depends(auth_utils.get_current_user)
):
    """Day 8 Feature: Generate job descriptions using AI"""
    try:
        if not job_title:
            raise HTTPException(status_code=400, detail="Job title is required.")
        
        description = await ai_service.generate_job_description(job_title)
        
        return {
            "job_title": job_title,
            "ai_generated_description": description
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- HEALTH CHECK ---

@app.get("/")
def api_root():
    """Server status check."""
    return {
        "status": "Online",
        "version": "1.0.0",
        "features": ["Auth", "Jobs", "AI Resume Matcher", "AI Job Description"]
    }

# --- STARTUP EVENT ---

@app.on_event("startup")
def create_default_admin():
    """Create default admin on startup if not exists."""
    db = database.SessionLocal()
    try:
        admin_email = "admin@jobportal.com"
        admin = db.query(models.User).filter(models.User.email == admin_email).first()
        
        if not admin:
            print("Creating default admin user...")
            new_admin = models.User(
                email=admin_email,
                hashed_password=auth_utils.hash_password("adminpassword123"),
                role="admin"
            )
            db.add(new_admin)
            db.commit()
            print("✅ Default admin created!")
        else:
            print("✅ Admin already exists")
    except Exception as e:
        print(f"❌ Error creating admin: {e}")
    finally:
        db.close()