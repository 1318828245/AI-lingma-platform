# OpenCloudOS 9.6 部署准备手册

本文记录 AI 灵码平台部署到单台 OpenCloudOS 9.6 云服务器的初始化和 M6-2 部署步骤。主机初始化与 Docker 运行时已验收；生产 Compose、Nginx 反向代理和 PostgreSQL 配置已提交到工作区，HTTPS、备份和服务器实际启动验收仍待完成。

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

不要把 `/var/run/docker.sock` 挂载进 `backend` 服务。当前生产模板默认 `AI_LINGMA_BUILD_MODE=mock`、`AI_LINGMA_COMMAND_MODE=sandbox`；真实 LLM 生成和 Docker 命令沙箱需等独立执行器完成后才可开启。

实际部署将在 M6-2 构建验证通过后执行，预定步骤为：

```bash
cd /opt/ai-lingma
cp .env.production.example .env.production
chmod 600 .env.production
# 填入高强度 PostgreSQL、JWT、管理员密码和正式域名后；
# 同时以 `id -u deploy` / `id -g deploy` 的输出填写 AI_LINGMA_RUNTIME_UID/GID：
sudo docker compose --env-file .env.production config
sudo docker compose --env-file .env.production up -d --build
sudo docker compose --env-file .env.production ps
```

## 9. 宿主 Nginx、HTTPS 与备份（待 M6-2 验证后执行）

Compose 的 Web 端口只监听 `127.0.0.1:8080`，公网流量应由宿主 Nginx 接收并反代到该端口。开放 80/443、签发证书、配置域名和定时备份前，必须先完成 Compose 健康检查；不要绕过 Nginx 将 8080 直接暴露公网。

## M6-2 后续工作

通过本手册的验收并不代表应用已经部署。下一步应在代码库中补齐并验证：

1. 构建并验证前后端镜像、PostgreSQL 启动和 Compose 健康检查；
2. 配置宿主 Nginx、域名、HTTPS 和仅暴露 80/443 的网络边界；
3. 完成 Docker 命令沙箱的独立执行器和真实运行验收；
4. 完成 PostgreSQL/storage 备份、日志轮转、升级/回滚说明与演练。

在这些配置完成、测试并提交前，不要将当前开发态项目直接暴露到公网。

## 参考

- [OpenCloudOS 9 安装指南](https://docs.opencloudos.org/OC9/install/V9_install/)
- [Docker Engine for CentOS 安装指南](https://docs.docker.com/engine/install/centos/)
- [Docker Compose 生产环境建议](https://docs.docker.com/compose/how-tos/production/)
