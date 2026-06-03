FROM python:3.12-slim

# Install uv for fast package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies into the virtual environment
RUN uv sync --frozen --no-cache

# Copy codebase
COPY . .

# Ensure the virtual environment's bin folder is in PATH
ENV PATH="/app/.venv/bin:$PATH"

# Run the interactive agent CLI
CMD ["python", "main.py"]
