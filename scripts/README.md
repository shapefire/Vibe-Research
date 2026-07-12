# Scripts

本目录包含运维与开发辅助脚本。

| 脚本 | 说明 |
|------|------|
| [`deploy.sh`](deploy.sh) | Docker 一键部署：拉代码 → 构建镜像 → 重启服务 |
| [`check_compliance_docs.py`](check_compliance_docs.py) | 合规文档校验（CI 使用） |

---

## deploy.sh — Docker 一键部署

适用于在 **Linux 服务器** 上自托管 Vibe-Research（Docker Compose 方式）。

### 前置条件

- 已安装 **Git**、**Docker**、**Docker Compose v2**
- 已 clone 本仓库，且能 `git pull` 到远程（默认 `origin`）
- 服务器已开放 **8900** 端口（或自行修改 `docker/docker-compose.yml` 中的端口映射）
- 建议安装 `curl`（用于健康检查；未安装时构建仍可进行，但健康检查会失败）

首次在服务器 clone 后：

```bash
cd /path/to/Vibe-Research
chmod +x scripts/deploy.sh
```

### 基本用法

在仓库根目录执行（也可在任意目录通过绝对路径调用）：

```bash
./scripts/deploy.sh
```

脚本会自动完成：

1. 检查工作区是否干净（有未提交改动则中止）
2. `git fetch` + `git pull --ff-only` 拉取当前分支最新代码
3. 启用 BuildKit，按 `docker/docker-compose.yml` 构建镜像（含国内 npm/pip 镜像加速）
4. `docker compose up -d` 重启服务
5. 轮询 `http://127.0.0.1:8900/api/health`（最多约 60 秒）
6. 打印容器状态，并清理悬空 Docker 镜像

部署成功后访问：`http://<服务器IP>:8900`

### 命令行选项

```bash
./scripts/deploy.sh --help
```

| 选项 | 说明 |
|------|------|
| （无） | 拉取当前分支最新代码，构建并重启 |
| `--branch <name>` | 切换到指定分支并拉取（如 `--branch main`） |
| `--no-pull` | 跳过 `git pull`，仅重建镜像并重启（适合已在服务器手动更新代码） |
| `--no-prune` | 部署成功后不执行 `docker image prune` |
| `-h`, `--help` | 显示帮助 |

### 常用示例

```bash
# 日常更新：拉 main 分支并部署
./scripts/deploy.sh --branch main

# 代码已在服务器上 git pull 过，只重建镜像
./scripts/deploy.sh --no-pull

# 保留旧悬空镜像（排查问题时）
./scripts/deploy.sh --no-prune
```

### 环境变量（可选）

生产环境建议在 [`docker/.env`](../docker/.env) 中配置（Compose 会自动加载）。首次部署：

```bash
cp docker/.env.example docker/.env
# 编辑 docker/.env，至少设置 VR_API_KEY（公网）与 VR_ALLOW_ORIGINS
```

| 变量 | 说明 |
|------|------|
| `VR_API_KEY` | 公网部署时设置 API 鉴权；本地可留空 |
| `VR_ALLOW_ORIGINS` | CORS 白名单，默认 `*` |
| `VR_DATA_DIR` | 容器内数据目录，compose 默认 `/data`（volume 持久化） |

变量说明详见 [`backend/.env.example`](../backend/.env.example)。

### 手动运维命令

脚本失败或需单独排查时，可在仓库根目录使用：

```bash
# 查看日志
docker compose -f docker/docker-compose.yml logs -f

# 仅构建（不启动）
DOCKER_BUILDKIT=1 docker compose -f docker/docker-compose.yml build

# 停止服务
docker compose -f docker/docker-compose.yml down

# 查看容器状态
docker compose -f docker/docker-compose.yml ps
```

### 常见问题

**工作区有未提交改动**

```
错误: 工作区有未提交改动，请先 commit/stash 或使用 --no-pull
```

服务器上不要直接改代码；若仅为重建镜像，加 `--no-pull`。

**健康检查超时**

脚本会打印最近 80 行容器日志。常见原因：端口被占用、依赖安装失败、容器启动崩溃。可执行：

```bash
docker compose -f docker/docker-compose.yml logs --tail=200
```

**BuildKit / cache mount 报错**

确保启用 BuildKit（脚本已自动设置）。手动构建时：

```bash
DOCKER_BUILDKIT=1 docker compose -f docker/docker-compose.yml build
```

**国内服务器构建慢**

镜像源已在 [`docker/docker-compose.yml`](../docker/docker-compose.yml) 中配置（DaoCloud 基础镜像代理、npmmirror、清华 PyPI）。若某代理不可用，修改 compose 中 `build.args` 的 `NODE_IMAGE` / `PYTHON_IMAGE` 等即可。

### 数据持久化

Compose 默认挂载 Docker volume `vr-data` → 容器 `/data`。持仓等用户数据写入该 volume，**容器重建不会丢失**。卸载服务时若需保留数据，不要使用 `docker compose down -v`。
