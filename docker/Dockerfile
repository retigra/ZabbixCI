FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

RUN apt-get update && apt-get install -y git && apt-get clean

WORKDIR /app

# Install dependencies before copying source for better layer caching
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Copy source and .git for setuptools_scm version resolution
COPY pyproject.toml /app/
COPY zabbixci /app/zabbixci
COPY .git /app/.git

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-dev


FROM python:3.13-slim

LABEL org.opencontainers.image.source=https://github.com/retigra/ZabbixCI
LABEL org.opencontainers.image.title="ZabbixCI"
LABEL org.opencontainers.image.description="Source control for Zabbix templates in Git"
LABEL org.opencontainers.image.documentation=https://github.com/retigra/ZabbixCI/tree/main/docs
LABEL org.opencontainers.image.licenses=AGPL
LABEL org.opencontainers.image.vendor="Retigra"
LABEL org.opencontainers.image.authors="info@retigra.nl"

RUN apt-get update && apt-get install -y git imagemagick && apt-get clean

COPY --from=builder /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT ["zabbixci"]
