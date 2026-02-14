from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, DateTime, Float, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum
from .database import Base


# --- ENUMS ---

class UserRole(str, enum.Enum):
    """User role enumeration"""
    ADMIN = "admin"
    RECRUITER = "recruiter"
    CANDIDATE = "candidate"


class JobStatus(str, enum.Enum):
    """Job posting status"""
    OPEN = "open"
    CLOSED = "closed"
    DRAFT = "draft"
    ARCHIVED = "archived"


class ApplicationStatus(str, enum.Enum):
    """Application status"""
    SUBMITTED = "submitted"
    REVIEWING = "reviewing"
    SHORTLISTED = "shortlisted"
    REJECTED = "rejected"
    HIRED = "hired"


# --- MODELS ---

class User(Base):
    """
    User model representing job portal users
    
    Attributes:
        id: Unique identifier
        email: User email (unique)
        hashed_password: Bcrypt hashed password
        is_active: Account status
        role: User role (admin, recruiter, candidate)
        first_name: User's first name
        last_name: User's last name
        phone: Contact phone number
        profile_image_url: Profile picture URL
        bio: User biography/description
        created_at: Account creation timestamp
        updated_at: Last update timestamp
        last_login: Last login timestamp
        
    Relationships:
        jobs: Jobs posted by this user (if recruiter)
        applications: Job applications submitted (if candidate)
    """
    __tablename__ = "users"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Authentication
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # Profile Info
    first_name = Column(String(100))
    last_name = Column(String(100))
    phone = Column(String(20))
    profile_image_url = Column(String(500))
    bio = Column(Text)
    
    # Account Status
    is_active = Column(Boolean, default=True, index=True)
    role = Column(SQLEnum(UserRole), default=UserRole.CANDIDATE, index=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login = Column(DateTime)
    
    # Relationships
    jobs = relationship("Job", back_populates="owner", cascade="all, delete-orphan")
    applications = relationship("JobApplication", back_populates="applicant", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
    
    def is_admin(self) -> bool:
        """Check if user is admin"""
        return self.role == UserRole.ADMIN
    
    def is_recruiter(self) -> bool:
        """Check if user is recruiter"""
        return self.role == UserRole.RECRUITER
    
    def is_candidate(self) -> bool:
        """Check if user is candidate"""
        return self.role == UserRole.CANDIDATE


class Job(Base):
    """
    Job posting model
    
    Attributes:
        id: Unique identifier
        title: Job title
        company: Company name
        description: Full job description
        salary_min: Minimum salary (optional)
        salary_max: Maximum salary (optional)
        salary_currency: Currency code (USD, EUR, etc)
        location: Job location
        job_type: Full-time, Part-time, Contract, Remote
        experience_level: Entry-level, Mid-level, Senior, Executive
        status: Job posting status (open, closed, draft, archived)
        is_open: Deprecated (use status instead)
        owner_id: ID of recruiter who posted the job
        created_at: When job was posted
        updated_at: Last update timestamp
        published_at: When job was published
        expires_at: Job posting expiration date
        view_count: Number of views
        application_count: Number of applications
        
    Relationships:
        owner: Recruiter who posted this job
        applications: Job applications received
    """
    __tablename__ = "jobs"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Job Details
    title = Column(String(255), index=True, nullable=False)
    company = Column(String(255), index=True, nullable=False)
    description = Column(Text, nullable=False)
    
    # Location & Type
    location = Column(String(255))
    job_type = Column(String(50))  # Full-time, Part-time, Contract, Remote
    experience_level = Column(String(100))  # Entry-level, Mid-level, Senior, Executive
    
    # Salary Information
    salary_min = Column(Float)
    salary_max = Column(Float)
    salary_currency = Column(String(3), default="USD")  # ISO 4217 currency code
    
    # Status & Visibility
    status = Column(SQLEnum(JobStatus), default=JobStatus.DRAFT, index=True)
    is_open = Column(Boolean, default=True, index=True)  # Legacy field
    
    # Foreign Key
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    published_at = Column(DateTime)
    expires_at = Column(DateTime)
    
    # Metrics
    view_count = Column(Integer, default=0)
    application_count = Column(Integer, default=0)
    
    # Relationships
    owner = relationship("User", back_populates="jobs")
    applications = relationship("JobApplication", back_populates="job", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Job(id={self.id}, title={self.title}, company={self.company}, status={self.status})>"
    
    def is_active(self) -> bool:
        """Check if job posting is currently active"""
        return self.status == JobStatus.OPEN and self.is_open
    
    def is_expired(self) -> bool:
        """Check if job posting has expired"""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False
    
    def salary_range(self) -> str:
        """Get formatted salary range"""
        if self.salary_min and self.salary_max:
            return f"{self.salary_currency} {self.salary_min:,.0f} - {self.salary_max:,.0f}"
        elif self.salary_min:
            return f"{self.salary_currency} {self.salary_min:,.0f}+"
        elif self.salary_max:
            return f"Up to {self.salary_currency} {self.salary_max:,.0f}"
        return "Not specified"


class JobApplication(Base):
    """
    Job application model - tracks candidate applications to jobs
    
    Attributes:
        id: Unique identifier
        job_id: ID of the job applied for
        applicant_id: ID of the candidate
        status: Application status (submitted, reviewing, shortlisted, rejected, hired)
        cover_letter: Candidate's cover letter
        resume_text: Candidate's resume (text format)
        ai_match_score: AI-generated match score (0-100)
        ai_analysis: AI analysis of the application
        rating: Recruiter's rating (1-5 stars)
        notes: Recruiter's notes
        created_at: When application was submitted
        updated_at: Last status update
        reviewed_at: When application was reviewed
        
    Relationships:
        job: The job applied for
        applicant: The candidate who applied
    """
    __tablename__ = "job_applications"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    applicant_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Application Content
    cover_letter = Column(Text)
    resume_text = Column(Text, nullable=False)
    
    # Status
    status = Column(SQLEnum(ApplicationStatus), default=ApplicationStatus.SUBMITTED, index=True)
    
    # AI Analysis
    ai_match_score = Column(Float)  # 0-100
    ai_analysis = Column(Text)  # JSON string with detailed analysis
    
    # Recruiter Review
    rating = Column(Integer)  # 1-5 stars
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    reviewed_at = Column(DateTime)
    
    # Relationships
    job = relationship("Job", back_populates="applications")
    applicant = relationship("User", back_populates="applications")
    
    def __repr__(self):
        return f"<JobApplication(id={self.id}, job_id={self.job_id}, applicant_id={self.applicant_id}, status={self.status})>"
    
    def is_active(self) -> bool:
        """Check if application is still being reviewed"""
        return self.status in [ApplicationStatus.SUBMITTED, ApplicationStatus.REVIEWING]
    
    def is_resolved(self) -> bool:
        """Check if application has been resolved"""
        return self.status in [ApplicationStatus.REJECTED, ApplicationStatus.HIRED]


class AuditLog(Base):
    """
    Audit log for tracking important actions (security and compliance)
    
    Attributes:
        id: Unique identifier
        user_id: ID of user who performed the action (nullable for system actions)
        action: Type of action (LOGIN, CREATE_JOB, DELETE_JOB, etc)
        resource_type: Type of resource affected (User, Job, Application, etc)
        resource_id: ID of the resource
        old_values: Previous values (JSON string)
        new_values: New values (JSON string)
        ip_address: IP address of the request
        user_agent: User agent string
        created_at: When the action occurred
    """
    __tablename__ = "audit_logs"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # User & Action
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(50), index=True, nullable=False)  # LOGIN, CREATE_JOB, DELETE_JOB, etc
    
    # Resource Information
    resource_type = Column(String(50), index=True)  # User, Job, Application, etc
    resource_id = Column(Integer, index=True)
    
    # Change Details
    old_values = Column(Text)  # JSON
    new_values = Column(Text)  # JSON
    
    # Request Details
    ip_address = Column(String(45))  # IPv6 compatible
    user_agent = Column(String(500))
    
    # Timestamp
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action}, resource_type={self.resource_type})>"


# --- DATABASE INITIALIZATION ---

def create_indexes():
    """Create additional composite indexes for performance"""
    # These would typically be created via Alembic migrations
    # Examples:
    # - (job_id, applicant_id) on job_applications for unique constraint
    # - (status, created_at) on job_applications for filtering
    # - (user_id, action, created_at) on audit_logs for audit trail
    pass