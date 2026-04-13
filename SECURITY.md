# Security Policy

## Supported Versions

Only the latest stable release is supported with security updates.

## Reporting a Vulnerability

Please **do not open public issues** for security vulnerabilities.

Instead, report issues via:
- GitHub Security Advisories (preferred), or
- Direct contact with the repository owner

Reports should include:
- Description of the issue
- Steps to reproduce
- Potential impact

## Supply Chain Security

This project:
- Uses signed releases
- Verifies checksums before installation
- Never auto-updates without user consent

## Prototype Network Trust Model

Current development builds are intended for trusted local network use only.

Known limitation:
- High-impact API actions such as service restart, reboot, and update apply do not yet use a full authentication or authorization model.
- The current implementation limits browser access by requiring same-host UI origin checks for these endpoints.
- This is a prototype safeguard, not a complete security boundary.

Until a real authentication mechanism is implemented:
- Do not expose the API or UI to the public internet.
- Do not treat these endpoints as safe on untrusted or shared networks.
- Treat local network access as trusted operator access.

Future hardening work should add authenticated authorization for privileged API actions before any broader deployment.
