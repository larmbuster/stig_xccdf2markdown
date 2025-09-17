# Containerfile for Podman
# Multi-stage build for efficiency
FROM python:3.11-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg \
    unzip \
    ca-certificates \
    # Required for Firefox
    firefox-esr \
    # Required for geckodriver
    libgtk-3-0 \
    libdbus-glib-1-2 \
    libxt6 \
    libx11-xcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    libnss3 \
    libnspr4 \
    libasound2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libgbm1 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libxkbcommon0 \
    # Clean up
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install geckodriver
RUN GECKODRIVER_VERSION=$(curl -s https://api.github.com/repos/mozilla/geckodriver/releases/latest | python3 -c "import sys, json; print(json.load(sys.stdin)['tag_name'])") && \
    wget -q "https://github.com/mozilla/geckodriver/releases/download/${GECKODRIVER_VERSION}/geckodriver-${GECKODRIVER_VERSION}-linux64.tar.gz" && \
    tar -xzf geckodriver-*.tar.gz && \
    mv geckodriver /usr/local/bin/ && \
    rm geckodriver-*.tar.gz && \
    chmod +x /usr/local/bin/geckodriver

# Set working directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY stig_converter.py .
COPY xccdf_to_markdown.xsl .

# Create a non-root user for security
RUN useradd -m -u 1000 stig_user

# Create directories that the script expects and set proper ownership
RUN mkdir -p /app/stig_downloads /app/stig_markdown_output && \
    chown -R stig_user:stig_user /app

# Set environment variables for container operation
ENV PYTHONUNBUFFERED=1
ENV STIG_HEADLESS=true
ENV DISPLAY=:99
ENV MOZ_HEADLESS=1
ENV CONTAINER_ENV=true
# Set container-specific paths (script will use these via env vars)
ENV STIG_DOWNLOAD_DIR=/app/stig_downloads
ENV STIG_OUTPUT_DIR=/app/stig_markdown_output
ENV STIG_XSLT_FILE=/app/xccdf_to_markdown.xsl

USER stig_user

# Default command - can be overridden
# Empty CMD means run the script without arguments (full mode)
ENTRYPOINT ["python", "stig_converter.py"]
CMD []