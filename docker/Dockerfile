FROM python:slim

RUN apt-get update && apt-get install -y git

# Set the working directory
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY pyproject.toml /app
COPY .git /app/.git
COPY zabbixci /app/zabbixci

# Install any needed packages specified in requirements.txt
RUN pip install /app/