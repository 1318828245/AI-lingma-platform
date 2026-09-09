# Docker 命令沙箱

构建基础镜像：

```powershell
docker build -t ai-lingma-sandbox:node20 -f backend/docker/sandbox/Dockerfile backend
```

设置 `AI_LINGMA_COMMAND_MODE=docker` 后，非内置命令会在独立容器中执行：默认无网络、移除 Linux capabilities、禁止新增权限、限制 PID/CPU/内存、只读根文件系统，仅工作区以读写方式挂载到 `/workspace`。

镜像不在运行时下载 npm 依赖。Vue 依赖应来自锁定版本的扩展镜像或受控离线 npm 缓存；不要为安装依赖放开沙箱网络。`shell` 仅限本地开发。
