from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base, get_db, init_db
from .services.scheduler import scheduler_service
from .models import ReportTask
from .routers import auth, gitea, notify, tasks, logs, ai

import os

# Initialize DB with migrations
init_db()

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
    active_tasks = db.query(ReportTask).filter(ReportTask.is_active).all()
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

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

# Serve Static Files (Frontend)
# This MUST be defined last to avoid intercepting /api routes
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str = ""):
    # If the path starts with api/, let FastAPI handle it as a 404 if not found
    if full_path.startswith("api/"):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not Found")
    
    # In some environments, the root path might be passed as an empty string
    if not full_path or full_path == "/":
        full_path = "index.html"

    # Check if the file exists in static (e.g., favicon.ico, assets/..., etc.)
    # We prioritize actual files if they exist
    if os.path.exists("static"):
        file_path = os.path.join("static", full_path)
        if os.path.isfile(file_path):
            from fastapi.responses import FileResponse
            return FileResponse(file_path)
            
        # Otherwise serve index.html for React Router (SPA fallback)
        index_path = os.path.join("static", "index.html")
        if os.path.exists(index_path):
            from fastapi.responses import FileResponse
            return FileResponse(index_path)
    
    # If not even index.html exists, or static dir doesn't exist
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Not Found")

