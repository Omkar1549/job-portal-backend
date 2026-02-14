from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

# --- USER SCHEMAS ---

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: str
    role: str
    
    class Config:
        from_attributes = True

# --- JOB SCHEMAS ---

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
    is_open: bool
    
    class Config:
        from_attributes = True

# --- TOKEN SCHEMA ---

class Token(BaseModel):
    access_token: str
    token_type: str