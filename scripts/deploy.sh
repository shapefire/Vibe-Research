#!/usr/bin/env bash
# Vibe-Research Docker 一键部署：拉代码 → 构建镜像 → 重启服务 → 健康检查
#
# 用法（在仓库根目录或任意目录执行均可）：
#   ./scripts/deploy.sh
#   ./scripts/deploy.sh --branch main
#   ./scripts/deploy.sh --no-pull          # 跳过 git pull（仅重建并重启）
#   ./scripts/deploy.sh --no-prune         # 跳过清理悬空镜像
#
# 可选：在 docker/.env 中设置 VR_API_KEY、VR_ALLOW_ORIGINS 等（compose 自动加载）

set -euo pipefail

BRANCH=""
SKIP_PULL=0
SKIP_PRUNE=0
HEALTH_URL="http://127.0.0.1:8900/api/health"
HEALTH_RETRIES=30
HEALTH_INTERVAL=2

usage() {
  sed -n '2,10p' "$0" | sed 's/^# \?//'
  echo
  echo "选项："
  echo "  --branch <name>   拉取并切换到指定分支（默认：当前分支）"
  echo "  --no-pull         跳过 git fetch / pull"
  echo "  --no-prune        部署成功后不清理悬空 Docker 镜像"
  echo "  -h, --help        显示此帮助"
}

log() { printf '[deploy] %s\n' "$*"; }
die() { log "错误: $*"; exit 1; }

# 忽略 chmod 等仅权限变更（服务器上 chmod +x deploy.sh 不应阻断部署）
git_diff_quiet() {
  git -c core.fileMode=false diff --quiet "$@"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --branch)
      [[ $# -ge 2 ]] || die "--branch 需要分支名"
      BRANCH="$2"
      shift 2
      ;;
    --no-pull)
      SKIP_PULL=1
      shift
      ;;
    --no-prune)
      SKIP_PRUNE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "未知参数: $1（使用 --help 查看用法）"
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${REPO_ROOT}/docker/docker-compose.yml"

command -v git >/dev/null 2>&1 || die "未找到 git"
command -v docker >/dev/null 2>&1 || die "未找到 docker"

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose -f "${COMPOSE_FILE}")
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose -f "${COMPOSE_FILE}")
else
  die "未找到 docker compose（请安装 Docker Compose v2）"
fi

[[ -d "${REPO_ROOT}/.git" ]] || die "未检测到 git 仓库: ${REPO_ROOT}"
[[ -f "${COMPOSE_FILE}" ]] || die "未找到 compose 文件: ${COMPOSE_FILE}"

cd "${REPO_ROOT}"

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
TARGET_BRANCH="${BRANCH:-${CURRENT_BRANCH}}"

log "仓库: ${REPO_ROOT}"
log "分支: ${TARGET_BRANCH}（当前: ${CURRENT_BRANCH}）"
log "提交: $(git rev-parse --short HEAD) $(git log -1 --pretty=%s)"

if [[ "${SKIP_PULL}" -eq 0 ]]; then
  if ! git_diff_quiet || ! git_diff_quiet --cached; then
    log "以下未提交改动（不含仅权限变更）会阻断 git pull："
    git -c core.fileMode=false status --short
    die "请先 commit/stash 真实内容改动，或使用 --no-pull 跳过拉代码"
  fi

  log "拉取最新代码..."
  git fetch origin "${TARGET_BRANCH}"
  if [[ "${CURRENT_BRANCH}" != "${TARGET_BRANCH}" ]]; then
    git checkout "${TARGET_BRANCH}"
  fi
  git pull --ff-only origin "${TARGET_BRANCH}"
  log "更新后提交: $(git rev-parse --short HEAD) $(git log -1 --pretty=%s)"
else
  log "跳过 git pull（--no-pull）"
fi

export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

log "构建镜像（BuildKit + 国内镜像源，见 docker/docker-compose.yml）..."
"${COMPOSE[@]}" build

log "重启服务..."
"${COMPOSE[@]}" up -d --remove-orphans

log "等待健康检查: ${HEALTH_URL}"
ready=0
for ((i = 1; i <= HEALTH_RETRIES; i++)); do
  if curl -sf "${HEALTH_URL}" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep "${HEALTH_INTERVAL}"
done

if [[ "${ready}" -eq 1 ]]; then
  health_json="$(curl -sf "${HEALTH_URL}")"
  log "服务已就绪: ${health_json}"
else
  log "健康检查超时（${HEALTH_RETRIES}×${HEALTH_INTERVAL}s），最近日志："
  "${COMPOSE[@]}" logs --tail=80
  die "部署后服务未通过健康检查"
fi

log "容器状态:"
"${COMPOSE[@]}" ps

if [[ "${SKIP_PRUNE}" -eq 0 ]]; then
  log "清理悬空镜像..."
  docker image prune -f >/dev/null
fi

log "部署完成。访问 http://<服务器IP>:8900"
