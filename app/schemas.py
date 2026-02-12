from pydantic import BaseModel, EmailStr
from typing import List, Optional

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