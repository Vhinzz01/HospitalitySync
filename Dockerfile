FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --system hospitalitysync \
    && useradd --system --gid hospitalitysync --create-home hospitalitysync

COPY requirements.txt ./
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY --chown=hospitalitysync:hospitalitysync alembic.ini ./
COPY --chown=hospitalitysync:hospitalitysync alembic ./alembic
COPY --chown=hospitalitysync:hospitalitysync app ./app

USER hospitalitysync

EXPOSE 8000

CMD ["sh", "-c", "python -m alembic upgrade head && exec python -m uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000"]
