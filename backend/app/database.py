from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./gitea_reporter.db")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def init_db():
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    # Simple migration: Add last_run_at to report_tasks if missing (SQLite specific)
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    columns = [c['name'] for c in inspector.get_columns('report_tasks')]
    if 'last_run_at' not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE report_tasks ADD COLUMN last_run_at DATETIME"))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
