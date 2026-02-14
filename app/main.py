from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List

# Relative Imports
try:
    from . import models, schemas, database, auth_utils, ai_service
except ImportError:
    import models, schemas, database, auth_utils, ai_service

# Initialize Database Tables
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(
    title="Job Portal Pro: Day 9 AI & RBAC Edition 🚀",
    description="Advanced job portal with AI-powered resume matching",
    version="1.0.0"
)

# --- AUTHENTICATION ENDPOINTS ---

@app.post("/register", response_model=schemas.UserOut)
def register(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    """Register a new user"""
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email is already registered!")
    new_user = models.User(
        email=user.email, 
        hashed_password=auth_utils.hash_password(user.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    """Login and get access token"""
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not auth_utils.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=403, detail="Incorrect email or password!")
    access_token = auth_utils.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

# --- AI ENDPOINTS ---

@app.post("/ai/match-resume")
async def match_resume(
    job_description: str, 
    resume_text: str, 
    current_user: models.User = Depends(auth_utils.get_current_user)
):
    """
    Day 9 Feature: Analyzes compatibility between a Job Description and a Resume.
    
    - Requires authentication
    - Returns match score and AI analysis
    - Uses Gemini 2.5 Flash AI
    
    Parameters:
    - job_description: Full job description text
    - resume_text: Candidate's resume text
    """
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
    """
    Day 8 Feature: Generate professional job descriptions using AI.
    
    - Requires authentication
    - Uses Gemini AI to generate descriptions
    
    Parameters:
    - job_title: Title of the job position
    """
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

# --- ADMIN ONLY ROUTES ---

@app.get("/admin/users", response_model=List[schemas.UserOut])
def get_all_users(
    db: Session = Depends(database.get_db), 
    current_admin: models.User = Depends(auth_utils.admin_required)
):
    """Get all registered users (Admin only)"""
    return db.query(models.User).all()

@app.delete("/admin/jobs/{job_id}")
def admin_delete_job(
    job_id: int, 
    db: Session = Depends(database.get_db), 
    current_admin: models.User = Depends(auth_utils.admin_required)
):
    """Delete a job posting (Admin only)"""
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found!")
    db.delete(job)
    db.commit()
    return {"message": "Admin deleted the job successfully."}

# --- REGULAR JOB ROUTES ---

@app.post("/jobs/", response_model=schemas.JobResponse)
def create_job(
    job: schemas.JobCreate, 
    db: Session = Depends(database.get_db), 
    current_user: models.User = Depends(auth_utils.get_current_user)
):
    """Create a new job posting"""
    new_job = models.Job(**job.dict(), owner_id=current_user.id)
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    return new_job

@app.get("/jobs/", response_model=List[schemas.JobResponse])
def get_jobs(db: Session = Depends(database.get_db)):
    """Get all job postings"""
    return db.query(models.Job).all()

@app.get("/")
def home():
    """Health check endpoint"""
    return {
        "status": "online",
        "message": "Job Portal is Live! AI Resume Matcher is ready.",
        "version": "1.0.0"
    }