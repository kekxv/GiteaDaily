from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import AIConfig, User
from ..schemas import AIConfigCreate, AIConfigResponse
from .auth import get_current_user

router = APIRouter()

@router.post("/", response_model=AIConfigResponse)
def create_ai_config(config: AIConfigCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    new_cfg = AIConfig(**config.dict(), user_id=current_user.id)
    db.add(new_cfg)
    db.commit()
    db.refresh(new_cfg)
    return new_cfg

@router.get("/", response_model=List[AIConfigResponse])
def get_ai_configs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(AIConfig).filter(AIConfig.user_id == current_user.id).all()

@router.post("/{config_id}/test")
async def test_ai_connection(config_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    cfg = db.query(AIConfig).filter(AIConfig.id == config_id, AIConfig.user_id == current_user.id).first()
    if not cfg:
        raise HTTPException(status_code=404, detail="Config not found")
    
    from ..services.ai import AIService
    result = await AIService.summarize_report(
        api_base=cfg.api_base,
        api_key=cfg.api_key,
        model=cfg.model,
        content="Hello, this is a test connection request. Please reply with 'Connection Successful'.",
        system_prompt="You are a connection tester."
    )
    
    if "失败" in result or "出错" in result:
        return {"success": False, "error": result}
    return {"success": True, "response": result}

@router.delete("/{config_id}")
def delete_ai_config(config_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    cfg = db.query(AIConfig).filter(AIConfig.id == config_id, AIConfig.user_id == current_user.id).first()
    if not cfg:
        raise HTTPException(status_code=404, detail="Config not found")
    db.delete(cfg)
    db.commit()
    return {"message": "Config deleted"}
