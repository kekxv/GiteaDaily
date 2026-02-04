from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import GiteaConfig, User
from ..schemas import GiteaConfigCreate, GiteaConfigResponse
from ..services.gitea import GiteaService
from .auth import get_current_user

router = APIRouter()

@router.post("/", response_model=GiteaConfigResponse)
def create_gitea_config(config: GiteaConfigCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    new_cfg = GiteaConfig(**config.dict(), user_id=current_user.id)
    db.add(new_cfg)
    db.commit()
    db.refresh(new_cfg)
    return new_cfg

@router.get("/", response_model=List[GiteaConfigResponse])
def get_gitea_configs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(GiteaConfig).filter(GiteaConfig.user_id == current_user.id).all()

@router.post("/{config_id}/test")
async def test_gitea_connection(config_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    cfg = db.query(GiteaConfig).filter(GiteaConfig.id == config_id, GiteaConfig.user_id == current_user.id).first()
    if not cfg:
        raise HTTPException(status_code=404, detail="Config not found")
    service = GiteaService(cfg.base_url, cfg.token)
    success = await service.test_connection()
    return {"success": success}

@router.delete("/{config_id}")
def delete_gitea_config(config_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    cfg = db.query(GiteaConfig).filter(GiteaConfig.id == config_id, GiteaConfig.user_id == current_user.id).first()
    if not cfg:
        raise HTTPException(status_code=404, detail="Config not found")
    db.delete(cfg)
    db.commit()
    return {"message": "Config deleted"}
