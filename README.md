💼 Job Portal Pro: AI & RBAC Edition 🚀

Job Portal Pro is a high-performance, production-ready backend system built with FastAPI. Developed as part of a 21-day intensive mastery challenge, this project demonstrates advanced backend engineering principles, including secure authentication, modular architecture, and cutting-edge AI integration.

🎯 Current Status: Day 9 of 21

The project has evolved from a simple CRUD application to an intelligent system capable of autonomous decision-making and role-based management.

🚀 Key Features

🤖 AI-Powered Intelligence (New)

Smart Resume Matcher (Day 9): Uses Gemini 2.5 Flash AI to analyze candidate resumes against job descriptions, providing a match percentage and gap analysis.

Automatic JD Generator (Day 8): Instantly generates professional job descriptions based on job titles using Generative AI.

🛡️ Advanced Security & Access Control

RBAC (Role-Based Access Control): Granular permissions for Admin and Candidate roles.

JWT Authentication: Stateless session management using JSON Web Tokens.

Password Hashing: Industry-standard security using Bcrypt to ensure no plain-text passwords are stored.

🏗️ Engineering Excellence

Modular Architecture: Separation of concerns across Models, Schemas, Routers, and Services.

ORM Integration: Persistent data storage using SQLAlchemy with SQLite.

Data Validation: Strict type checking and validation powered by Pydantic.

Performance: Optimized for asynchronous I/O to handle high concurrency.

🛠️ Tech Stack

Language: Python 3.10+

Framework: FastAPI

Database: SQLite (SQLAlchemy ORM)

AI Engine: Google Gemini 2.5 Flash

Security: Passlib (Bcrypt), Python-JOSE (JWT)

Testing: Swagger UI / Postman

📂 Project Structure

app/
├── main.py          # Entry point and API Routes
├── database.py      # Database connection and Session management
├── models.py        # SQLAlchemy models (Database Tables)
├── schemas.py       # Pydantic models (Data Validation)
├── auth_utils.py    # Security, JWT, and RBAC logic
├── ai_service.py    # Gemini AI Integration service
└── .gitignore       # Repository clean-up


⚙️ Installation & Setup

Clone the repository:

git clone [https://github.com/Omkar1549/job-portal-backend.git](https://github.com/Omkar1549/job-portal-backend.git)
cd job-portal-backend


Install dependencies:

pip install fastapi uvicorn sqlalchemy passlib[bcrypt] python-jose[cryptography] httpx


Run the application:

python -m uvicorn app.main:app --reload


Access Documentation:
Open http://127.0.0.1:8000/docs to explore the interactive API dashboard.

🎙️ About the Author

Omkar Kandekar is a Full Stack Developer focused on building scalable, performance-optimized systems. This project serves as a showcase of technical growth, consistency (documented via GitHub Green Dots), and the ability to integrate AI into real-world business solutions.

Built with passion, logic, and a lot of FastAPI! 🟢✨
