# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 1.x     | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **Do NOT** open a public GitHub issue.
2. Email the maintainer or use GitHub's private vulnerability reporting feature.
3. Include a description, steps to reproduce, and potential impact.

We aim to acknowledge reports within 48 hours and provide a fix within 7 days for critical issues.

## Security Measures

- Secrets are never stored in code; use environment variables or a secrets manager.
- All infrastructure provisioning uses least-privilege IAM roles.
- Container images run as non-root users.
- Dependencies are monitored via Renovate and scanned with Trivy.
- Gitleaks runs on every PR to prevent secret leakage.
