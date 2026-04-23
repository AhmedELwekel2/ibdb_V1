FROM python:3.11-slim

# System deps for WeasyPrint / Cairo / Pango and fonts
# Added fonts-hosny-amiri for Arabic PDF support
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libcairo2 \
        libgdk-pixbuf-2.0-0 \
        libffi8 \
        libjpeg62-turbo \
        zlib1g \
        fonts-dejavu-core \
        fonts-liberation \
        fonts-hosny-amiri \
        libxml2-dev \
        libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Install Playwright browsers (chromium) for custom scrapers
RUN playwright install --with-deps chromium

# Optional: ensure NLTK data is available at build time
RUN python -c "import nltk; nltk.download('punkt')"

ENV PYTHONUNBUFFERED=1

CMD ["python", "telegram_bot_quality_arabic_claude_version.py"]