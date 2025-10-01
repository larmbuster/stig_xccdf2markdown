# Container Usage Guide

This guide explains how to run the STIG converter in Podman containers, ideal for CI/CD pipelines and consistent deployments. Podman provides a secure, rootless container runtime.

## 🚀 Quick Start

### Pre-built Images

Pre-built container images are automatically published to GitHub Container Registry:

```bash
# Pull the latest image
podman pull ghcr.io/larmbuster/stig_xccdf2markdown:latest

# Run with the pre-built image
podman run --rm --userns=keep-id \
  -v $(pwd)/stig_downloads:/app/stig_downloads:Z \
  -v $(pwd)/stig_markdown_output:/app/stig_markdown_output:Z \
  ghcr.io/larmbuster/stig_xccdf2markdown:latest --test
```

Available tags:
- `latest` - Latest stable build from main branch
- `sha-XXXXXXX` - Specific commit builds
- `v1.0.0` - Version tags (when released)
- `pr-123` - Pull request builds (for testing)

### Installing Podman
```bash
# macOS
brew install podman
podman machine init
podman machine start

# RHEL/Fedora/CentOS
sudo dnf install podman

# Ubuntu/Debian
sudo apt-get update
sudo apt-get install podman

# Windows
# Download and install Podman Desktop from podman.io
```

### Using Podman Compose (Easiest)
```bash
# Install podman-compose if needed
pip install podman-compose

# Test mode (default)
podman-compose up

# Full conversion
podman-compose run stig-converter

# Process existing files only
podman-compose run stig-converter --process-only
```

### Using Podman Directly
```bash
# Build the image from Containerfile
podman build -f Containerfile -t stig-converter .

# Run in test mode (rootless with SELinux labels)
podman run --rm \
  --userns=keep-id \
  -v $(pwd)/stig_downloads:/app/stig_downloads:Z \
  -v $(pwd)/stig_markdown_output:/app/stig_markdown_output:Z \
  stig-converter --test

# Full conversion
podman run --rm \
  --userns=keep-id \
  -v $(pwd)/stig_downloads:/app/stig_downloads:Z \
  -v $(pwd)/stig_markdown_output:/app/stig_markdown_output:Z \
  stig-converter
```

### Using the Pipeline Script
```bash
# Various modes
./run_in_pipeline.sh --mode test
./run_in_pipeline.sh --mode full
./run_in_pipeline.sh --mode process-only
./run_in_pipeline.sh --mode download-only
./run_in_pipeline.sh --mode full --max-pages 20
```

## 📦 Container Architecture

### Base Image
- **RHEL UBI 9 with Python 3.11** - Enterprise-grade base image
- **Firefox 134.0** - Direct from Mozilla (not in UBI repos)
- **Geckodriver v0.36.0** - Pre-installed WebDriver

### Security Features
- **Rootless by default** - Podman runs without root privileges
- **User namespace isolation** - Enhanced security with `--userns=keep-id`
- **SELinux support** - Automatic labeling with `:Z` flag
- **No daemon required** - No privileged daemon needed
- **Read-only mounts** for configuration
- **Resource limits** configurable
- **No new privileges** flag enforced

### Environment Variables
| Variable | Description | Container Default |
|----------|-------------|-------------------|
| `CONTAINER_ENV` | Container mode flag | `true` |
| `STIG_HEADLESS` | Headless browser mode | `true` |
| `MOZ_HEADLESS` | Mozilla headless flag | `1` |
| `STIG_DOWNLOAD_DIR` | Download directory | `/app/stig_downloads` |
| `STIG_OUTPUT_DIR` | Output directory | `/app/stig_markdown_output` |

## 🔄 Volume Mounts

Required volumes:
- `/app/stig_downloads` - Downloaded ZIP files (persistent)
- `/app/stig_markdown_output` - Generated Markdown files (persistent)

Optional:
- `/app/xccdf_to_markdown.xsl` - Custom XSLT file (read-only)

## 💾 Resource Requirements

### Minimum
- CPU: 1 core
- Memory: 1GB RAM
- Disk: 2GB free space

### Recommended
- CPU: 2+ cores
- Memory: 2GB+ RAM
- Disk: 10GB+ free space

## 🔧 Podman Compose Configuration

The included `podman-compose.yml` provides:
- **Rootless operation** - Enhanced security by default
- **SELinux compatibility** - Proper volume labeling with `:Z`
- **User namespace mapping** - `userns_mode: "keep-id"`
- **Resource limits** - 2 CPU, 2GB RAM
- **Security settings** - No new privileges
- **Volume persistence** - With proper permissions
- **Network isolation** - Bridge network
- **Test mode by default** - Change `command:` for other modes

To modify the default mode, edit `podman-compose.yml`:
```yaml
command: ["--test"]  # Change to [] for full mode
```

## 🐛 Troubleshooting

### Container Won't Start
- Check Podman installation: `podman info`
- For macOS, ensure machine is running: `podman machine start`
- Verify disk space: `df -h`
- Check permissions on mounted volumes
- SELinux issues: Use `:Z` flag on volumes

### Browser Crashes
- Increase memory limits in podman-compose.yml
- Ensure at least 1GB RAM available
- Container automatically applies `--no-sandbox` flag

### No Files Downloaded
- Check network connectivity
- Verify cyber.mil is accessible
- Try `--test` mode first

### Permission Errors
- Podman rootless handles permissions automatically with `--userns=keep-id`
- SELinux systems: Ensure `:Z` flag is used on volume mounts
- Linux: `chmod 755 stig_downloads stig_markdown_output`
- If issues persist: `podman unshare chown -R 1000:1000 ./stig_*`

### Out of Memory
- Increase Podman memory limits: `--memory=4g`
- For podman-compose, edit the memory limits in yaml
- Use `--max-pages` to limit scope
- Process in batches with `--process-only`

## 🎯 Best Practices

1. **Start with test mode** to verify setup
2. **Use volumes** with `:Z` flag for SELinux systems
3. **Set resource limits** appropriate for your system
4. **Monitor logs** with `podman-compose logs -f` or `podman logs`
5. **Cache downloads** by preserving the downloads volume
6. **Process incrementally** for large datasets

## 📊 Performance Tips

### For Large-Scale Processing
```bash
# Download first, then process
./run_in_pipeline.sh --mode download-only
./run_in_pipeline.sh --mode process-only

# Process in chunks
./run_in_pipeline.sh --mode full --max-pages 20

# Increase resources
podman-compose up
```

### Resource Optimization
Edit `podman-compose.yml`:
```yaml
deploy:
  resources:
    limits:
      cpus: '4'
      memory: 4G
```

Or use command line:
```bash
podman run --memory=4g --cpus=4 stig-converter
```


## 🔗 Related Documentation
- [Main README](../README.md)
- [CI/CD Integration](CI_CD_INTEGRATION.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)
