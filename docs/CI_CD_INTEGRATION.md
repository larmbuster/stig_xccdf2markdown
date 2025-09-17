# CI/CD Integration Guide

Complete guide for integrating the STIG converter into CI/CD pipelines using Podman.

## ✅ GitHub Actions (Included)

The repository includes a complete GitHub Actions workflow (`.github/workflows/stig-converter.yml`).

### Quick Setup
```bash
# Already included - just push to enable
git push
```

### Features
- **Multiple Triggers**
  - Manual dispatch with parameters
  - Weekly schedule (Sundays 2 AM UTC)
  - Optional push triggers
  
- **Configurable Modes**
  - `test` - Quick 10-page test
  - `full` - Complete conversion
  - `process-only` - Convert existing ZIPs
  - `download-only` - Download without converting

- **Artifact Storage**
  - Markdown files: 30 days retention
  - ZIP files: 7 days retention
  - No repository commits (clean history)

### Manual Trigger
1. Go to **Actions** tab in GitHub
2. Select **"STIG Converter Pipeline"**
3. Click **"Run workflow"**
4. Choose options:
   - Mode: test/full/process-only/download-only
   - Max pages: (optional limit)
5. Click **"Run workflow"**

### Scheduled Runs
Automatically runs weekly. To modify schedule, edit `.github/workflows/stig-converter.yml`:
```yaml
schedule:
  - cron: '0 2 * * 0'  # Sundays at 2 AM UTC
```

## 🔧 Jenkins Integration

### Pipeline Script Example
```groovy
pipeline {
    agent any
    
    environment {
        MODE = 'full'
        MAX_PAGES = ''  // Empty for all
    }
    
    stages {
        stage('Build') {
            steps {
                sh 'podman build -f Containerfile -t stig-converter .'
            }
        }
        
        stage('Convert') {
            steps {
                sh './run_in_pipeline.sh --mode ${MODE}'
            }
        }
        
        stage('Archive') {
            steps {
                archiveArtifacts artifacts: 'stig_markdown_output/**/*.md'
                archiveArtifacts artifacts: 'stig_downloads/**/*.zip'
            }
        }
    }
    
    post {
        always {
            cleanWs()
        }
    }
}
```

### Freestyle Job
```bash
#!/bin/bash
# Build container image with Podman
podman build -f Containerfile -t stig-converter .

# Run converter
./run_in_pipeline.sh --mode full

# Archive results (configure in Jenkins UI)
```

## 🔧 GitLab CI Integration

### `.gitlab-ci.yml` Example
```yaml
stages:
  - build
  - convert
  - archive

variables:
  MODE: "test"

before_script:
  - apt-get update && apt-get -y install podman

build:
  stage: build
  script:
    - podman build -f Containerfile -t stig-converter .
  tags:
    - linux

convert:
  stage: convert
  script:
    - ./run_in_pipeline.sh --mode ${MODE}
  artifacts:
    paths:
      - stig_markdown_output/
      - stig_downloads/
    expire_in: 1 week
  tags:
    - linux

scheduled-full:
  extends: convert
  variables:
    MODE: "full"
  only:
    - schedules
```

## 🔧 Azure DevOps Integration

### `azure-pipelines.yml` Example
```yaml
trigger:
- main

schedules:
- cron: "0 2 * * 0"
  displayName: Weekly STIG conversion
  branches:
    include:
    - main

pool:
  vmImage: 'ubuntu-latest'

variables:
  mode: 'test'

steps:
- script: |
    sudo apt-get update
    sudo apt-get -y install podman
  displayName: 'Install Podman'

- script: |
    podman build -f Containerfile -t stig-converter .
  displayName: 'Build container image with Podman'

- script: |
    podman run --rm --userns=keep-id \
      -v $(Build.SourcesDirectory)/stig_downloads:/app/stig_downloads:Z \
      -v $(Build.SourcesDirectory)/stig_markdown_output:/app/stig_markdown_output:Z \
      stig-converter --$(mode)
  displayName: 'Run STIG Converter'

- task: PublishBuildArtifacts@1
  inputs:
    pathToPublish: 'stig_markdown_output'
    artifactName: 'stig-markdown'
```

## 🔧 CircleCI Integration

### `.circleci/config.yml` Example
```yaml
version: 2.1

executors:
  podman-executor:
    docker:
      - image: cimg/base:stable

jobs:
  convert:
    executor: podman-executor
    steps:
      - checkout
      - run:
          name: Install Podman
          command: |
            sudo apt-get update
            sudo apt-get -y install podman
      - run:
          name: Build container image
          command: podman build -f Containerfile -t stig-converter .
      - run:
          name: Run converter
          command: |
            podman run --rm --userns=keep-id \
              -v $(pwd)/stig_downloads:/app/stig_downloads:Z \
              -v $(pwd)/stig_markdown_output:/app/stig_markdown_output:Z \
              stig-converter --test
      - store_artifacts:
          path: stig_markdown_output
          destination: markdown
      - store_artifacts:
          path: stig_downloads
          destination: downloads

workflows:
  version: 2
  convert-stigs:
    jobs:
      - convert
  
  scheduled:
    triggers:
      - schedule:
          cron: "0 2 * * 0"
          filters:
            branches:
              only:
                - main
    jobs:
      - convert
```

## 📊 Environment Variables

All CI/CD systems can use these environment variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `MODE` | Operation mode | `full`, `test`, `process-only` |
| `MAX_PAGES` | Page limit | `20` or empty for all |
| `CONTAINER_ENV` | Container flag | `true` (auto-set) |
| `STIG_HEADLESS` | Browser mode | `true` (recommended) |

## 🎯 Best Practices

### 1. Resource Management
```yaml
# Set appropriate timeouts
timeout-minutes: 120

# Configure resource limits
resources:
  limits:
    memory: 2Gi
    cpu: 2
```

### 2. Caching Strategy
```yaml
# Cache downloads between runs
cache:
  paths:
    - stig_downloads/
```

### 3. Incremental Processing
```bash
# Download once, process multiple times
./run_in_pipeline.sh --mode download-only
./run_in_pipeline.sh --mode process-only
```

### 4. Error Handling
```bash
# Use the pipeline script for proper error handling
./run_in_pipeline.sh --mode test || exit 1
```

### 5. Artifact Management
- Set appropriate retention periods
- Compress large artifacts
- Clean up old artifacts regularly

## 🔒 Security Considerations

1. **Container Security**
   - Runs as non-root user (UID 1000)
   - Read-only configuration mounts
   - No new privileges flag

2. **Secret Management**
   - No credentials required for public STIG downloads
   - Use CI/CD secret management for any future auth needs

3. **Network Security**
   - Container handles SSL/TLS for cyber.mil
   - Timeout controls prevent hanging

## 📈 Performance Optimization

### Parallel Processing
```yaml
# Run multiple modes in parallel
strategy:
  matrix:
    mode: [download-only, process-only]
```

### Build Caching
```yaml
# GitHub Actions with Podman
- name: Cache and build
  run: |
    # Use Podman's built-in layer caching
    podman build --layers \
      --cache-from localhost/stig-converter:cache \
      -t stig-converter:latest .
```

### Incremental Updates
```bash
# Only process new files
if [ -d "stig_downloads" ]; then
  ./run_in_pipeline.sh --mode process-only
else
  ./run_in_pipeline.sh --mode full
fi
```

## 🐛 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Podman not found | Install Podman on the runner |
| Permission denied | Check directory permissions (chmod 755) |
| Out of memory | Increase memory limits or use --max-pages |
| Network timeout | Check cyber.mil accessibility |
| No artifacts | Verify output directories have content |

### Debug Mode
```bash
# Enable verbose logging with Podman
podman run --rm --userns=keep-id \
  -e DEBUG=true \
  -v ./stig_downloads:/app/stig_downloads:Z \
  -v ./stig_markdown_output:/app/stig_markdown_output:Z \
  stig-converter --test
```

## 📚 Related Documentation
- [Main README](../README.md)
- [Container Usage](CONTAINER_USAGE.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)
