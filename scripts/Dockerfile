FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y wget unzip curl && \
    pip install pandas pymysql requests

# Copy scripts
COPY . /app

# Default command
CMD ["python3", "pipeline_local.py"]
