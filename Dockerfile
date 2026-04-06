# AcademiaOS -- multi-stage Docker build
# Stage 1: Build the React frontend
# Stage 2: Python runtime with pandoc, texlive, and Node.js for Claude CLI

# ---------------------------------------------------------------------------
# Stage 1 -- Frontend build
# ---------------------------------------------------------------------------
FROM node:20-slim AS frontend-build

WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --production=false
COPY frontend/ ./
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2 -- Python runtime
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# System deps: pandoc for doc conversion, texlive-base for PDF generation,
# curl + Node.js for Claude CLI, and git for potential vault operations.
RUN apt-get update && apt-get install -y --no-install-recommends \
        pandoc \
        texlive-base \
        texlive-latex-recommended \
        curl \
        git \
        r-base-core \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g @anthropic-ai/claude-code \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Application source
COPY src/ ./src/
COPY prompts/ ./prompts/
COPY scripts/ ./scripts/
COPY config/ ./config/

# Frontend dist from build stage
COPY --from=frontend-build /build/dist ./frontend/dist

# Entrypoint
COPY entrypoint.sh ./
RUN chmod +x entrypoint.sh

# Persistent volumes for user data
VOLUME ["/app/vaults", "/app/files", "/app/progress"]

# Default environment
ENV PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8000

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
