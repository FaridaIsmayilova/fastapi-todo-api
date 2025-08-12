from fastapi import FastAPI
from contextlib import asynccontextmanager

from .database import Base, engine
from . import models
from .routes import tasks
from .routes.auth import router as auth_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-create tables for all models imported above
    Base.metadata.create_all(bind=engine)
    yield
    # No teardonown actions needed

app = FastAPI(title="fastapi-todo-api", lifespan=lifespan)

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(auth_router)
app.include_router(tasks.router)


