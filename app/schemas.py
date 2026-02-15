from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# USER SCHEMAS
class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    role: str
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

# JOB SCHEMAS
class JobBase(BaseModel):
    title: str
    company: str
    description: str
    salary: int

class JobCreate(JobBase):
    pass

class JobResponse(JobBase):
    id: int
    owner_id: int
    class Config:
        from_attributes = True

# --- DAY 10: APPLICATION SCHEMAS ---
class ApplicationOut(BaseModel):
    id: int
    job_id: int
    candidate_id: int
    ai_analysis: str
    status: str
    applied_at: datetime
    class Config:
        from_attributes = True