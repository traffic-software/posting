FROM python:3.12-slim

ARG VCS_REF=local
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_REVISION=${VCS_REF} \
    HOME=/home/app \
    XDG_RUNTIME_DIR=/tmp/runtime-app

WORKDIR /srv/app
COPY requirements.lock ./
RUN apt-get update \
    && apt-get install -y --no-install-recommends chromium chromium-driver xvfb \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -r requirements.lock
RUN apt-get update \
    && apt-get install -y --no-install-recommends libtk8.6 chromium-sandbox openbox \
    && rm -rf /var/lib/apt/lists/* \
    && python -c 'import tkinter'
COPY app ./app

RUN groupadd --system app && useradd --system --gid app --create-home app \
    && mkdir -p /data "$XDG_RUNTIME_DIR" \
    && touch "$HOME/.Xauthority" \
    && chown -R app:app /data "$HOME" "$XDG_RUNTIME_DIR"
USER app

EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
