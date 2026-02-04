from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import TaskLog, ReportTask, User
from ..schemas import TaskLogResponse
from .auth import get_current_user

router = APIRouter()

@router.get("/", response_model=List[TaskLogResponse])
def get_logs(
    task_id: int = Query(None),
    start_date: str = Query(None),
    end_date: str = Query(None),
    limit: int = Query(50),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(TaskLog).join(ReportTask).filter(ReportTask.user_id == current_user.id)
    if task_id:
        query = query.filter(TaskLog.task_id == task_id)
    
    if start_date:
        from datetime import datetime
        query = query.filter(TaskLog.created_at >= datetime.fromisoformat(start_date))
    if end_date:
        from datetime import datetime
        query = query.filter(TaskLog.created_at <= datetime.fromisoformat(end_date))
    
    return query.order_by(TaskLog.created_at.desc()).offset(offset).limit(limit).all()
