# Containerfile for Podman
# Using RHEL UBI 9 with Python 3.11
FROM registry.access.redhat.com/ubi9-minimal:latest

# Metadata labels
LABEL org.opencontainers.image.title="STIG XCCDF to Markdown Converter" \
      org.opencontainers.image.description="Automatically downloads STIGs from cyber.mil and converts them to Markdown format" \
      org.opencontainers.image.source="https://github.com/larmbuster/stig_xccdf2markdown" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.base.name="registry.access.redhat.com/ubi9/python-311"

# Build arguments for version control
ARG FIREFOX_VERSION=134.0
ARG GECKODRIVER_VERSION=v0.36.0

# Switch to root for system package installation
USER 0

# Install runtime dependencies with microdnf (minimal set required for headless Firefox and Python)
RUN microdnf update -y \
    && microdnf install -y \
       python3.11 python3.11-pip \
       ca-certificates tar bzip2 unzip \
       dbus dbus-glib \
       fontconfig freetype dejavu-sans-fonts \
       gtk3 libXt libX11 libX11-xcb libXcomposite libXcursor libXdamage libXfixes libXi libXrandr libXrender libXScrnSaver libXtst libXext \
       nss nspr \
       alsa-lib \
       at-spi2-atk at-spi2-core \
       cups-libs libdrm mesa-libgbm mesa-libGL pango cairo libxkbcommon \
    && microdnf clean all \
    && rm -rf /var/cache/yum /var/cache/dnf

# Create a dummy machine-id (Firefox checks for it)
RUN echo "00000000000000000000000000000000" > /etc/machine-id || true

# Install Firefox from Mozilla (not available in UBI repos)
RUN curl -L -o /tmp/firefox.tar.bz2 \
    "https://ftp.mozilla.org/pub/firefox/releases/${FIREFOX_VERSION}/linux-x86_64/en-US/firefox-${FIREFOX_VERSION}.tar.bz2" \
    && tar -xjf /tmp/firefox.tar.bz2 -C /opt/ \
    && ln -s /opt/firefox/firefox /usr/local/bin/firefox \
    && rm /tmp/firefox.tar.bz2

# Install geckodriver
RUN curl -L -o /tmp/geckodriver.tar.gz \
    "https://github.com/mozilla/geckodriver/releases/download/${GECKODRIVER_VERSION}/geckodriver-${GECKODRIVER_VERSION}-linux64.tar.gz" \
    && tar -xzf /tmp/geckodriver.tar.gz -C /usr/local/bin/ \
    && chmod +x /usr/local/bin/geckodriver \
    && rm /tmp/geckodriver.tar.gz

# Set working directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .
# Ensure modern pip and install Python dependencies for Python 3.11
RUN python3.11 -m pip install --upgrade --no-cache-dir pip \
    && pip3.11 install --no-cache-dir -r requirements.txt

# Copy application files
COPY stig_converter.py .
COPY xccdf_to_markdown.xsl .

# Create non-root user and set up directories in one layer
RUN useradd -m -u 1000 stig_user \
    && mkdir -p /app/stig_downloads /app/stig_markdown_output \
    && mkdir -p /home/stig_user/.cache/fontconfig \
                /home/stig_user/.cache/dconf \
                /home/stig_user/.cache/mozilla \
    && chown -R stig_user:stig_user /app /home/stig_user/.cache

# Set environment variables for container operation
ENV PYTHONUNBUFFERED=1 \
    STIG_HEADLESS=true \
    DISPLAY=:99 \
    MOZ_HEADLESS=1 \
    CONTAINER_ENV=true \
    STIG_DOWNLOAD_DIR=/app/stig_downloads \
    STIG_OUTPUT_DIR=/app/stig_markdown_output \
    STIG_XSLT_FILE=/app/xccdf_to_markdown.xsl \
    HOME=/home/stig_user

USER stig_user

# Default command - can be overridden
ENTRYPOINT ["python3.11", "stig_converter.py"]
CMD []
