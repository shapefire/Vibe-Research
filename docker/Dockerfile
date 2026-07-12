# syntax=docker/dockerfile:1

# 国内默认；海外构建可在 compose 中覆盖
ARG NODE_IMAGE=docker.m.daocloud.io/node:20-alpine
ARG PYTHON_IMAGE=docker.m.daocloud.io/python:3.11-slim-bookworm
ARG NPM_REGISTRY=https://registry.npmmirror.com
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn

# Stage 1: 构建前端
FROM ${NODE_IMAGE} AS frontend-build
ARG NPM_REGISTRY
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm config set registry "${NPM_REGISTRY}" && \
    npm ci --prefer-offline
COPY frontend/ ./
RUN npm run build

# Stage 2: 运行后端 + 静态资源
FROM ${PYTHON_IMAGE}
ARG PIP_INDEX_URL
ARG PIP_TRUSTED_HOST
WORKDIR /app
COPY backend/requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir \
      -i "${PIP_INDEX_URL}" \
      --trusted-host "${PIP_TRUSTED_HOST}" \
      -r requirements.txt
COPY backend/ ./backend/
COPY --from=frontend-build /app/frontend/dist ./frontend/dist
COPY a-stock-data/ ./a-stock-data/
COPY global-stock-data/ ./global-stock-data/

ENV VR_DATA_DIR=/data
VOLUME /data
WORKDIR /app/backend
EXPOSE 8900

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8900"]
