# Role
你是一名资深的全栈开发工程师，擅长 Python (FastAPI) 后端开发、React 前端开发以及系统架构设计。

# Project Goal
请协助我开发一个名为 **"Gitea Daily Reporter"** 的 Web 系统。
该系统的核心功能是：允许用户配置 Gitea 仓库源和企业微信机器人，系统根据预设的定时计划（如每天早上9点），自动统计前一天的代码提交记录（Commit Log），汇总成 Markdown 格式日报，并通过 Webhook 推送给企业微信。

# Tech Stack Requirements
为了保证开发效率、现代化和可维护性，请使用以下技术栈：

1.  **Backend:** Python 3.10+
    *   **Framework:** FastAPI (高性能 API，自动生成 Swagger 文档)
    *   **Database:** SQLAlchemy (ORM) + SQLite (方便部署，也可切换 PostgreSQL)
    *   **Scheduling:** APScheduler (用于处理 Cron 定时任务的核心组件)
    *   **HTTP Client:** Httpx 或 Requests
    *   **Auth:** OAuth2 with Password Bearer + JWT

2.  **Frontend:**
    *   **Library:** React 18+ (Functional Components, Hooks)
    *   **Build Tool:** Vite
    *   **UI Framework:** Ant Design (antd) 5.x - *非常适合后台管理系统，提供高质量的 Table 和 Form 组件*
    *   **State Management:** Zustand 或 React Context
    *   **HTTP Client:** Axios
    *   **Router:** React Router v6

3.  **Deployment:**
    *   提供 `docker-compose.yml` 以便一键部署前后端。

# Functional Requirements (Detailed)

## 1. 用户认证模块 (User Auth)
*   **注册/登录**: 支持用户名密码注册和登录。
*   **鉴权**: 后端 API 使用 JWT 保护。前端需处理 Token 存储和路由守卫 (Protected Route)。
*   **隔离**: 每个用户只能管理自己的 Gitea 配置和任务。

## 2. 数据源配置 (Gitea Source)
*   用户可以添加多个 Gitea 源配置。
*   **字段**: `Name` (别名), `Base URL` (如 `https://git.company.com`), `Access Token`.
*   **Action**: 提供 "测试连接" 按钮，验证 Token 是否有效。

## 3. 通知渠道配置 (Notification)
*   目前仅需支持 **企业微信机器人 (WeCom Webhook)**。
*   **字段**: `Name` (别名), `Webhook URL`.
*   **Action**: 提供 "发送测试消息" 按钮。

## 4. 任务调度管理 (Task Management) - 核心功能
*   用户创建“日报任务”。
*   **字段**:
    *   `Task Name`: 任务名称
    *   `Cron Schedule`: 计划时间 (前端可用 TimePicker 或输入 Cron 表达式，如 `0 9 * * *`)
    *   `Gitea Source`: 下拉选择已配置的源。
    *   `Scope`:
        *   **Type A (All)**: 自动遍历该 Token 能访问的所有仓库。
        *   **Type B (Specific)**: 用户输入 `owner/repo` 列表 (可动态添加/删除行)。
    *   `Notification`: 下拉选择通知渠道。
    *   `Status`: 开/关。
*   **逻辑**: 保存时，后端需同步更新 APScheduler 的作业列表。

## 5. 执行记录 (Execution Logs)
*   记录每次任务执行的结果。
*   **字段**: `Task Name`, `Time`, `Status` (Success/Failed), `Commit Count`, `Log Details`.
*   前端展示一个 Table，支持分页查看历史记录。

# Database Schema Design Suggestion
请基于以下实体关系设计数据库模型 (SQLAlchemy Models):

1.  **User**: `id`, `username`, `password_hash`
2.  **GiteaConfig**: `id`, `user_id`, `name`, `base_url`, `token`
3.  **NotifyConfig**: `id`, `user_id`, `name`, `webhook_url`
4.  **ReportTask**: `id`, `user_id`, `gitea_config_id`, `notify_config_id`, `cron_expression`, `scope_type` (all/specific), `target_repos` (JSON), `is_active`
5.  **TaskLog**: `id`, `task_id`, `status`, `summary`, `created_at`

# Output Requirements
请分步骤输出代码和说明，避免单次回复过长被截断：

1.  **Step 1: 项目结构与数据库设计**
    *   展示推荐的文件目录结构 (Frontend/Backend 分离)。
    *   提供 `backend/models.py` 和 `backend/database.py`。
2.  **Step 2: 后端核心服务**
    *   提供 `backend/services/gitea.py`: 封装 Gitea API 调用、统计逻辑、Markdown 生成。
    *   提供 `backend/services/scheduler.py`: 封装 APScheduler 管理逻辑。
3.  **Step 3: 后端 API 接口**
    *   提供 FastAPI `main.py` 和主要路由 (`routers/tasks.py` 等) 的实现。
4.  **Step 4: 前端 React 实现 (关键部分)**
    *   简述 Vite + React + Ant Design 的初始化。
    *   提供核心组件代码：`TaskForm.jsx` (任务创建表单) 和 `TaskList.jsx` (任务列表)。
    *   展示如何封装 Axios 请求拦截器以处理 JWT。
5.  **Step 5: 部署**
    *   提供 `Dockerfile` (多阶段构建，包含前端 build 和后端运行) 和 `docker-compose.yml`。

请开始你的设计与编码。
