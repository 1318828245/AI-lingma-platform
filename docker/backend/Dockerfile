FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Chromium 用于项目缩略图和视觉评估；Node/npm 仅供受控构建路径使用。
RUN apt-get update \
    && apt-get install -y --no-install-recommends chromium nodejs npm \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 --shell /usr/sbin/nologin app

WORKDIR /app
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend /app
COPY docker/backend/start.sh /app/start.sh
RUN mkdir -p /data \
    && chmod 755 /app/start.sh \
    && chown -R app:app /app /data

USER app
EXPOSE 8000

CMD ["/app/start.sh"]
