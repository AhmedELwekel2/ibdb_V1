FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (for WeasyPrint/ReportLab if used by the bot)
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    fontconfig \
    libxml2 \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the quality_bot code since the backend imports from it
COPY quality_bot /app/quality_bot

# Copy the backend code
COPY quality_platform/backend /app/quality_platform/backend

# Install python packages.
RUN if [ -f /app/quality_bot/requirements.txt ]; then pip install --no-cache-dir -r /app/quality_bot/requirements.txt; fi
RUN pip install --no-cache-dir -r /app/quality_platform/backend/requirements.txt

WORKDIR /app/quality_platform/backend

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
