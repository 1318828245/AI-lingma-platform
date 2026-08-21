# M6-1 Docker 命令沙箱

构建基础镜像：

```powershell
docker build -t ai-lingma-sandbox:node20 -f backend/docker/sandbox/Dockerfile backend
```

生产环境设置 `AI_LINGMA_COMMAND_MODE=docker`。每条非内置命令会在独立容器中运行：容器无网络、移除 Linux capabilities、禁止新增权限、限制 PID/CPU/内存，并使用只读根文件系统；仅项目工作区以读写方式挂载到 `/workspace`。

该基础镜像不在运行时下载 npm 依赖。Vue 项目的依赖必须来自锁定版本的扩展镜像或受控离线 npm 缓存；不要为了 `npm install` 放开容器网络。开发机可继续使用默认的 `AI_LINGMA_COMMAND_MODE=shell`。
