# Multi-stage Alpine Dockerfile
# - builder: builds a wheel for the project (includes build deps)
# - runtime: minimal Alpine image that installs the wheel only

FROM python:3.11-alpine AS builder

# Keep python output unbuffered and avoid writing .pyc files
ENV UV_LINK_MODE=copy
ENV UV_COMPILE_BYTECODE=1

WORKDIR /workspace

COPY . .

# Upgrade pip/setuptools/wheel and build a wheel into /dist
RUN python -m pip install uv \
    && uv build

#########################
## Runtime image (Alpine)
#########################
FROM python:3.11-alpine

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Runtime OS deps: ca-certificates so HTTPS works. Keep runtime minimal.
RUN apk add --no-cache ca-certificates

# Copy built wheel(s) from builder
COPY --from=builder /workspace/dist /dist

RUN python -m pip install --no-cache-dir /dist/*.whl

# Create a non-root user for runtime and ensure ownership
RUN adduser -D appuser \
    && chown -R appuser:appuser /app

USER appuser

# Use ENTRYPOINT so runtime args passed to `docker run` are forwarded to the console script
ENTRYPOINT ["external-secrets-reloader"]
