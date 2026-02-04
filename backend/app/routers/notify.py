from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import NotifyConfig, User
from ..schemas import NotifyConfigCreate, NotifyConfigResponse
from ..services.webhook import WebhookService
from .auth import get_current_user

router = APIRouter()

@router.post("/", response_model=NotifyConfigResponse)
def create_notify_config(config: NotifyConfigCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    new_cfg = NotifyConfig(**config.dict(), user_id=current_user.id)
    db.add(new_cfg)
    db.commit()
    db.refresh(new_cfg)
    return new_cfg

@router.get("/", response_model=List[NotifyConfigResponse])
def get_notify_configs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(NotifyConfig).filter(NotifyConfig.user_id == current_user.id).all()

@router.post("/{config_id}/test")
async def test_notify_connection(config_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    cfg = db.query(NotifyConfig).filter(NotifyConfig.id == config_id, NotifyConfig.user_id == current_user.id).first()
    if not cfg:
        raise HTTPException(status_code=404, detail="Config not found")
    success = await WebhookService.send_wecom_markdown(cfg.webhook_url, "这是一条来自 Gitea Daily Reporter 的测试消息。")
    return {"success": success}

@router.delete("/{config_id}")
def delete_notify_config(config_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    cfg = db.query(NotifyConfig).filter(NotifyConfig.id == config_id, NotifyConfig.user_id == current_user.id).first()
    if not cfg:
        raise HTTPException(status_code=404, detail="Config not found")
    db.delete(cfg)
    db.commit()
    return {"message": "Config deleted"}
