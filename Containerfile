# Containerfile for Podman
# Using RHEL UBI 9 with Python 3.11
FROM registry.access.redhat.com/ubi9/python-311:latest

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

# Install EPEL repository and system dependencies with version pinning in one layer
# Note: curl-minimal already present in base image
RUN dnf install -y \
    https://dl.fedoraproject.org/pub/epel/epel-release-latest-9.noarch.rpm \
    && dnf install -y \
    unzip-6.0-58.el9_5 \
    ca-certificates-2024.2.69_v8.0.303-91.4.el9_4 \
    tar-1.34-7.el9 \
    bzip2-1.0.8-10.el9_5 \
    # D-Bus libraries (Firefox needs these)
    dbus-1.12.20-8.el9 \
    dbus-glib-0.110-13.el9 \
    # Fonts (required for Firefox rendering)
    fontconfig-2.14.0-2.el9_1 \
    freetype-2.10.4-10.el9_5 \
    dejavu-sans-fonts-2.37-18.el9 \
    # X11 and graphics libraries
    gtk3-3.24.31-5.el9 \
    libXt-1.2.0-6.el9 \
    libX11-1.7.0-11.el9 \
    libX11-xcb-1.7.0-11.el9 \
    libXcomposite-0.4.5-7.el9 \
    libXcursor-1.2.0-7.el9 \
    libXdamage-1.1.5-7.el9 \
    libXfixes-5.0.3-16.el9 \
    libXi-1.7.10-8.el9 \
    libXrandr-1.5.2-8.el9 \
    libXrender-0.9.10-16.el9 \
    libXScrnSaver-1.2.3-10.el9 \
    libXtst-1.2.3-16.el9 \
    libXext-1.3.4-8.el9 \
    # Crypto and security
    nss-3.112.0-4.el9_4 \
    nspr-4.36.0-4.el9_4 \
    # Audio libraries
    alsa-lib-1.2.13-2.el9 \
    # Accessibility
    at-spi2-atk-2.38.0-4.el9 \
    at-spi2-core-2.40.3-1.el9 \
    # Graphics and rendering
    cups-libs-2.3.3op2-33.el9_6.1 \
    libdrm-2.4.123-2.el9 \
    mesa-libgbm-24.2.8-3.el9_6 \
    mesa-libGL-24.2.8-3.el9_6 \
    pango-1.48.7-3.el9 \
    cairo-1.17.4-7.el9 \
    libxkbcommon-1.0.3-4.el9 \
    && dnf clean all \
    && rm -rf /var/cache/dnf

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
# Ensure modern pip and install Python dependencies
RUN python -m pip install --upgrade --no-cache-dir pip \
    && pip install --no-cache-dir -r requirements.txt

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
ENTRYPOINT ["python", "stig_converter.py"]
CMD []
