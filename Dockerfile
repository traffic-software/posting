FROM python:3.12-slim

ARG VCS_REF=local
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_REVISION=${VCS_REF}

WORKDIR /srv/app
COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock
COPY app ./app

RUN groupadd --system app && useradd --system --gid app app \
    && mkdir -p /data && chown app:app /data
USER app

EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
