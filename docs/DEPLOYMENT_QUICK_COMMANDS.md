# AI 灵码平台生产快速命令手册

适用于服务器目录 `/opt/ai-lingma`，执行用户为 `deploy`。命令默认不会删除 PostgreSQL 数据卷。

## 进入项目与状态

```bash
cd /opt/ai-lingma
sudo docker compose --env-file .env.production ps
sudo docker compose --env-file .env.production top
df -h
free -h
```

## 启动、停止、重启

```bash
# 启动已有镜像
sudo docker compose --env-file .env.production up -d

# 代码更新后单线程构建启动（2 核 4G 推荐）
sudo env COMPOSE_PARALLEL_LIMIT=1 docker compose --env-file .env.production up -d --build

# 重启全部服务
sudo docker compose --env-file .env.production restart

# 只重启后端（修改环境变量后）
sudo docker compose --env-file .env.production up -d --no-deps backend

# 停止容器，保留数据
sudo docker compose --env-file .env.production stop

# 删除容器和网络，保留命名卷
sudo docker compose --env-file .env.production down
```

生产环境禁止随意使用 `down -v`，否则会删除 PostgreSQL 数据卷。

## 健康检查和日志

```bash
curl -fsS http://127.0.0.1:8080/healthz
curl -fsS http://127.0.0.1:8080/api/health
sudo docker compose --env-file .env.production logs --tail=100 backend
sudo docker compose --env-file .env.production logs --tail=100 web
sudo docker compose --env-file .env.production logs --tail=100 postgres
sudo docker compose --env-file .env.production logs -f backend
```

实时日志使用 `Ctrl+C` 退出，不会停止服务。

## 修改生产配置

```bash
cd /opt/ai-lingma
cp -p .env.production ".env.production.$(date -u +%Y%m%dT%H%M%SZ).bak"
chmod 600 .env.production
vim .env.production

sudo docker compose --env-file .env.production config -q
sudo docker compose --env-file .env.production up -d --no-deps backend
```

首次部署或旧镜像没有自动初始化时：

```bash
sudo docker compose --env-file .env.production exec -T backend python -m app.scripts.init
```

## 启用真实 DeepSeek API

编辑 `.env.production`，真实 Key 只保存在服务器：

```dotenv
AI_LINGMA_LLM_MODEL=deepseek-v4-flash
AI_LINGMA_LLM_BASE_URL=https://api.deepseek.com
AI_LINGMA_LLM_API_KEY=真实Key
AI_LINGMA_BUILD_MODE=mock
AI_LINGMA_COMMAND_MODE=sandbox

# Qwen 视觉评估
AI_LINGMA_EVAL_VISION_PROVIDER=qwen_compatible
AI_LINGMA_EVAL_VISION_MODEL=qwen3-vl-flash
AI_LINGMA_EVAL_VISION_BASE_URL=Qwen兼容OpenAI接口地址
AI_LINGMA_EVAL_VISION_API_KEY=真实Key
AI_LINGMA_EVAL_VISION_THINKING_ENABLED=false
```

应用配置：

```bash
chmod 600 .env.production
sudo docker compose --env-file .env.production up -d --no-deps backend
sudo docker compose --env-file .env.production logs --tail=100 backend
```

不要将 `.env.production` 提交到 Git，也不要在日志、截图或聊天中暴露 API Key。

本地 `backend/.env` 与生产配置的对应关系：

| 配置 | 是否同步 | 说明 |
| --- | --- | --- |
| `LLM_MODEL`、`LLM_BASE_URL`、`LLM_API_KEY` | 是 | DeepSeek 真实生成 |
| `EVAL_VISION_*` | 是 | Qwen 截图视觉评估 |
| `ASSET_*_API_KEY` | 可选 | Pexels/Pixabay/Unsplash 素材来源 |
| `DATABASE_URL` | 否 | Compose 注入 PostgreSQL 地址 |
| `STORAGE_DIR`、`BACKEND_URL` | 否 | Compose 使用容器内部路径/服务名 |
| `COMMAND_MODE=shell` | 否 | 仅本地开发，生产保持 `sandbox` |
| `DEBUG=true` | 否 | 生产必须为 `false` |

## 重置管理员密码

```bash
read -r -s -p '新管理员密码: ' NEW_ADMIN_PASSWORD
echo
sudo docker compose --env-file .env.production exec -T \
  -e NEW_ADMIN_PASSWORD="$NEW_ADMIN_PASSWORD" backend python - <<'PY'
import os
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User

db = SessionLocal()
try:
    user = db.query(User).filter(User.username == "admin").one()
    user.password_hash = hash_password(os.environ["NEW_ADMIN_PASSWORD"])
    db.commit()
    print("管理员密码已更新")
finally:
    db.close()
PY
unset NEW_ADMIN_PASSWORD
```

## 手工备份和定时器

```bash
sudo chmod 750 scripts/backup.sh
sudo ./scripts/backup.sh
sudo find /srv/ai-lingma-data/backups -maxdepth 2 -type f -print | sort
sudo systemctl status ai-lingma-backup.timer --no-pager
sudo systemctl list-timers ai-lingma-backup.timer
```

恢复操作会覆盖数据库和 storage，只能按部署文档的维护窗口流程执行。

## 更新代码

```bash
git status --short
sudo ./scripts/backup.sh
git fetch origin
git pull --ff-only origin main
sudo env COMPOSE_PARALLEL_LIMIT=1 docker compose --env-file .env.production up -d --build
sudo docker compose --env-file .env.production ps
curl -fsS http://127.0.0.1:8080/api/health
```

失败时先保存日志和当前提交，不要直接删除数据卷：

```bash
sudo docker compose --env-file .env.production logs --tail=200 backend web postgres > "/tmp/ai-lingma-failed-$(date -u +%Y%m%dT%H%M%SZ).log"
git rev-parse HEAD
```

## 本服务器预装 Nginx

当前实际运行的是 `/www/server/nginx`，虚拟主机目录是 `/www/server/panel/vhost/nginx/`：

```bash
sudo /www/server/nginx/sbin/nginx -t -c /www/server/nginx/conf/nginx.conf
sudo /www/server/nginx/sbin/nginx -s reload -c /www/server/nginx/conf/nginx.conf
sudo ss -ltnp | grep -E ':80|:443|:8080'
```

不要启动冲突的 `/usr/sbin/nginx` systemd 服务。修改配置后必须先通过 `nginx -t`。

## 故障排查顺序

```bash
sudo docker compose --env-file .env.production ps
curl -fsS http://127.0.0.1:8080/api/health
sudo docker compose --env-file .env.production logs --tail=200 backend
sudo docker compose --env-file .env.production logs --tail=200 web
sudo /www/server/nginx/sbin/nginx -t -c /www/server/nginx/conf/nginx.conf
sudo ss -ltnp | grep -E ':80|:443|:8080'
```

先判断是应用容器、Web 反代、Nginx 端口还是云安全组问题，再做单项修改。
