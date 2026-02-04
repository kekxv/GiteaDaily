from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, JSON, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)

    gitea_configs = relationship("GiteaConfig", back_populates="owner")
    notify_configs = relationship("NotifyConfig", back_populates="owner")
    ai_configs = relationship("AIConfig", back_populates="owner")
    tasks = relationship("ReportTask", back_populates="owner")

class GiteaConfig(Base):
    __tablename__ = "gitea_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String, nullable=False)
    base_url = Column(String, nullable=False)
    token = Column(String, nullable=False)

    owner = relationship("User", back_populates="gitea_configs")
    tasks = relationship("ReportTask", back_populates="gitea_config")

class NotifyConfig(Base):
    __tablename__ = "notify_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String, nullable=False)
    webhook_url = Column(String, nullable=False)

    owner = relationship("User", back_populates="notify_configs")
    tasks = relationship("ReportTask", back_populates="notify_config")

class AIConfig(Base):
    __tablename__ = "ai_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String, nullable=False)
    api_base = Column(String, default="https://api.openai.com/v1")
    api_key = Column(String, nullable=False)
    model = Column(String, default="gpt-3.5-turbo")
    system_prompt = Column(Text, nullable=True)

    owner = relationship("User", back_populates="ai_configs")
    tasks = relationship("ReportTask", back_populates="ai_config")

class ReportTask(Base):
    __tablename__ = "report_tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    gitea_config_id = Column(Integer, ForeignKey("gitea_configs.id"))
    notify_config_id = Column(Integer, ForeignKey("notify_configs.id"))
    ai_config_id = Column(Integer, ForeignKey("ai_configs.id"), nullable=True)
    name = Column(String, nullable=False)
    cron_expression = Column(String, nullable=False)
    scope_type = Column(String, nullable=False)  # "all" or "specific"
    target_repos = Column(JSON, nullable=True)  # List of "owner/repo"
    report_days = Column(Integer, default=1)  # Number of days to look back
    is_ai_enabled = Column(Boolean, default=False)
    ai_system_prompt = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)

    owner = relationship("User", back_populates="tasks")
    gitea_config = relationship("GiteaConfig", back_populates="tasks")
    notify_config = relationship("NotifyConfig", back_populates="tasks")
    ai_config = relationship("AIConfig", back_populates="tasks")
    logs = relationship("TaskLog", back_populates="task")

class TaskLog(Base):
    __tablename__ = "task_logs"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("report_tasks.id"))
    status = Column(String, nullable=False)  # "success" or "failed"
    commit_count = Column(Integer, default=0)
    summary = Column(Text, nullable=True)
    log_details = Column(Text, nullable=True)
    raw_data = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    task = relationship("ReportTask", back_populates="logs")
