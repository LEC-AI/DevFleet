FROM python:3.12-slim

WORKDIR /app

# Git is needed for worktree isolation
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create non-root user (claude CLI refuses --dangerously-skip-permissions as root)
RUN useradd -m -u 1001 devfleet && chown -R devfleet:devfleet /app
USER devfleet

EXPOSE 18801

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "18801", "--reload"]
