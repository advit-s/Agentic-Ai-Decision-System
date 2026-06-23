# Agentic Decision System - Local Development Dockerfile
# No secrets baked in. Fake/offline provider is the default.
# No real provider keys required for build or basic run.

FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml README.md LICENSE ./
COPY src/ src/
COPY company_docs/.gitkeep company_docs/
COPY company_data/manifest.json company_data/
COPY tests/ tests/
# docs/ is excluded by .dockerignore to keep image size small
COPY web/ web/

# Install in dev mode (includes test deps)
RUN pip install --no-cache-dir -e ".[dev,doc-parsing]"

# Create .decision_system/ dir (generated at runtime, ignored by git)
RUN mkdir -p .decision_system

# Default environment: fake/offline mode
ENV DECISION_PROVIDER=fake
ENV PYTHONUNBUFFERED=1

# Default port for FastAPI
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "from decision_system import __version__; print(__version__)" || exit 1

# Default: run the API
CMD ["decision-system", "serve-api", "--host", "0.0.0.0", "--port", "8000"]
