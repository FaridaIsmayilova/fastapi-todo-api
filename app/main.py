from fastapi import FastAPI
from contextlib import asynccontextmanager

from .database import Base, engine
from . import models
from .routes import tasks

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-create tables for all models imported above
    Base.metadata.create_all(bind=engine)
    yield
    # No teardonown actions needed

app = FastAPI(title="Project ToDo API", lifespan=lifespan)

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(tasks.router)


