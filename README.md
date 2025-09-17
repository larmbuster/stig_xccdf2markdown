# STIG XCCDF to Markdown Converter

![AI Assisted Yes](https://img.shields.io/badge/AI%20Assisted-Yes-green?style=for-the-badge)

![Container Build](https://github.com/larmbuster/stig_xccdf2markdown/actions/workflows/build-container.yml/badge.svg?branch=main&event=push)
![STIG Converter](https://github.com/larmbuster/stig_xccdf2markdown/actions/workflows/stig-converter.yml/badge.svg?branch=main&event=workflow_dispatch)

A powerful tool that automatically downloads Security Technical Implementation Guides (STIGs) from cyber.mil and converts them into clean, readable Markdown format.

## 🚀 Quick Start

### Local Installation
```bash
# Clone the repository
git clone <repository-url>
cd stig_xccdf2markdown

# Install dependencies
pip install -r requirements.txt

# Run the converter
python stig_converter.py --test  # Test mode (10 pages)
python stig_converter.py          # Full conversion
```

### Using Podman

#### Option 1: Use Pre-built Image (Quickest)
```bash
# Make the required directories
mkdir stig_downloads stig_markdown_output

# Pull the latest image from GitHub Container Registry
# Images are automatically built on every commit to main
podman pull ghcr.io/larmbuster/stig_xccdf2markdown:latest

# Run the converter
podman run --rm --userns=keep-id \
  -v $(pwd)/stig_downloads:/app/stig_downloads:Z \
  -v $(pwd)/stig_markdown_output:/app/stig_markdown_output:Z \
  ghcr.io/larmbuster/stig_xccdf2markdown:latest --test
```

#### Option 2: Build Locally
```bash
# Make the required directories
mkdir stig_downloads stig_markdown_output

# Using Podman Compose
podman-compose up

# Or build and run directly
podman build -f Containerfile -t stig-converter .
podman run --rm --userns=keep-id \
  -v $(pwd)/stig_downloads:/app/stig_downloads:Z \
  -v $(pwd)/stig_markdown_output:/app/stig_markdown_output:Z \
  stig-converter --test
```

## 📦 Download Pre-built Results

Instead of running the converter yourself, you can download pre-built STIG Markdown files directly from the GitHub Actions workflow:

1. **Go to the [STIG Converter Pipeline](https://github.com/larmbuster/stig_xccdf2markdown/actions/workflows/stig-converter.yml)**
2. **Click on any completed "STIG Converter Pipeline" workflow run**
3. **Scroll down to the "Artifacts" section**
4. **Download the artifacts:**
   - `stig-markdown-{run_number}` - Contains all converted Markdown files (retained for 30 days)
   - `stig-downloads-{run_number}` - Contains the original ZIP files (retained for 7 days)

The workflow runs automatically every Sunday at 2 AM UTC.

## 📋 Prerequisites

- **Python 3.8+** (for local installation)
- **Firefox browser** (for local installation)
- **Podman** (for containerized deployment)

## 🎯 Features

- **Automated Web Scraping** - Navigates cyber.mil to find all STIG downloads
- **Batch Processing** - Downloads and converts multiple STIGs in one run
- **Multiple Modes** - Test, full, download-only, or process-only operations
- **Container Ready** - Podman support with rootless, secure operation
- **CI/CD Integration** - GitHub Actions workflow included
- **Cross-Platform** - Works on Windows, macOS, and Linux

## 💻 Usage

### Command Line Options

| Option | Description |
|--------|-------------|
| `--test` | Quick test mode (processes 10 pages) |
| `--max-pages N` | Limit to N pages |
| `--process-only` | Convert existing ZIP files without downloading |
| `--download-only` | Download files without converting |
| `--skip-download` | Scrape links but don't download (testing) |
| `--no-headless` | Show browser window (debugging) |

### Examples

```bash
# Test the system quickly
python stig_converter.py --test

# Process existing downloads
python stig_converter.py --process-only

# Download first 5 pages only
python stig_converter.py --max-pages 5

# Debug with visible browser
python stig_converter.py --test --no-headless
```

## 📁 Output Structure

```
stig_xccdf2markdown/
├── stig_downloads/          # Downloaded ZIP files
│   └── *.zip
└── stig_markdown_output/    # Converted Markdown files
    └── *.md
```

## 🐳 Container Deployment (Podman)

### GitHub Actions (CI/CD)
The repository includes a complete GitHub Actions workflow that runs automatically:
- **Weekly** - Sundays at 2 AM UTC
- **Manual** - Via Actions tab with configurable options
- **Results** - Stored as downloadable artifacts

### Local Container Usage
```bash
# Install Podman (if not already installed)
# macOS: brew install podman && podman machine init && podman machine start
# Linux: sudo apt install podman  # or dnf/yum
# Windows: Install Podman Desktop from podman.io

# Build and run
podman build -f Containerfile -t stig-converter .
podman run --rm --userns=keep-id \
  -v ./stig_downloads:/app/stig_downloads:Z \
  -v ./stig_markdown_output:/app/stig_markdown_output:Z \
  stig-converter --test
```

See [Container Usage Guide](docs/CONTAINER_USAGE.md) for detailed instructions.

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `STIG_BASE_URL` | STIG download URL | `https://www.cyber.mil/stigs/downloads/` |
| `STIG_DOWNLOAD_DIR` | Download directory | `stig_downloads` |
| `STIG_OUTPUT_DIR` | Output directory | `stig_markdown_output` |
| `CONTAINER_ENV` | Container mode flag | `false` (auto-detected) |

## 📚 Documentation

- [Project Overview](docs/PROJECT_OVERVIEW.md) - Detailed architecture and features
- [Quick Reference](docs/QUICK_REFERENCE.md) - Command cheat sheet
- [Container Usage Guide](docs/CONTAINER_USAGE.md) - Podman deployment details
- [Container Registry Guide](docs/CONTAINER_REGISTRY.md) - Using pre-built images
- [CI/CD Integration Guide](docs/CI_CD_INTEGRATION.md) - Pipeline integration
- [Troubleshooting Guide](docs/TROUBLESHOOTING.md) - Common issues and solutions

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This tool is not officially affiliated with or endorsed by the U.S. Department of War or cyber.mil. It is an independent tool created to help security professionals work with publicly available STIG content.
