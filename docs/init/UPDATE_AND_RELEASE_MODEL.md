# Update and Release Model

## Purpose

This document defines how software is built, promoted, verified, and installed on a robot running TurboPi OpenSource OS.

The goals of this model are:
- Prevent unauthorized or malicious updates
- Ensure users control when updates occur
- Enable safe rollback on failure
- Support future open-source adoption

---

## Core Principles

- Merge does NOT equal deploy
- All updates are explicit and user-initiated
- Only signed releases are installable
- Rollback must always be possible

---

## Release Lifecycle

### 1. Development
- Code is merged into `main`
- CI builds artifacts and runs tests
- No robot updates occur at this stage

### 2. Release Promotion
- Maintainer creates a signed GitHub Release
- Release is marked as **Stable**
- Artifact checksum is published

### 3. User Installation
- Robot checks for latest stable release
- UI displays update availability
- User selects **Update Now**

---

## Update Execution Flow

1. UI calls Update API
2. Updater service downloads artifact
3. Signature and checksum are verified
4. Artifact installed to versioned directory
5. Symlink switched atomically
6. Required services restarted
7. Reboot performed if required
8. Health check validates success
9. Rollback executed automatically on failure

See [docs/updater/RELEASE_INSTALL_LAYOUT.md](../updater/RELEASE_INSTALL_LAYOUT.md) for detailed directory structure and atomic switching mechanism.

---

## UI Controls

### Check for Updates
Queries the release registry and reports availability.

### Update Now
Installs the selected stable release.
Triggers reboot automatically if required.

### Restart Services
Restarts only TurboPi services.
Used for configuration or application-level changes.

### Reboot Bot
Performs a full operating system reboot.
Used for kernel, firmware, or network changes.

---

## Rollback Strategy

- Previous release remains installed
- Failure triggers automatic rollback
- UI displays rollback reason and logs

---

## Security Guarantees

- Unsigned releases are rejected
- Checksums must match exactly
- UI cannot install arbitrary artifacts
