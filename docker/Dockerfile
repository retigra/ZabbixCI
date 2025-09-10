FROM ghcr.io/astral-sh/uv:python3.12-trixie-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /app

RUN apt update && apt install -y git && apt-get clean

COPY pyproject.toml /app
COPY uv.lock /app/uv.lock
COPY .git /app/.git
RUN mkdir /app/zabbixci

RUN uv sync --locked --no-install-project --no-dev

COPY . /app

RUN uv sync --locked --no-dev

FROM python:3.12-slim-trixie

LABEL org.opencontainers.image.source=https://github.com/retigra/ZabbixCI
LABEL org.opencontainers.image.title="ZabbixCI"
LABEL org.opencontainers.image.description="Source control for Zabbix templates in Git"
LABEL org.opencontainers.image.documentation=https://github.com/retigra/ZabbixCI/tree/main/docs
LABEL org.opencontainers.image.licenses=AGPL
LABEL org.opencontainers.image.vendor="Retigra"
LABEL org.opencontainers.image.authors="info@retigra.nl"

RUN apt-get update && apt-get install -y imagemagick && apt-get clean

COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --from=builder --chown=app:app /app/zabbixci /app/zabbixci

ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT [ "zabbixci" ]
