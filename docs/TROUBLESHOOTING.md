# Troubleshooting Guide

Common issues and solutions for the STIG XCCDF to Markdown Converter.

## 🔍 Quick Diagnostics

### Check System Requirements
```bash
# Python version (need 3.8+)
python --version

# Firefox installation
firefox --version

# Podman installation
podman --version
podman info

# Disk space
df -h
```

## 🚨 Common Issues

### Installation Issues

#### "Firefox binary not found"
**Symptoms:** Error message about missing Firefox

**Solutions:**
- **macOS:** Install Firefox at `/Applications/Firefox.app`
  ```bash
  brew install --cask firefox
  ```
- **Linux:** Install via package manager
  ```bash
  # Ubuntu/Debian
  sudo apt install firefox
  
  # Fedora
  sudo dnf install firefox
  ```
- **Windows:** Download from [Mozilla Firefox](https://www.mozilla.org/firefox/)

#### "Module not found" errors
**Symptoms:** Python import errors

**Solution:**
```bash
pip install -r requirements.txt
# Or for Python 3
pip3 install -r requirements.txt
```

### Runtime Issues

#### Browser Won't Start / Hangs

**Symptoms:** Script hangs at "Starting Firefox browser..."

**Solutions:**
1. Try visible mode to see what's happening:
   ```bash
   python stig_converter.py --test --no-headless
   ```

2. Check Firefox permissions (macOS):
   - Open Firefox manually once
   - Accept any security prompts

3. Use Podman instead (avoids browser issues):
   ```bash
   podman-compose up
   # Or direct run
   podman run --rm --userns=keep-id \
     -v ./stig_downloads:/app/stig_downloads:Z \
     -v ./stig_markdown_output:/app/stig_markdown_output:Z \
     stig-converter --test
   ```

#### No STIG Files Found

**Symptoms:** "No STIG files to process" message

**Possible Causes:**
- cyber.mil is temporarily unavailable
- Site structure has changed
- Network connectivity issues

**Solutions:**
1. Check site manually: https://www.cyber.mil/stigs/downloads/
2. Verify network connection
3. Try with fewer pages:
   ```bash
   python stig_converter.py --max-pages 1
   ```
4. Check for site changes in download button structure

#### SSL/Certificate Warnings

**Symptoms:** SSL verification errors

**Solution:** These are typically harmless. The script handles them automatically with `verify=False` for requests.

### Container Issues

#### Container Fails to Start

**Symptoms:** Podman container exits immediately

**Solutions:**
1. Check Podman:
   ```bash
   podman info
   ```
   
   For Podman on macOS:
   ```bash
   podman machine start
   ```

2. Rebuild image:
   ```bash
   podman build --no-cache -f Containerfile -t stig-converter .
   ```

3. Check logs:
   ```bash
   podman logs <container-id>
   ```

#### Permission Denied in Container

**Symptoms:** Cannot write to output directories

**Solutions:**
1. Set correct permissions:
   ```bash
   chmod 755 stig_downloads stig_markdown_output
   ```

2. For CI/CD, ensure directories are created with proper permissions:
   ```bash
   mkdir -p stig_downloads stig_markdown_output
   chmod 777 stig_downloads stig_markdown_output  # For CI/CD only
   ```

#### Out of Memory Errors

**Symptoms:** Container killed or browser crashes

**Solutions:**
1. Increase container memory:
   - Podman: Use `--memory=4g` flag
   - podman-compose.yml: Adjust limits
     ```yaml
     deploy:
       resources:
         limits:
           memory: 4G
     ```

2. Process in smaller batches:
   ```bash
   podman run --rm --userns=keep-id \
     -v ./stig_downloads:/app/stig_downloads:Z \
     -v ./stig_markdown_output:/app/stig_markdown_output:Z \
     stig-converter --max-pages 10
   ```

### Download Issues

#### Downloads Fail or Timeout

**Symptoms:** "Failed to download" messages

**Solutions:**
1. Check cyber.mil accessibility
2. Increase timeout in code (if needed)
3. Try downloading fewer files:
   ```bash
   python stig_converter.py --max-pages 1
   ```

#### "Already exists" for All Files

**Symptoms:** Skipping all downloads

**Solution:** Clear download directory or use `--process-only`:
```bash
rm -rf stig_downloads/*.zip
# Or
python stig_converter.py --process-only
```

### Processing Issues

#### XML Parsing Errors

**Symptoms:** "Could not parse XML file" errors

**Possible Causes:**
- Corrupted ZIP file
- Non-XCCDF XML file
- Invalid XML structure

**Solutions:**
1. Re-download the file
2. Check ZIP file integrity:
   ```bash
   unzip -t stig_downloads/filename.zip
   ```

#### No Markdown Files Generated

**Symptoms:** Downloads succeed but no .md files created

**Solutions:**
1. Check XSLT file exists:
   ```bash
   ls xccdf_to_markdown.xsl
   ```

2. Process existing files:
   ```bash
   python stig_converter.py --process-only
   ```

3. Check for XML files in ZIPs:
   ```bash
   unzip -l stig_downloads/*.zip | grep .xml
   ```

## 🔧 Platform-Specific Issues

### macOS

#### "Operation not permitted" errors
- Grant Terminal/IDE full disk access in System Preferences → Security & Privacy

#### Firefox won't start in automation
- Open Firefox manually once and accept security prompts
- Check Gatekeeper settings

### Windows

#### Path/Encoding Issues
- Use PowerShell instead of Command Prompt
- Run as Administrator if needed
- Script automatically handles UTF-8 encoding

#### Firefox Not Found
- Check installation paths:
  - `C:\Program Files\Mozilla Firefox\`
  - `C:\Program Files (x86)\Mozilla Firefox\`

### Linux

#### Display Issues in Containers
- Headless mode is enforced in containers
- No X11 display needed

#### SELinux Denials (RHEL/Fedora)
```bash
# Temporary fix
setenforce 0

# Or add SELinux context
chcon -R -t container_file_t stig_downloads stig_markdown_output
```

## 🐛 Debug Mode

### Enable Verbose Output

**Local:**
```bash
python stig_converter.py --verbose --test
```

**Container (Podman):**
```bash
podman run --rm --userns=keep-id \
  -e DEBUG=true \
  -v $(pwd)/stig_downloads:/app/stig_downloads:Z \
  -v $(pwd)/stig_markdown_output:/app/stig_markdown_output:Z \
  stig-converter --test
```


### Check Intermediate Steps

1. **Test scraping only:**
   ```bash
   python stig_converter.py --test --skip-download
   ```

2. **Test downloading only:**
   ```bash
   python stig_converter.py --max-pages 1 --download-only
   ```

3. **Test processing only:**
   ```bash
   python stig_converter.py --process-only
   ```

## 📊 Performance Issues

### Slow Scraping
- Normal: ~3-5 seconds per page
- Use `--max-pages` to limit scope
- Container mode may be slightly slower

### High Memory Usage
- Each page load uses ~200-500MB
- Processing large XML files needs additional memory
- Solutions:
  - Process in batches
  - Increase system/container memory
  - Use `--download-only` then `--process-only`

### Disk Space Issues
- Each STIG ZIP: 1-10MB
- Extracted XMLs: 2-20MB each
- Check available space: `df -h`
- Clean old downloads: `rm -rf stig_downloads/*.zip`

## 💡 Getting Help

### Diagnostic Information to Collect

When reporting issues, include:

1. **System info:**
   ```bash
   python --version
   firefox --version
   podman --version
   uname -a
   ```

2. **Error messages:** Full error output

3. **Mode used:** Command line arguments

4. **Logs:** 
   - Console output
   - Docker logs if using containers

### Log Locations

- **Local:** Console output
- **Podman:** `podman logs <container-name>`
- **CI/CD:** Check pipeline logs
- **Custom:** Set via `LOG_FILE` environment variable

## 🔗 Related Documentation
- [Main README](../README.md)
- [Container Usage](CONTAINER_USAGE.md)
- [CI/CD Integration](CI_CD_INTEGRATION.md)
