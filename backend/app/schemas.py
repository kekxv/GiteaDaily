from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# Auth
class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

# Gitea Config
class GiteaConfigBase(BaseModel):
    name: str
    base_url: str
    token: str

class GiteaConfigCreate(GiteaConfigBase):
    pass

class GiteaConfigResponse(GiteaConfigBase):
    id: int
    class Config:
        from_attributes = True

# Notify Config
class NotifyConfigBase(BaseModel):
    name: str
    webhook_url: str

class NotifyConfigCreate(NotifyConfigBase):
    pass

class NotifyConfigResponse(NotifyConfigBase):
    id: int
    class Config:
        from_attributes = True

# AI Config
class AIConfigBase(BaseModel):
    name: str
    api_base: str = "https://api.openai.com/v1"
    api_key: str
    model: str = "gpt-3.5-turbo"
    system_prompt: Optional[str] = None

class AIConfigCreate(AIConfigBase):
    pass

class AIConfigResponse(AIConfigBase):
    id: int
    class Config:
        from_attributes = True

# Report Task
class ReportTaskBase(BaseModel):
    name: str
    gitea_config_id: int
    notify_config_id: int
    ai_config_id: Optional[int] = None
    cron_expression: str
    scope_type: str
    target_repos: Optional[List[str]] = None
    report_days: int = 1
    is_ai_enabled: bool = False
    ai_system_prompt: Optional[str] = None
    is_active: bool = True

class ReportTaskCreate(ReportTaskBase):
    pass

class ReportTaskResponse(ReportTaskBase):
    id: int
    last_run_at: Optional[datetime] = None
    class Config:
        from_attributes = True

# Task Log
class TaskLogResponse(BaseModel):
    id: int
    task_id: int
    status: str
    commit_count: int
    summary: str
    log_details: Optional[str] = None
    raw_data: Optional[str] = None
    created_at: datetime
    class Config:
        from_attributes = True
