FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Runs as an unprivileged user. Migrations and seeding need nothing root can do, and a
# container that runs as root turns any code-execution bug into a root shell.
RUN adduser --system --no-create-home --group app && chown -R app:app /app
USER app

EXPOSE 8000
# Invoked via `sh` so the script does not depend on an executable bit surviving
# a Windows build context or bind mount.
CMD ["sh", "./entrypoint.sh"]
