FROM python:slim

LABEL org.opencontainers.image.source=https://github.com/retigra/ZabbixCI
LABEL org.opencontainers.image.title="ZabbixCI"
LABEL org.opencontainers.image.description="Source control for Zabbix templates in Git"
LABEL org.opencontainers.image.documentation=https://github.com/retigra/ZabbixCI/tree/main/docs
LABEL org.opencontainers.image.licenses=AGPL
LABEL org.opencontainers.image.vendor="Retigra"
LABEL org.opencontainers.image.authors="info@retigra.nl"

RUN apt-get update && apt-get install -y git

# Set the working directory
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY pyproject.toml /app
COPY requirements.txt /app
COPY .git /app/.git
COPY zabbixci /app/zabbixci

# Install any needed packages specified in requirements.txt
RUN pip install /app/
RUN pip install -r /app/requirements.txt

ENTRYPOINT [ "zabbixci" ]
