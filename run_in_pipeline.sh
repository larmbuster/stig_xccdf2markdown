#!/bin/bash

# STIG Converter Pipeline Script
# This script is designed to run the STIG converter in a CI/CD pipeline
# It handles Podman container execution with proper error handling and logging

set -e  # Exit on error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="${OUTPUT_DIR:-$SCRIPT_DIR/stig_markdown_output}"
DOWNLOAD_DIR="${DOWNLOAD_DIR:-$SCRIPT_DIR/stig_downloads}"
LOG_FILE="${LOG_FILE:-$SCRIPT_DIR/stig_converter.log}"
MAX_PAGES="${MAX_PAGES:-}"  # Empty means process all pages
MODE="${MODE:-full}"  # Options: full, test, process-only, download-only

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check for Podman
    if ! command -v podman &> /dev/null; then
        error "Podman is not installed. Please install Podman first."
    fi
    
    if ! podman info &> /dev/null; then
        error "Podman is not running properly. Please check your installation."
        error "On macOS, you may need to run: podman machine start"
    fi
    
    log "Prerequisites check passed."
}

# Build container image
build_image() {
    log "Building container image with Podman..."
    
    cd "$SCRIPT_DIR"
    
    if [ ! -f "Containerfile" ]; then
        error "Containerfile not found in $SCRIPT_DIR"
    fi
    
    if podman build -f Containerfile -t stig-converter:latest . >> "$LOG_FILE" 2>&1; then
        log "Container image built successfully."
    else
        error "Failed to build container image. Check $LOG_FILE for details."
    fi
}

# Prepare directories
prepare_directories() {
    log "Preparing directories..."
    
    mkdir -p "$OUTPUT_DIR"
    mkdir -p "$DOWNLOAD_DIR"
    
    # Set permissions for container user (UID 1000)
    if [[ "$OSTYPE" != "msys" && "$OSTYPE" != "win32" ]]; then
        chmod 755 "$OUTPUT_DIR" "$DOWNLOAD_DIR"
    fi
    
    log "Directories prepared: $OUTPUT_DIR, $DOWNLOAD_DIR"
}

# Run the converter
run_converter() {
    local cmd_args=""
    
    case "$MODE" in
        test)
            cmd_args="--test"
            log "Running in TEST mode (limited to 10 pages)..."
            ;;
        process-only)
            cmd_args="--process-only"
            log "Running in PROCESS-ONLY mode..."
            ;;
        download-only)
            cmd_args="--download-only"
            log "Running in DOWNLOAD-ONLY mode..."
            ;;
        full)
            if [ -n "$MAX_PAGES" ]; then
                cmd_args="--max-pages $MAX_PAGES"
                log "Running in FULL mode with max $MAX_PAGES pages..."
            else
                cmd_args=""
                log "Running in FULL mode (all pages)..."
            fi
            ;;
        *)
            error "Unknown mode: $MODE"
            ;;
    esac
    
    log "Starting STIG converter container with Podman..."
    
    # Run the container with Podman
    # Note: $cmd_args is intentionally unquoted to allow multiple arguments
    # :Z adds SELinux context for volume mounts
    podman run \
        --rm \
        --name stig-converter-pipeline \
        -v "$DOWNLOAD_DIR:/app/stig_downloads:Z" \
        -v "$OUTPUT_DIR:/app/stig_markdown_output:Z" \
        -v "$SCRIPT_DIR/xccdf_to_markdown.xsl:/app/xccdf_to_markdown.xsl:ro,Z" \
        -e CONTAINER_ENV=true \
        -e STIG_HEADLESS=true \
        -e MOZ_HEADLESS=1 \
        --security-opt no-new-privileges \
        --userns=keep-id \
        stig-converter:latest \
        $cmd_args 2>&1 | tee -a "$LOG_FILE"
    
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        log "STIG converter completed successfully."
    else
        error "STIG converter failed. Check $LOG_FILE for details."
    fi
}

# Verify results
verify_results() {
    log "Verifying results..."
    
    local md_count=$(find "$OUTPUT_DIR" -name "*.md" -type f 2>/dev/null | wc -l)
    local zip_count=$(find "$DOWNLOAD_DIR" -name "*.zip" -type f 2>/dev/null | wc -l)
    
    log "Found $md_count Markdown files in output directory"
    log "Found $zip_count ZIP files in download directory"
    
    if [[ "$MODE" != "download-only" && $md_count -eq 0 ]]; then
        warning "No Markdown files were generated."
    fi
    
    if [[ "$MODE" != "process-only" && $zip_count -eq 0 ]]; then
        warning "No ZIP files were downloaded."
    fi
}

# Cleanup function
cleanup() {
    log "Cleaning up..."
    
    # Stop and remove container if it's still running
    podman stop stig-converter-pipeline 2>/dev/null || true
    podman rm stig-converter-pipeline 2>/dev/null || true
    
    log "Cleanup completed."
}

# Main execution
main() {
    log "=== STIG Converter Pipeline Script ==="
    log "Mode: $MODE"
    log "Output directory: $OUTPUT_DIR"
    log "Download directory: $DOWNLOAD_DIR"
    
    # Set trap for cleanup on exit
    trap cleanup EXIT
    
    # Execute pipeline steps
    check_prerequisites
    build_image
    prepare_directories
    run_converter
    verify_results
    
    log "=== Pipeline completed successfully ==="
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --mode)
            MODE="$2"
            shift 2
            ;;
        --max-pages)
            MAX_PAGES="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --download-dir)
            DOWNLOAD_DIR="$2"
            shift 2
            ;;
        --log-file)
            LOG_FILE="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --mode MODE           Set mode: full, test, process-only, download-only (default: full)"
            echo "  --max-pages N         Limit to N pages (only for full mode)"
            echo "  --output-dir DIR      Set output directory for Markdown files"
            echo "  --download-dir DIR    Set download directory for ZIP files"
            echo "  --log-file FILE       Set log file path"
            echo "  --help                Show this help message"
            echo ""
            echo "Environment variables:"
            echo "  MODE                  Same as --mode"
            echo "  MAX_PAGES            Same as --max-pages"
            echo "  OUTPUT_DIR           Same as --output-dir"
            echo "  DOWNLOAD_DIR         Same as --download-dir"
            echo "  LOG_FILE             Same as --log-file"
            exit 0
            ;;
        *)
            error "Unknown option: $1. Use --help for usage information."
            ;;
    esac
done

# Run main function
main
