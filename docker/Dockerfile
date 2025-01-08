FROM python:slim

# Set the working directory
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY pyproject.toml /app
COPY zabbixci /app/zabbixci

# Install any needed packages specified in requirements.txt
RUN pip install /app/