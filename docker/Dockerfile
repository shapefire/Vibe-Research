# Stage 1: 构建前端
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: 运行后端 + 静态资源
FROM python:3.11-slim-bookworm
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY --from=frontend-build /app/frontend/dist ./frontend/dist
COPY a-stock-data/ ./a-stock-data/
COPY global-stock-data/ ./global-stock-data/

ENV VR_DATA_DIR=/data
VOLUME /data
WORKDIR /app/backend
EXPOSE 8900

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8900"]
