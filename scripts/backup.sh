#!/usr/bin/env bash
# 备份 PostgreSQL 与应用 storage；由 deploy 手工执行或 systemd timer 以 root 执行。
set -euo pipefail

APP_DIR="${AI_LINGMA_APP_DIR:-/opt/ai-lingma}"
ENV_FILE="${AI_LINGMA_ENV_FILE:-${APP_DIR}/.env.production}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "找不到生产环境变量文件：${ENV_FILE}" >&2
  exit 1
fi

# .env.production 仅允许由服务器管理员维护；此处只使用其数据库、数据目录配置。
set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

DATA_DIR="${AI_LINGMA_DATA_DIR:-/srv/ai-lingma-data}"
BACKUP_DIR="${AI_LINGMA_BACKUP_DIR:-${DATA_DIR}/backups}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TARGET_DIR="${BACKUP_DIR}/${STAMP}"

umask 077
mkdir -p "${TARGET_DIR}"
cd "${APP_DIR}"

docker compose --env-file "${ENV_FILE}" exec -T postgres \
  pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" --format=custom \
  > "${TARGET_DIR}/postgres.dump"

tar --create --gzip --file "${TARGET_DIR}/storage.tar.gz" \
  --directory "${DATA_DIR}" --exclude=backups .

(cd "${TARGET_DIR}" && sha256sum postgres.dump storage.tar.gz > SHA256SUMS)

# 保留最近 7 天；仅删除本脚本创建的 UTC 时间戳目录。
find "${BACKUP_DIR}" -mindepth 1 -maxdepth 1 -type d -name '20????????T??????Z' -mtime +7 -exec rm -rf -- {} +
echo "备份完成：${TARGET_DIR}"
