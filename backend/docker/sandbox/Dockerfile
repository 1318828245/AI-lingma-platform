# M6-1：生成/构建命令的最小 Docker 沙箱基础镜像。
# 运行时由宿主服务附加 --network none、资源上限、只读根文件系统和工作区挂载。
FROM node:20-bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 make g++ \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 --shell /usr/sbin/nologin sandbox

USER sandbox
WORKDIR /workspace

# 不在镜像构建阶段安装任意项目依赖。生产环境应使用锁定版本的扩展镜像或离线 npm 缓存。
