# Container Registry Guide

This guide explains how to use and manage the pre-built container images published to GitHub Container Registry (ghcr.io).

## 📦 Available Images

Container images are automatically built and published when:
- **Every commit** to the main branch
- **Every commit** to the dev branch (if exists)
- A new version tag is created (e.g., v1.0.0)
- Pull requests to main (for testing, not published)
- Weekly on Mondays (optional, for security updates)
- Manual trigger via GitHub Actions

### Image Location
```
ghcr.io/larmbuster/stig_xccdf2markdown
```

### Available Tags

| Tag | Description | When Updated |
|-----|-------------|--------------|
| `latest` | Latest stable build | Every commit to main branch |
| `dev` | Latest development build | Every commit to dev branch |
| `v1.0.0` | Specific version release | When version tag is created |
| `sha-XXXXXXX` | Specific commit build | Every commit to main/dev |
| `pr-123` | Pull request test build | On PR creation/update (not published) |

## 🚀 Using Pre-built Images

### Pull the Image
```bash
# Pull latest stable version
podman pull ghcr.io/larmbuster/stig_xccdf2markdown:latest

# Pull a specific version
podman pull ghcr.io/larmbuster/stig_xccdf2markdown:v1.0.0

# Pull a specific commit
podman pull ghcr.io/larmbuster/stig_xccdf2markdown:sha-abc1234
```

### Run the Container
```bash
# Basic usage with latest image
podman run --rm --userns=keep-id \
  -v $(pwd)/stig_downloads:/app/stig_downloads:Z \
  -v $(pwd)/stig_markdown_output:/app/stig_markdown_output:Z \
  ghcr.io/larmbuster/stig_xccdf2markdown:latest --test

# Full conversion
podman run --rm --userns=keep-id \
  -v $(pwd)/stig_downloads:/app/stig_downloads:Z \
  -v $(pwd)/stig_markdown_output:/app/stig_markdown_output:Z \
  ghcr.io/larmbuster/stig_xccdf2markdown:latest

# Process existing files only
podman run --rm --userns=keep-id \
  -v $(pwd)/stig_downloads:/app/stig_downloads:Z \
  -v $(pwd)/stig_markdown_output:/app/stig_markdown_output:Z \
  ghcr.io/larmbuster/stig_xccdf2markdown:latest --process-only
```

## 🔒 Authentication

### Public Access
The container images are **public by default** if the repository is public. No authentication is needed to pull them.

### Private Repository
If the repository is private, you'll need to authenticate:

```bash
# Login with GitHub Personal Access Token (PAT)
echo $GITHUB_TOKEN | podman login ghcr.io -u USERNAME --password-stdin

# Or interactively
podman login ghcr.io
```

Required PAT permissions:
- `read:packages` - To pull images
- `write:packages` - To push images (maintainers only)
- `delete:packages` - To delete images (maintainers only)

## 📋 Image Management

### List Available Tags
```bash
# Using GitHub CLI
gh api \
  -H "Accept: application/vnd.github+json" \
  /users/larmbuster/packages/container/stig_xccdf2markdown/versions

# Using curl
curl -L \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://api.github.com/users/larmbuster/packages/container/stig_xccdf2markdown/versions
```

### Inspect Image
```bash
# View image details
podman inspect ghcr.io/larmbuster/stig_xccdf2markdown:latest

# View image layers
podman history ghcr.io/larmbuster/stig_xccdf2markdown:latest

# View image size
podman images ghcr.io/larmbuster/stig_xccdf2markdown
```

### Clean Up Local Images
```bash
# Remove specific image
podman rmi ghcr.io/larmbuster/stig_xccdf2markdown:latest

# Remove all unused images
podman image prune -a
```

## 🔄 CI/CD Integration

### GitHub Actions
```yaml
jobs:
  use-prebuilt:
    runs-on: ubuntu-latest
    steps:
    - name: Run STIG Converter
      run: |
        podman run --rm --userns=keep-id \
          -v ${{ github.workspace }}/stig_downloads:/app/stig_downloads:Z \
          -v ${{ github.workspace }}/stig_markdown_output:/app/stig_markdown_output:Z \
          ghcr.io/${{ github.repository }}:latest --test
```

### GitLab CI
```yaml
convert:
  image: ghcr.io/larmbuster/stig_xccdf2markdown:latest
  script:
    - python stig_converter.py --test
```

### Jenkins
```groovy
pipeline {
    agent {
        docker {
            image 'ghcr.io/larmbuster/stig_xccdf2markdown:latest'
        }
    }
    stages {
        stage('Convert') {
            steps {
                sh 'python stig_converter.py --test'
            }
        }
    }
}
```

## 🏷️ Versioning Strategy

### Semantic Versioning
When creating releases, use semantic versioning:
- `v1.0.0` - Major version (breaking changes)
- `v1.1.0` - Minor version (new features)
- `v1.1.1` - Patch version (bug fixes)

### Creating a Release
```bash
# Tag the repository
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0

# The GitHub Action will automatically build and tag the image
```

## 🔍 Troubleshooting

### Image Pull Errors

**"unauthorized: authentication required"**
- The repository might be private
- Solution: Authenticate with `podman login ghcr.io`

**"manifest unknown"**
- The tag doesn't exist
- Solution: Check available tags on GitHub Packages page

**"no space left on device"**
- Local disk is full
- Solution: Clean up old images with `podman image prune`

### Container Run Errors

**"permission denied"**
- SELinux context issue
- Solution: Ensure `:Z` flag on volume mounts

**"cannot find user"**
- User namespace issue
- Solution: Use `--userns=keep-id` flag

## 📊 Image Size Optimization

The current image is optimized for:
- Small size (~800MB)
- Fast startup
- Security (non-root user)

Future optimizations could include:
- Multi-stage builds (already implemented)
- Alpine Linux base (would need Firefox ESR package)
- Distroless images (complex with Firefox requirement)

## 🔗 Related Documentation
- [Container Usage Guide](CONTAINER_USAGE.md)
- [CI/CD Integration](CI_CD_INTEGRATION.md)
- [Main README](../README.md)
