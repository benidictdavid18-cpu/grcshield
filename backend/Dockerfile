FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
# Invoked via `sh` so the script does not depend on an executable bit surviving
# a Windows build context or bind mount.
CMD ["sh", "./entrypoint.sh"]
