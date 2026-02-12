from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
import models, schemas, database, auth_utils

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Job Portal Pro: RBAC Edition 👑")

@app.post("/register", response_model=schemas.UserOut)
def register(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="ईमेल आधीच आहे!")
    new_user = models.User(email=user.email, hashed_password=auth_utils.hash_password(user.password))
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not auth_utils.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=403, detail="चुकीचा पासवर्ड!")
    access_token = auth_utils.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

# --- Admin Only: सर्व युजर्सची लिस्ट पाहणे ---
@app.get("/admin/users", response_model=List[schemas.UserOut])
def get_all_users(db: Session = Depends(database.get_db), current_admin: models.User = Depends(auth_utils.admin_required)):
    return db.query(models.User).all()

# --- Admin Only: कोणाचाही जॉब डिलीट करणे ---
@app.delete("/admin/jobs/{job_id}")
def admin_delete_job(job_id: int, db: Session = Depends(database.get_db), current_admin: models.User = Depends(auth_utils.admin_required)):
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job: raise HTTPException(status_code=404, detail="जॉब नाही")
    db.delete(job)
    db.commit()
    return {"message": "एडमिनने जॉब डिलीट केला! ✅"}

# --- Regular Endpoints ---
@app.post("/jobs/", response_model=schemas.JobResponse)
def create_job(job: schemas.JobCreate, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth_utils.get_current_user)):
    new_job = models.Job(**job.dict(), owner_id=current_user.id)
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    return new_job

@app.get("/jobs/", response_model=List[schemas.JobResponse])
def get_jobs(db: Session = Depends(database.get_db)):
    return db.query(models.Job).all()