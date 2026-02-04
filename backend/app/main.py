from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .database import engine, Base, get_db
from .services.scheduler import scheduler_service
from .models import ReportTask
from .routers import auth, gitea, notify, tasks, logs, ai
import logging

from fastapi.staticfiles import StaticFiles
import os

# Initialize DB
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Gitea Daily Reporter API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup
@app.on_event("startup")
async def startup_event():
    scheduler_service.start()
    # Reload active tasks into scheduler
    db = next(get_db())
    active_tasks = db.query(ReportTask).filter(ReportTask.is_active == True).all()
    for task in active_tasks:
        try:
            scheduler_service.add_or_update_task(task.id, task.cron_expression)
        except Exception as e:
            print(f"Failed to load task {task.id}: {e}")
    db.close()

@app.on_event("shutdown")
def shutdown_event():
    scheduler_service.stop()

# Routers
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(gitea.router, prefix="/api/gitea", tags=["Gitea"])
app.include_router(notify.router, prefix="/api/notify", tags=["Notify"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["Tasks"])
app.include_router(logs.router, prefix="/api/logs", tags=["Logs"])

# Serve Static Files (Frontend)
if os.path.exists("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")

@app.get("/api/health")
def health_check():
    return {"status": "ok"}
