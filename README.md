# Gitea Daily Reporter (GDR) 🚀

Gitea Daily Reporter 是一款为团队和个人设计的自动化日报工具。它能够自动监控 Gitea 仓库活动，利用 AI 智能总结工作内容，并通过企业微信机器人准时推送精美的 Markdown 日报。

## 🌟 核心功能

- **多模式追踪**:
  - **所有仓库**: 监控 Token 可访问的所有活动。
  - **个人仓库**: 仅监控用户拥有的项目。
  - **个人活动记录**: 基于 Gitea Activity Feed 追踪特定用户的行为轨迹（提交、Issue、PR、评论）。
  - **指定仓库**: 灵活配置需要关注的具体项目。
- **AI 智能总结**: 兼容 OpenAI 格式接口（支持 DeepSeek, GPT 等），自动对原始提交信息进行语义化总结，生成专业的工作简报。
- **分片推送**: 自动处理企业微信 4096 字节长度限制，超长日报自动分片发送。
- **灵活调度**: 支持每天、工作日、每周特定天数或固定间隔时间的定时任务。
- **生命周期日志**: 记录每次任务的执行状态、发送详情、原始 JSON 数据以及可能的错误堆栈。
- **本地时间支持**: 完全适配服务器本地时区。

## 🛠️ 技术栈

- **后端**: Python 3.10+, FastAPI, SQLAlchemy, APScheduler, OpenAI SDK.
- **前端**: React 18, Vite, Ant Design 5.x, Zustand.
- **数据库**: SQLite (默认).
- **部署**: Docker, Docker Compose.

## 🚀 快速开始

### 方式一：使用 Docker (推荐)

1. 克隆仓库并进入目录。
2. 运行以下命令：
   ```bash
   docker-compose up --build -d
   ```
3. 访问 `http://localhost:8000` 即可使用。

### 方式二：本地开发运行

#### 后端
```bash
cd backend
uv venv
source .venv/bin/activate  # Windows 使用 .venv\Scripts\activate
uv pip install -r requirements.txt
uv run uvicorn app.main:app --reload
```

#### 前端
```bash
cd frontend
pnpm install
pnpm dev
```

## 📝 使用指南

1. **注册登录**: 首次启动后注册管理员账号。
2. **配置中心**:
   - 添加 **Gitea 源**: 输入 Base URL 和 Access Token。
   - 添加 **通知渠道**: 输入企业微信 Webhook URL。
   - 添加 **AI 配置**: 输入 OpenAI 兼容的 API 信息（可选）。
3. **任务管理**:
   - 创建新任务，选择范围类型（建议个人使用选“个人活动记录”）。
   - 开启 AI 总结以获得更高质量的日报。
   - 点击“测试发送”验证配置。
   - 保存后系统将按计划自动运行。

## 🤝 贡献与反馈

欢迎提交 Issue 或 Pull Request 来改进本项目！

## 📄 开源协议

本项目采用 [MIT License](LICENSE) 开源协议。
