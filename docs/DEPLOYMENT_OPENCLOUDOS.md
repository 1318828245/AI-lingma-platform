# OpenCloudOS 9.6 部署准备手册

本文记录 AI 灵码平台部署到单台 OpenCloudOS 9.6 云服务器的初始化和 M6-2 部署步骤。主机初始化与 Docker 运行时已验收；生产 Compose、Nginx 反向代理和 PostgreSQL 配置已提交到工作区，HTTPS、备份和服务器实际启动验收仍待完成。

日常启动、停止、日志、配置、备份、升级和故障排查命令见 [DEPLOYMENT_QUICK_COMMANDS.md](DEPLOYMENT_QUICK_COMMANDS.md)。

生产环境变量应以 `.env.production.example` 为结构参考，但不要把 `backend/.env` 原样复制到生产：Compose 会注入 PostgreSQL 的 `AI_LINGMA_DATABASE_URL`，并将 `AI_LINGMA_STORAGE_DIR`、`AI_LINGMA_BACKEND_URL` 覆盖为容器内部路径；开发环境的 `AI_LINGMA_COMMAND_MODE=shell` 也不得带入生产。需要同步的真实服务配置包括 DeepSeek、Qwen 视觉模型和（可选的）Pexels/Pixabay/Unsplash Key，均只写服务器 `.env.production`。

## 适用范围与前提

- 服务器：OpenCloudOS 9.6，`x86_64`；本次已核验为 4G 内存、60G 磁盘、1G swap。
- 登录方式：云厂商控制台的 `root` 会话，以及本地 Windows PowerShell。
- 目标账号：`deploy`，用于日常部署；不要用 root 运行应用。
- 本文不会将 `deploy` 加入 `docker` 组。该组能实质取得主机 root 级能力，部署命令暂统一使用 `sudo docker`。

> 不要在云安全组或系统防火墙开放 Docker 2375/2376 端口。

## 1. 配置云安全组

初始化阶段仅需允许：

- TCP `22`：来源限制为自己的固定公网 IP；若公网 IP 会变化，至少使用尽可能小的来源范围。

暂不开放 TCP `80`、`443`；完成 Nginx 和 HTTPS 配置后再开放。绝不开放 `2375`、`2376`。

## 2. 更新系统并启用防火墙

在 root 控制台执行：

```bash
dnf update -y
dnf install -y git curl vim firewalld

systemctl enable --now firewalld
firewall-cmd --permanent --add-service=ssh
firewall-cmd --reload
firewall-cmd --list-all
```

预期：`services` 中包含 `ssh`。此时不要依赖云安全组以外的端口放行。

## 3. 创建部署用户并配置 SSH 密钥

### 3.1 在服务器 root 控制台创建账号

```bash
useradd -m -s /bin/bash deploy
passwd deploy
usermod -aG wheel deploy

install -d -m 700 -o deploy -g deploy /home/deploy/.ssh
echo 'deploy ALL=(ALL) ALL' > /etc/sudoers.d/deploy
chmod 440 /etc/sudoers.d/deploy
visudo -cf /etc/sudoers.d/deploy
```

最后一条应显示 `parsed: OK`。

### 3.2 在本地 Windows 生成公钥

PowerShell：

```powershell
ssh-keygen -t ed25519 -C "ai-lingma-server"
Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub
```

复制第二条命令输出的整行公钥。在服务器 root 控制台中执行：

```bash
vim /home/deploy/.ssh/authorized_keys
chown deploy:deploy /home/deploy/.ssh/authorized_keys
chmod 600 /home/deploy/.ssh/authorized_keys
```

### 3.3 验收

在本地新开 PowerShell：

```powershell
ssh deploy@<服务器公网IP>
```

登录后执行：

```bash
whoami
sudo -l
sudo firewall-cmd --list-all
```

预期：`whoami` 输出 `deploy`，`sudo -l` 不再报无权限。

## 4. 禁止高风险 SSH 登录方式

仅在上一步已确认 `deploy` 可以通过密钥登录并可使用 sudo 后执行。执行时保留当前已登录的 SSH 会话，且不要立即关闭。

```bash
sudo tee /etc/ssh/sshd_config.d/99-ai-lingma.conf > /dev/null <<'EOF'
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
EOF

sudo sshd -t
sudo systemctl reload sshd
```

然后在 Windows **新开** PowerShell 验证：

```powershell
ssh deploy@<服务器公网IP>
```

新会话成功后，才可关闭旧会话。这样可避免 SSH 配置错误导致无法登录。

## 5. 安装 Docker Engine 与 Compose

在 `deploy` 用户下执行：

```bash
sudo dnf install -y dnf-plugins-core
sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo dnf clean all

sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker

sudo docker version
sudo docker compose version
sudo docker run --rm hello-world
```

OpenCloudOS 9 使用 Docker 时需要 Docker 版本高于 20.10.9。Docker Compose 应以插件形式安装，命令为 `docker compose`（中间有空格），而不是旧的 `docker-compose`。

### 常见错误：仓库 URL 末尾多出 `~`

正确的地址必须恰好以 `.repo` 结束：

```text
https://download.docker.com/linux/centos/docker-ce.repo
```

如果误输入为 `.repo~`，会导致 `repodata/repomd.xml` 返回 404，Docker 不会被安装，随后执行 `systemctl enable --now docker` 会出现 `docker.service does not exist`。

修复命令：

```bash
sudo rm -f /etc/yum.repos.d/download.docker.com_linux_centos_docker-ce.repo_.repo
sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo dnf clean all
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo docker run --rm hello-world
```

若 `rm` 提示文件不存在，可以忽略；它只是在清理错误 URL 所生成的仓库文件。

## 6. 创建应用与数据目录

```bash
sudo install -d -o deploy -g deploy /opt/ai-lingma
sudo install -d -o deploy -g deploy /srv/ai-lingma-data
```

- `/opt/ai-lingma`：部署代码和 Compose 配置。
- `/srv/ai-lingma-data`：数据库、生成工作区和其他必须持久化的数据；后续 Compose 将只挂载这一受控位置。

## 7. 当前阶段验收清单

```bash
whoami
sudo docker version --format '{{.Server.Version}}'
sudo docker compose version
sudo docker run --rm hello-world
sudo systemctl is-enabled docker
sudo systemctl is-active docker
df -h
free -h
```

预期 Docker 服务为 `enabled` 且 `active`，并能看到 `hello-world` 的成功提示。

## 8. M6-2 Compose 部署基线（尚待服务器执行）

代码库根目录已提供：

- `docker-compose.yml`：内部 PostgreSQL、后端和 Web 三个服务；数据库端口不发布，Web 仅绑定宿主机 `127.0.0.1:8080`。
- `docker/backend/Dockerfile`：非 root FastAPI 运行镜像。
- `docker/frontend/Dockerfile` 与 `docker/nginx/default.conf`：Vue 构建和 API/SSE/预览反代。
- `.env.production.example`：生产变量模板，必须复制为未提交的 `.env.production`。

不要把 `/var/run/docker.sock` 挂载进 `backend` 服务。生产模板默认 `AI_LINGMA_BUILD_MODE=mock`、`AI_LINGMA_COMMAND_MODE=sandbox`；可以在保持 mock 构建的同时启用真实 LLM，用于真实生成和受控文件编辑。真实 npm 构建与 Docker 命令沙箱仍须等待独立执行器验收后才可开启。

### 8.1 首次启动（仅服务器本机验收）

此阶段不要在云安全组开放 80/443。以 `deploy` 用户登录后执行：

```bash
sudo install -d -o deploy -g deploy /opt/ai-lingma
sudo install -d -o deploy -g deploy /srv/ai-lingma-data

git clone https://github.com/1318828245/AI-lingma-platform.git /opt/ai-lingma
cd /opt/ai-lingma

cp .env.production.example .env.production
chmod 600 .env.production

id -u deploy
id -g deploy
vim .env.production
```

如果 `/opt/ai-lingma` 已是此前克隆的仓库，不要再次 clone，改为：

```bash
cd /opt/ai-lingma
git pull --ff-only origin main
```

### 8.2 填写生产变量

在服务器本地生成三份不同的随机值：

```bash
openssl rand -hex 32
```

每次执行会输出一份只含十六进制字符的随机值；分别填入 `.env.production` 的下列字段。使用十六进制可避免 `$`、`:` 等字符被 Compose 插值误解析。

```dotenv
POSTGRES_PASSWORD=<第一份随机值>
AI_LINGMA_JWT_SECRET=<第二份随机值>
AI_LINGMA_ADMIN_PASSWORD=<第三份随机值或自行设置的强密码>
```

将 `AI_LINGMA_RUNTIME_UID` 和 `AI_LINGMA_RUNTIME_GID` 改为前一步 `id -u deploy`、`id -g deploy` 的输出；当前服务器预期为 `1002`。首次启动保持下列安全默认值：

```dotenv
AI_LINGMA_BUILD_MODE=mock
AI_LINGMA_COMMAND_MODE=sandbox
AI_LINGMA_LLM_MODEL=mock
```

不要在此阶段改为 `AI_LINGMA_COMMAND_MODE=docker`。

### 8.3 启用真实 DeepSeek API（域名 HTTPS 就绪后）

真实 API Key 只能写入服务器 `/opt/ai-lingma/.env.production`，不得粘贴到聊天、提交到 Git、写进前端或镜像。编辑该文件，将下列三项改为实际值：

```dotenv
AI_LINGMA_LLM_MODEL=deepseek-v4-flash
AI_LINGMA_LLM_BASE_URL=https://api.deepseek.com
AI_LINGMA_LLM_API_KEY=<只在服务器本地粘贴的 DeepSeek API Key>
```

保持：

```dotenv
AI_LINGMA_BUILD_MODE=mock
AI_LINGMA_COMMAND_MODE=sandbox
```

这样会使用真实 DeepSeek 进行需求解析、计划和代码生成，但构建验证保持 mock，避免在公开 Web 后端中运行不受独立执行器保护的 npm 安装。修改变量后重建后端容器：

```bash
cd /opt/ai-lingma
sudo docker compose --env-file .env.production up -d --no-deps backend
sudo docker compose --env-file .env.production logs --tail=100 backend
```

DeepSeek 当前 OpenAI 兼容基础地址为 `https://api.deepseek.com`，可使用 `deepseek-v4-flash` 或 `deepseek-v4-pro`。详见 [DeepSeek API 快速开始](https://api-docs.deepseek.com/quick_start/pricing-details-cny/)。

### 8.4 管理员密码不匹配时的重置

`AI_LINGMA_ADMIN_PASSWORD` 只在首次创建管理员时生效；修改环境文件不会自动覆盖数据库中的已有密码。如果登录页面持续提示用户名或密码错误，可在服务器交互式输入新密码并直接更新已有管理员：

```bash
cd /opt/ai-lingma
read -r -s -p '新管理员密码: ' NEW_ADMIN_PASSWORD; echo
sudo docker compose --env-file .env.production exec -T \
  -e NEW_ADMIN_PASSWORD="$NEW_ADMIN_PASSWORD" backend \
  python -c 'import os; from app.core.database import SessionLocal; from app.core.security import hash_password; from app.models.user import User; db=SessionLocal(); user=db.query(User).filter(User.username == "admin").one(); user.password_hash=hash_password(os.environ["NEW_ADMIN_PASSWORD"]); db.commit(); print("管理员密码已更新")'
unset NEW_ADMIN_PASSWORD
```

该命令不删除项目和数据库，只更新 `admin` 的密码哈希。若管理员用户名不是 `admin`，将 Python 命令中的用户名替换为实际值；密码输入不会回显。

### 8.5 校验、构建并启动

先只检查 Compose 配置，再使用单线程构建启动。2 核 4G 主机不宜同时并行构建多个镜像。

```bash
sudo docker compose --env-file .env.production config
sudo env COMPOSE_PARALLEL_LIMIT=1 docker compose --env-file .env.production up -d --build
sudo docker compose --env-file .env.production ps
curl -fsS http://127.0.0.1:8080/healthz
curl -fsS http://127.0.0.1:8080/api/health
```

预期：`ps` 中 `postgres`、`backend`、`web` 均为运行状态；两个 `curl` 分别返回 `ok` 和 JSON 健康状态。若启动失败，先收集日志，不要删除数据卷：

```bash
sudo docker compose --env-file .env.production logs --tail=100 postgres backend web
```

后端镜像启动时会幂等执行 `python -m app.scripts.init`，首次启动会创建 `.env.production` 指定的管理员和种子模板，已有管理员密码不会被覆盖。若当前服务器运行的是旧镜像，首次可手动执行一次：

```bash
sudo docker compose --env-file .env.production exec -T backend python -m app.scripts.init
```

首次成功后，Web 仍只监听 `127.0.0.1:8080`，公网无法访问是预期行为。完成宿主 Nginx、域名和 HTTPS 后才开放 80/443。

## 9. 临时公网 IP + HTTP 验证

在域名申请完成前，可用服务器公网 IP 做**短期** HTTP 验证。HTTP 不加密登录令牌和密码，因此不应作为长期方案，也不要用于真实 LLM 密钥或真实业务数据。

### 9.1 云安全组

新增 TCP `80` 入站规则，来源优先限制为自己的固定公网 IP。不要开放 `8080`；Compose 已将它只绑定在服务器回环地址。仍不开放 `443`、`2375`、`2376`。

### 9.2 安装并配置宿主 Nginx

在 `deploy` 用户的 SSH 会话中执行：

```bash
sudo dnf install -y nginx
sudo tee /etc/nginx/conf.d/ai-lingma.conf > /dev/null <<'EOF'
server {
    listen 80 default_server;
    server_name 124.223.213.147;
    client_max_body_size 2m;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        proxy_read_timeout 1200s;
    }
}
EOF

sudo nginx -t
sudo systemctl enable --now nginx
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --reload
sudo firewall-cmd --list-all
```

若 `nginx -t` 报 `default_server` 重复，先查看已有虚拟主机：

```bash
sudo grep -R "listen 80" /etc/nginx/conf.d /etc/nginx/nginx.conf
```

将冲突的默认站点移除或改为普通 `listen 80;` 后，再运行 `sudo nginx -t`；不要在测试失败时重启 Nginx。

### 9.3 验收与临时登录

在服务器执行：

```bash
curl -fsS http://127.0.0.1/
sudo systemctl is-active nginx
```

在自己的浏览器访问：

```text
http://124.223.213.147
```

使用部署时设定的 `AI_LINGMA_ADMIN_USERNAME` 和 `AI_LINGMA_ADMIN_PASSWORD` 登录。只验证页面、登录、创建项目和 mock 生成流程；不要在 HTTP 阶段填入真实 LLM/API 密钥。

完成验证后，若不再需要临时公网访问，先在云安全组删除 TCP 80 规则，再执行：

```bash
sudo firewall-cmd --permanent --remove-service=http
sudo firewall-cmd --reload
```

## 10. 域名、Nginx 与 HTTPS

Compose 的 Web 端口只监听 `127.0.0.1:8080`，公网流量必须由宿主 Nginx 接收并反代到该端口。不要绕过 Nginx 将 8080 直接暴露公网。

### 10.1 DNS 与安全组前置条件

假设正式域名为 `app.example.com`：

1. 在 DNS 服务商添加 `A` 记录：`app.example.com` → `124.223.213.147`；
2. 等待 `nslookup app.example.com` 返回该 IP；
3. 在云安全组开放 TCP `80` 和 `443` 给 `0.0.0.0/0`；
4. 在服务器防火墙放行 `http`、`https`；不开放 `8080`、`2375`、`2376`。

申请 Let's Encrypt 证书时，域名必须已经解析到本机，且公网能访问 80 端口。

### 10.2 配置 HTTP 站点与反向代理

本服务器已确认使用云镜像预装的 Nginx，主配置为 `/www/server/nginx/conf/nginx.conf`，虚拟主机由 `/www/server/panel/vhost/nginx/*.conf` 加载。不要再启动通过 dnf 安装的 `/usr/sbin/nginx` systemd 服务，也不要同时运行两套监听 80 的 Nginx。

临时使用公网 IP 时，在预装 Nginx 的虚拟主机目录写入：

```bash
sudo systemctl disable nginx
sudo systemctl stop nginx
sudo tee /www/server/panel/vhost/nginx/ai-lingma.conf > /dev/null <<'EOF'
server {
    listen 80;
    server_name 124.223.213.147;
    client_max_body_size 2m;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        proxy_read_timeout 1200s;
    }
}
EOF

sudo /www/server/nginx/sbin/nginx -t -c /www/server/nginx/conf/nginx.conf
sudo /www/server/nginx/sbin/nginx -s reload -c /www/server/nginx/conf/nginx.conf
curl -I -H 'Host: 124.223.213.147' http://127.0.0.1
```

临时 IP 验收通过后，域名上线时只需将该文件的 `server_name` 改为正式域名，并在同一套 `/www/server/nginx` 上执行 Certbot/证书配置；不要把配置复制到 `/etc/nginx/conf.d/`。

如果直接执行 `dnf install nginx` 出现 `All matches were filtered out by exclude filtering`，先不要修改仓库文件，使用一次性绕过排除规则的安装：

```bash
sudo dnf --disableexcludes=all install -y nginx
```

如果随后出现 `nginx-stable` 版本依赖 `libssl.so.3(OPENSSL_3.2.0)` 或 `OPENSSL_3.5.0`，说明误选了 Nginx 官方新版本仓库，而 OpenCloudOS 9 的系统 OpenSSL 版本较低。不要使用 `--skip-broken`，改为禁用该仓库、从系统 AppStream 安装：

```bash
sudo dnf module list nginx
sudo dnf --disableexcludes=all --disablerepo=nginx-stable install -y nginx
```

如果 AppStream 提供模块但没有默认流，再根据 `dnf module list nginx` 显示的可用版本启用对应流，例如：

```bash
sudo dnf module enable -y nginx:1.24
sudo dnf --disableexcludes=all --disablerepo=nginx-stable install -y nginx
```

不要为解决该问题升级系统 OpenSSL，也不要混装来自不同发行版的 RPM。

若仍提示找不到包，检查排除规则和已启用仓库：

```bash
sudo grep -RniE '^(exclude|includepkgs)|nginx' /etc/dnf /etc/yum.repos.d
sudo dnf repolist --enabled
sudo dnf repoquery --available nginx
```

OpenCloudOS 官方文档说明 EPOL 源用于提供增强软件包；确认系统没有 EPOL 源时再安装并重试：

```bash
sudo dnf install -y opencloudos-stream-epol-repos
sudo dnf clean all
sudo dnf --disableexcludes=all install -y nginx
```

只有在 OpenCloudOS 源确实没有可用 Nginx 包时，才考虑使用 [Nginx 官方 RHEL 9 软件源](https://nginx.org/en/linux_packages.html)，不要混用来源不明的 RPM。

替换下面的 `<DOMAIN>` 与 `<ADMIN_EMAIL>`，并确保 `.env.production` 中的 `AI_LINGMA_CORS_ORIGINS` 同步为 `["https://<DOMAIN>"]`：

```bash
sudo cp /etc/nginx/conf.d/ai-lingma.conf /etc/nginx/conf.d/ai-lingma.conf.before-tls
sudo tee /etc/nginx/conf.d/ai-lingma.conf > /dev/null <<'EOF'
server {
    listen 80;
    server_name <DOMAIN>;
    client_max_body_size 2m;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        proxy_read_timeout 1200s;
    }
}
EOF
sudo nginx -t
sudo systemctl reload nginx

sudo dnf install -y certbot python3-certbot-nginx
sudo certbot --nginx -d <DOMAIN> --email <ADMIN_EMAIL> --agree-tos --no-eff-email --redirect
```

若 OpenCloudOS 仓库未提供 `certbot` 或 `python3-certbot-nginx`，不要从不明第三方仓库下载安装；改用 [Certbot 官方安装说明](https://certbot.eff.org/instructions?os=centosrhel8&tab=standard&ws=nginx) 所列的受支持方式。Certbot 需要 root 权限并要求端口 80 可由公网访问。

### 10.3 HTTPS 验收与续期

```bash
sudo nginx -t
sudo systemctl is-active nginx
sudo certbot renew --dry-run
curl -I https://<DOMAIN>
```

浏览器访问 `https://<DOMAIN>`，登录并验证一次真实生成。确认无误后，可删除临时 IP HTTP 配置中的 `default_server`，并在云安全组删除仅为临时调试而存在的规则。

## 11. 备份、恢复与升级

### 11.1 安装备份定时器

项目已提供 `scripts/backup.sh`，备份 PostgreSQL 自定义格式导出、`storage` 压缩包和 SHA-256 校验和，默认保留 7 天。先手工运行一次：

```bash
cd /opt/ai-lingma
sudo chmod 750 scripts/backup.sh
sudo ./scripts/backup.sh
sudo find /srv/ai-lingma-data/backups -maxdepth 2 -type f | sort
```

启用每日 03:20 UTC 的 systemd 定时器：

```bash
sudo install -m 644 deploy/systemd/ai-lingma-backup.service /etc/systemd/system/ai-lingma-backup.service
sudo install -m 644 deploy/systemd/ai-lingma-backup.timer /etc/systemd/system/ai-lingma-backup.timer
sudo systemctl daemon-reload
sudo systemctl enable --now ai-lingma-backup.timer
sudo systemctl list-timers ai-lingma-backup.timer
```

备份目录应同步到另一台受控机器或对象存储；同一台服务器上的备份不能抵御主机丢失。

### 11.2 恢复演练

恢复会覆盖数据库和 storage，只能在维护窗口进行。先停止应用、复制现有数据并验证备份校验和：

```bash
cd /opt/ai-lingma
BACKUP=/srv/ai-lingma-data/backups/<UTC时间戳>
set -a; source .env.production; set +a
(cd "$BACKUP" && sha256sum -c SHA256SUMS)
sudo docker compose --env-file .env.production stop backend web
sudo docker compose --env-file .env.production exec -T postgres \
  pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists < "$BACKUP/postgres.dump"
sudo tar --extract --gzip --file "$BACKUP/storage.tar.gz" --directory /srv/ai-lingma-data
sudo docker compose --env-file .env.production up -d backend web
```

`source .env.production` 仅在服务器本地、可信 shell 中执行；不要在不理解覆盖范围时运行此段命令。

### 11.3 升级与失败回退

每次升级前先执行备份，再拉取提交并重建；不要使用 `docker compose down -v`，它会删除 PostgreSQL 数据卷。

```bash
cd /opt/ai-lingma
git status --short
sudo ./scripts/backup.sh
git pull --ff-only origin main
sudo env COMPOSE_PARALLEL_LIMIT=1 docker compose --env-file .env.production up -d --build
sudo docker compose --env-file .env.production ps
curl -fsS http://127.0.0.1:8080/api/health
```

若新版本健康检查失败，停止进一步操作，记录 `git rev-parse HEAD`、收集 `docker compose logs --tail=200`，再在维护窗口根据上一提交和已验证备份执行回退；不要在未确认数据库兼容性时直接强制 `git reset --hard`。

## 12. M6-2 完成标准与遗留边界

M6-2 的部署基线完成标准：Compose 三服务健康、域名 HTTPS、真实 LLM 密钥仅驻留服务器、每日备份定时器、升级前备份和恢复演练均通过。

仍未完成：独立 Docker 命令沙箱执行器、严格预览隔离、跨进程任务队列和多机备份。上述能力未完成前，生产保持 `AI_LINGMA_BUILD_MODE=mock`、`AI_LINGMA_COMMAND_MODE=sandbox`。

## 参考

- [OpenCloudOS 9 安装指南](https://docs.opencloudos.org/OC9/install/V9_install/)
- [Docker Engine for CentOS 安装指南](https://docs.docker.com/engine/install/centos/)
- [Docker Compose 生产环境建议](https://docs.docker.com/compose/how-tos/production/)
