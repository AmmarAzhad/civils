
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.redis_session import setup_redis_pool, close_redis_pool
from app.db.session import init_db, close_db
from app.routes import workflows
from app.routes import tasks 

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("--- Starting up ---")
    setup_redis_pool()
    await init_db()
    yield
    print("--- Shutting down ---")
    await close_redis_pool()
    await close_db()

app = FastAPI(lifespan=lifespan)

app.include_router(workflows.router, prefix="/workflows", tags=["Workflows"])
app.include_router(tasks.router_tasks, prefix="/tasks", tags=["Tasks"])

@app.get("/")
def read_root():
    return {"Status": "API is up and running!!!"}