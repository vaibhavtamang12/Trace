FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/src
WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir .
COPY configs ./configs
COPY data ./data

EXPOSE 8000
CMD ["uvicorn", "recommendation_platform.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
