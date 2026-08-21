#!/bin/sh
set -eu

# 幂等初始化：首次创建管理员和种子模板，已有数据不会覆盖密码或业务数据。
python -m app.scripts.init
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips=*
