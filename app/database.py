# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import settings

# Replace with your actual PostgreSQL connection string
# Format: "postgresql://USER:PASSWORD@HOST:PORT/DATABASE_NAME"
# It's best to load this from environment variables
DATABASE_URL = settings.database_url

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set in the configuration")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# In modern SQLAlchemy, this comes from sqlalchemy.orm
Base = declarative_base()

# Dependency to get DB session in routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()