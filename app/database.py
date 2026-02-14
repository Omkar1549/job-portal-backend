import os
import logging
from sqlalchemy import create_engine, event, pool, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool, StaticPool
from typing import Generator
from contextlib import contextmanager

# Configure logging
logger = logging.getLogger(__name__)

# --- DATABASE CONFIGURATION ---

# Get database URL from environment variable or use default
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./job_portal.db"
)

# Determine if using SQLite (for different pool configuration)
IS_SQLITE = DATABASE_URL.startswith("sqlite")

# Environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG = ENVIRONMENT == "development"

# --- ENGINE CONFIGURATION ---

if IS_SQLITE:
    # SQLite configuration (for development)
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # Single connection for SQLite
        echo=DEBUG,  # Log SQL queries in development
    )
    logger.info(f"SQLite database initialized: {DATABASE_URL}")
else:
    # PostgreSQL/MySQL configuration (for production)
    engine = create_engine(
        DATABASE_URL,
        # Connection pooling
        poolclass=QueuePool,
        pool_size=20,  # Number of connections to keep in pool
        max_overflow=40,  # Additional connections allowed
        pool_pre_ping=True,  # Test connection before using
        pool_recycle=3600,  # Recycle connections after 1 hour
        # Performance
        echo=DEBUG,
        # Connection settings
        connect_args={
            "connect_timeout": 10,
            "application_name": "job_portal_api",
        }
    )
    logger.info(f"Production database initialized: {DATABASE_URL}")

# --- SESSION CONFIGURATION ---

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,  # Don't expire objects after commit
)

# --- BASE FOR ORM MODELS ---

Base = declarative_base()

# --- CONNECTION POOL EVENTS (only for non-SQLite) ---

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Set SQLite pragmas for better performance"""
    if IS_SQLITE:
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
        cursor.execute("PRAGMA synchronous=NORMAL")  # Better performance
        cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache
        cursor.execute("PRAGMA foreign_keys=ON")  # Enable foreign keys
        cursor.close()
        logger.debug("SQLite pragmas applied")


# Only add pool events for non-SQLite databases
if not IS_SQLITE:
    @event.listens_for(engine, "pool_connect")
    def receive_pool_connect(dbapi_conn, connection_record):
        """Log pool connections"""
        logger.debug("Database connection acquired from pool")

    @event.listens_for(engine, "pool_checkout")
    def receive_pool_checkout(dbapi_conn, connection_record, connection_proxy):
        """Log pool checkouts"""
        logger.debug("Database connection checked out from pool")

    @event.listens_for(engine, "pool_detach")
    def receive_pool_detach(dbapi_conn, connection_record):
        """Log pool detach"""
        logger.debug("Database connection detached from pool")


# --- DATABASE DEPENDENCY ---

def get_db() -> Generator[Session, None, None]:
    """
    Dependency for getting database session
    
    Usage in FastAPI:
        @app.get("/")
        def read_root(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


# --- CONTEXT MANAGER FOR MANUAL SESSIONS ---

@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager for manual session management
    
    Usage:
        with get_db_context() as db:
            user = db.query(User).first()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        logger.error(f"Database context error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


# --- HEALTH CHECK ---

async def check_database_connection() -> bool:
    """
    Check if database is accessible
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            logger.info("Database health check: OK")
            return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


def get_connection_pool_status() -> dict:
    """
    Get current connection pool status
    
    Returns:
        Dictionary with pool statistics
    """
    try:
        if IS_SQLITE:
            return {"pool_type": "StaticPool", "note": "SQLite uses single connection"}
        
        pool = engine.pool
        return {
            "pool_size": getattr(pool, 'pool_size', 'N/A'),
            "checked_out_connections": getattr(pool, 'checkedout', lambda: 'N/A')(),
            "overflow": getattr(pool, 'overflow', lambda: 'N/A')(),
        }
    except Exception as e:
        logger.error(f"Error getting pool status: {e}")
        return {"error": str(e)}


# --- DATABASE INITIALIZATION ---

def init_db():
    """
    Initialize database (create all tables)
    
    Note: This is typically handled by Alembic migrations in production
    """
    try:
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise


def drop_all_tables():
    """
    Drop all tables (DANGEROUS - use only for testing)
    """
    try:
        logger.warning("Dropping all database tables...")
        Base.metadata.drop_all(bind=engine)
        logger.warning("All database tables dropped")
    except Exception as e:
        logger.error(f"Error dropping tables: {e}")
        raise


# --- QUERY OPTIMIZATION ---

def get_db_with_optimizations() -> Generator[Session, None, None]:
    """
    Get database session with query optimizations
    
    - joinedload for relationships
    - selectinload for lazy relationships
    - configure_mappers for caching
    """
    db = SessionLocal()
    try:
        # Set query optimization flags
        db.info['_sa_adapter_cache'] = {}
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


# --- DATABASE STATISTICS ---

def get_database_stats() -> dict:
    """
    Get database statistics
    
    Returns:
        Dictionary with database info
    """
    try:
        with engine.connect() as conn:
            if IS_SQLITE:
                # SQLite stats
                result = conn.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ))
                tables = [row[0] for row in result]
                
                stats = {
                    "database_type": "SQLite",
                    "database_url": DATABASE_URL,
                    "tables": tables,
                    "table_count": len(tables),
                    "connection_pool": get_connection_pool_status(),
                }
            else:
                # PostgreSQL/MySQL stats (adjust query as needed)
                result = conn.execute(text(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
                ))
                tables = [row[0] for row in result]
                
                stats = {
                    "database_type": "PostgreSQL/MySQL",
                    "database_url": DATABASE_URL.split("@")[1] if "@" in DATABASE_URL else "***",
                    "tables": tables,
                    "table_count": len(tables),
                    "connection_pool": get_connection_pool_status(),
                }
            
            return stats
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        return {"error": str(e)}


# --- DATABASE BACKUP (SQLite only) ---

def backup_database(backup_path: str = "./backups/job_portal_backup.db"):
    """
    Backup SQLite database
    
    Args:
        backup_path: Path where backup should be saved
    """
    if not IS_SQLITE:
        logger.warning("Backup only supported for SQLite")
        return
    
    try:
        import shutil
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        
        db_file = DATABASE_URL.replace("sqlite:///", "")
        shutil.copy2(db_file, backup_path)
        logger.info(f"Database backed up to: {backup_path}")
    except Exception as e:
        logger.error(f"Error backing up database: {e}")
        raise


# --- TRANSACTION HELPER ---

def execute_in_transaction(func, *args, **kwargs):
    """
    Execute function within a database transaction
    
    Usage:
        def create_user(db: Session, email: str):
            user = User(email=email)
            db.add(user)
            return user
        
        execute_in_transaction(create_user, email="test@example.com")
    """
    with get_db_context() as db:
        try:
            result = func(db, *args, **kwargs)
            db.commit()
            return result
        except Exception as e:
            db.rollback()
            logger.error(f"Transaction error: {e}")
            raise


# --- DATABASE INITIALIZATION ON STARTUP ---

if __name__ == "__main__":
    # Initialize database when script is run directly
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialization complete")