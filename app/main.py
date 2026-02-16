from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List

# Internal Module Imports
try:
    from . import models, schemas, database, auth_utils, ai_service
except ImportError:
    import models, schemas, database, auth_utils, ai_service

# Initialize Database Tables
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(
    title="Job Portal Pro: AI & RBAC Edition 🚀",
    description="Advanced backend system with Automated Admin Seeding and AI Integration",
    version="1.1.0"
)

# --- AUTOMATED ADMIN SEEDER ---

@app.on_event("startup")
def create_default_admin():
    """
    Startup event to ensure at least one Admin exists in the system.
    Default Credentials:
    - Email: admin@jobportal.com
    - Password: adminpassword123
    """
    db = database.SessionLocal()
    try:
        admin_email = "admin@jobportal.com"
        # Check if the admin already exists
        admin = db.query(models.User).filter(models.User.email == admin_email).first()
        
        if not admin:
            print("LOG: No admin detected. Seeding default admin user...")
            new_admin = models.User(
                email=admin_email,
                hashed_password=auth_utils.hash_password("adminpassword123"),
                role="admin" # Explicitly setting role as admin
            )
            db.add(new_admin)
            db.commit()
            print("LOG: Default admin created successfully! ✅")
        else:
            print("LOG: Admin user already exists. Skipping seed.")
    except Exception as e:
        print(f"LOG ERROR: Failed to seed admin: {e}")
    finally:
        db.close()

# --- AUTHENTICATION ENDPOINTS ---

@app.post("/register", response_model=schemas.UserOut)
def register(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    """Registers a new user as a 'candidate' by default."""
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email is already registered!")
    
    new_user = models.User(
        email=user.email, 
        hashed_password=auth_utils.hash_password(user.password),
        role="candidate" # Default role for new sign-ups
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    """Authenticates user and returns a JWT token."""
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not auth_utils.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=403, detail="Invalid credentials!")
    
    access_token = auth_utils.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

# --- ADMIN CONTROL PANEL ---

@app.put("/admin/applications/{app_id}/status")
def update_application_status(
    app_id: int, 
    new_status: str, 
    db: Session = Depends(database.get_db), 
    current_admin: models.User = Depends(auth_utils.admin_required)
):
    """
    Day 11 Mastery Test: Update application status.
    Strictly restricted to Admin users only.
    """
    # 1. Fetch the application
    application = db.query(models.Application).filter(models.Application.id == app_id).first()
    
    if not application:
        raise HTTPException(status_code=404, detail="Application record not found.")

    # 2. Update status logic
    application.status = new_status
    db.commit()
    db.refresh(application)

    return {
        "message": f"Application status successfully updated to: {new_status}",
        "application_id": app_id,
        "updated_by": current_admin.email
    }

@app.get("/admin/users", response_model=List[schemas.UserOut])
def list_users(db: Session = Depends(database.get_db), current_admin: models.User = Depends(auth_utils.admin_required)):
    """Fetch all registered users. Admin only."""
    return db.query(models.User).all()

# --- JOB & AI SERVICES ---

@app.post("/jobs/", response_model=schemas.JobResponse)
def create_job(job: schemas.JobCreate, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth_utils.get_current_user)):
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

@app.get("/")
def api_root():
    """Server status check."""
    return {
        "status": "Online",
        "milestone": "Day 11: Mid-way Audit Complete",
        "admin_seeder": "Active"
    }