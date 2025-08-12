from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import settings

cfg = settings()
DB_URL = (
    f"postgresql+psycopg2://{cfg.POSTGRES_USER}:{cfg.POSTGRES_PASSWORD}"
    f"@{cfg.POSTGRES_HOST}:{cfg.POSTGRES_PORT}/{cfg.POSTGRES_DB}"
)

engine = create_engine(DB_URL, pool_pre_ping = True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
