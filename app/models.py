from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
import database

class User(database.Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Day 7: नवीन कॉलम - 'admin' किंवा 'candidate'
    role = Column(String, default="candidate") 
    
    jobs = relationship("Job", back_populates="owner")

class Job(database.Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    company = Column(String, nullable=False)
    description = Column(Text)
    salary = Column(Integer)
    is_open = Column(Boolean, default=True)
    
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="jobs")