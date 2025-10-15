## Container Image Security Scanning

This project’s container build pipeline performs multiple security checks to improve supply chain security and provide actionable remediation guidance.

### What runs in the build

- Vulnerability scanning (Trivy)
  - OS packages and language dependencies
  - SARIF, JSON, and human-readable TXT outputs
  - SARIF uploaded to the GitHub Security tab
  - Severity narrowed to HIGH, CRITICAL for SARIF (faster uploads)
  - Unfixed vulnerabilities ignored in SARIF to reduce noise
- SBOM generation (Syft)
  - CycloneDX JSON, SPDX JSON, Syft JSON, and a human-readable summary
  - Suitable for downstream tools like Grype/Trivy
- SBOM-based vulnerability scan (Grype)
  - Second opinion scan using the Syft SBOM
- Secrets and misconfigurations (Trivy)
  - Secret scanning to detect hard-coded credentials
  - Configuration scanning for container best practices

All scans are non-blocking: findings are reported but do not fail the build.

### Where to find results

- GitHub Actions job summary
  - Counts by severity and category (OS vs app dependencies)
  - Top packages with available fixes
  - Top CRITICAL/HIGH CVEs with package context
- Artifacts (90-day retention)
  - `security-scan-{run}`: all scanner outputs (SARIF, JSON, TXT)
  - `sbom-{run}`: SBOMs in multiple formats and metadata
- GitHub Security tab
  - Trivy SARIF is uploaded under Code Scanning Alerts

### Usage examples

- Review actionable fixes directly in the job summary
- Download `security-scan-{run}` for full details and CI integration
- Use the SBOM with additional tools:
  - Grype: `grype sbom:sbom-syft.json`
  - Trivy: `trivy sbom sbom-cyclonedx.json`

### Operational notes

- Push to registry happens after tests and scans (avoids publishing untested images)
- Uploads use retries to handle transient registry or network issues
- The build uses a single shared image archive to ensure scanner compatibility


