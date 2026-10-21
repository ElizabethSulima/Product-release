FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

COPY pyproject.toml poetry.lock ./

RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --only main --no-interaction

WORKDIR /app

COPY . .

EXPOSE 8000

CMD ["uvicorn", "src.main:app_fast", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--workers", "4"]