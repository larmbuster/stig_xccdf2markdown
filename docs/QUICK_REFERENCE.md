# Quick Reference

## 🚀 Installation

### Local
```bash
pip install -r requirements.txt
```

### Podman
```bash
podman build -f Containerfile -t stig-converter .
```

## 💻 Common Commands

### Test Runs
```bash
# Local - test with 10 pages
python stig_converter.py --test

# Podman - test mode
podman-compose up
```

### Full Conversion
```bash
# Local - all STIGs
python stig_converter.py

# Podman - all STIGs (rootless with SELinux support)
podman run --rm --userns=keep-id \
  -v $(pwd)/stig_downloads:/app/stig_downloads:Z \
  -v $(pwd)/stig_markdown_output:/app/stig_markdown_output:Z \
  stig-converter
```

### Process Existing Files
```bash
# Local
python stig_converter.py --process-only

# Podman
podman run --rm --userns=keep-id \
  -v $(pwd)/stig_downloads:/app/stig_downloads:Z \
  -v $(pwd)/stig_markdown_output:/app/stig_markdown_output:Z \
  stig-converter --process-only
```

## 📋 Command Line Options

| Option | Description |
|--------|-------------|
| `--test` | Quick test (10 pages) |
| `--max-pages N` | Limit to N pages |
| `--process-only` | Convert existing ZIPs |
| `--download-only` | Download without converting |
| `--skip-download` | Scrape links only |
| `--no-headless` | Show browser window |

## 🐳 Container Commands (Podman)

```bash
# Build
podman build -f Containerfile -t stig-converter .

# Run with podman-compose
podman-compose up

# Run with custom command
podman-compose run stig-converter --max-pages 5

# View logs
podman-compose logs -f
# Or for a specific container
podman logs <container-name>

# Clean up
podman-compose down
```

## 🔧 Environment Variables

```bash
# Set custom directories
STIG_DOWNLOAD_DIR=/custom/path python stig_converter.py

# Force headless mode
STIG_HEADLESS=true python stig_converter.py

# Container mode (auto-detected)
CONTAINER_ENV=true python stig_converter.py
```

## 📁 Directory Structure

```
stig_xccdf2markdown/
├── stig_converter.py        # Main script
├── xccdf_to_markdown.xsl    # XSLT transformation
├── requirements.txt         # Python dependencies
├── Containerfile           # Container definition
├── podman-compose.yml      # Podman Compose config
├── run_in_pipeline.sh      # CI/CD helper script
├── stig_downloads/         # Downloaded ZIPs
├── stig_markdown_output/   # Generated Markdown
└── docs/                   # Documentation
```

## 🚦 GitHub Actions

### Enable
```bash
# Already included - just push
git push
```

### Manual Trigger
1. Go to Actions tab
2. Select "STIG Converter Pipeline"
3. Click "Run workflow"
4. Choose mode and options
5. Click green "Run workflow"

### Check Results
- Go to workflow run
- Download artifacts
- Check step summary

## ⚡ Performance Tips

```bash
# Process in batches
python stig_converter.py --max-pages 20

# Download first, process later
python stig_converter.py --download-only
python stig_converter.py --process-only

# Increase container memory
podman run --memory="4g" --userns=keep-id \
  -v ./stig_downloads:/app/stig_downloads:Z \
  -v ./stig_markdown_output:/app/stig_markdown_output:Z \
  stig-converter
```

## 🆘 Quick Fixes

| Problem | Solution |
|---------|----------|
| Firefox not found | Install Firefox or use Podman container |
| No files found | Check cyber.mil manually |
| Permission denied | `chmod 755` directories |
| Out of memory | Use `--max-pages` or increase RAM |
| Container won't start | Check `podman info` |

## 📚 More Help
- [Troubleshooting Guide](TROUBLESHOOTING.md)
- [Container Usage](CONTAINER_USAGE.md)
- [CI/CD Integration](CI_CD_INTEGRATION.md)
