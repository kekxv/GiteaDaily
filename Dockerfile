# Stage 1: Build Frontend
FROM node:20-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN npm install -g pnpm && pnpm install
COPY frontend/ ./
RUN pnpm build

# Stage 2: Backend & Final Image
FROM python:3.11-slim
WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/app ./app

# Copy frontend build from stage 1
COPY --from=frontend-build /frontend/dist ./static

# Environment variables
ENV DATABASE_URL=sqlite:///./data/gitea_reporter.db
ENV SECRET_KEY=change-me-in-production

# Create data directory for SQLite
RUN mkdir ./data

# Expose port
EXPOSE 8000

# Run the application with multiple workers for concurrency
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
