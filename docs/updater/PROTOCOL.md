# Updater Protocol

## Directory Layout

/opt/turbopi/
  releases/
    0.1.0/
    0.1.1/
  current -> releases/0.1.0
  previous -> releases/0.0.9

See [RELEASE_INSTALL_LAYOUT.md](./RELEASE_INSTALL_LAYOUT.md) for complete directory structure and symlink strategy.

## Update Steps

1. Fetch latest stable release metadata
2. Download artifact + checksum
3. Verify checksum
4. Extract to releases/<version>
5. Update symlink atomically
6. Sync managed systemd units from release payload (if present), then daemon-reload
7. Restart runtime services
8. Run health check
9. Rollback on failure

## Reboot Rules

Reboot required if:
- Kernel updated
- Network stack updated
- Explicit reboot flag present

UI must explain reason clearly.
