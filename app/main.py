from fastapi import FastAPI
from contextlib import asynccontextmanager

from .database import Base, engine
from . import models  # ensure models are imported before create_all
from .routes.auth import router as auth_router
from .routes.tasks import router as tasks_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-create tables for all imported models
    Base.metadata.create_all(bind=engine)
    yield  # no teardown needed

app = FastAPI(title="fastapi-todo-api", lifespan=lifespan)

@app.get("/health")
def health():
    return {"status": "ok"}

# Routers
app.include_router(auth_router)     # /auth/*
app.include_router(tasks_router)    # /tasks/*



