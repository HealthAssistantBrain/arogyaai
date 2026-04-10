import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Default to internal docker-compose postgres url if not set
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://user:password@postgres:5432/arogyaai")

engine_kwargs = {"pool_pre_ping": True}
if DATABASE_URL.startswith("postgresql"):
    engine_kwargs["connect_args"] = {
        "connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT_SECONDS", "3"))
    }

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency for FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
