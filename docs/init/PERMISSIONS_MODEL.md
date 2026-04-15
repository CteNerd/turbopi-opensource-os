# TurboPi Permission Model

## Overview

TurboPi services run under different user contexts with strict systemd sandbox isolation. This document defines the canonical permission model that all installation and update scripts must maintain.

## Service Users

| Service | User | Group | Rationale |
|---------|------|-------|-----------|
| turbopi-api.service | turbopi | turbopi | Unprivileged backend, reads config, writes state/logs |
| turbopi-ui.service | turbopi | turbopi | Unprivileged frontend, serves static content |
| turbopi-updater.service | root | root | Needs root for system updates, chown, systemd unit sync |
| turbopi-wake-word.service | turbopi | turbopi | Unprivileged voice processing |

## Directory Ownership and Permissions

### Runtime Code and Releases

```
/opt/turbopi/                    turbopi:turbopi   drwxr-xr-x (755)
├── current -> releases/X.Y.Z    turbopi:turbopi   lrwxrwxrwx
├── previous -> releases/X.Y.Z   turbopi:turbopi   lrwxrwxrwx
└── releases/
    └── X.Y.Z/                   turbopi:turbopi   drwxr-xr-x (755)
        ├── bin/                 turbopi:turbopi   drwxr-xr-x (755)
        ├── src/                 turbopi:turbopi   drwxr-xr-x (755)
        └── systemd/             turbopi:turbopi   drwxr-xr-x (755)
```

**Rationale**: Services run as `turbopi` user, so all runtime code must be owned by `turbopi:turbopi`. Updater service (running as root) performs chown during extraction.

### State Directory

```
/var/lib/turbopi/                turbopi:turbopi   drwxr-x--- (750)
└── update-trigger.json          turbopi:turbopi   -rw-r----- (640)
```

**Rationale**: API service (as `turbopi` user) creates update trigger files. Updater service (as root) reads and removes them. Directory must be owned by `turbopi:turbopi` for API write access.

**SystemD Integration**: StateDirectory=turbopi in service units should auto-create this directory, but installation scripts ensure it exists with correct ownership.

### Log Directory

```
/var/log/turbopi/                turbopi:turbopi   drwxr-x--- (750)
├── api.log                      turbopi:turbopi   -rw-r----- (640)
├── ui.log                       turbopi:turbopi   -rw-r----- (640)
└── updater.log                  root:root         -rw-r----- (640)
```

**Rationale**: Services write their own logs. Updater runs as root so creates root-owned logs. Directory owned by `turbopi:turbopi` to allow non-root services to write.

**SystemD Integration**: LogsDirectory=turbopi in service units should auto-create this directory.

### Configuration Directory

```
/etc/turbopi/                    root:turbopi      drwxr-x--- (750)
└── config.env                   root:turbopi      -rw-r----- (640)
```

**Rationale**: Configuration file contains sensitive data (API tokens, passwords). Only root can write, but `turbopi` group can read. Services running as `turbopi` user can read via group membership.

## SystemD Sandbox Restrictions

All services use `ProtectSystem=strict`, making `/usr`, `/boot`, and `/etc` read-only by default. Services explicitly whitelist writable paths:

### turbopi-api.service

```ini
ReadWritePaths=/var/lib/turbopi /var/log/turbopi
StateDirectory=turbopi
StateDirectoryMode=0750
LogsDirectory=turbopi
LogsDirectoryMode=0750
```

**Access**: Can write to `/var/lib/turbopi` (update triggers) and `/var/log/turbopi` (logs).

### turbopi-updater.service

```ini
ReadWritePaths=/opt/turbopi /etc/systemd/system /var/lib/turbopi
```

**Access**: Can modify runtime code in `/opt/turbopi`, sync systemd units to `/etc/systemd/system`, and consume update triggers from `/var/lib/turbopi`.

### turbopi-ui.service

```ini
ReadWritePaths=/var/log/turbopi
LogsDirectory=turbopi
LogsDirectoryMode=0750
```

**Access**: Can write logs only.

## Installation and Update Contracts

### Fresh Installation (install-services.sh)

Must create and set ownership on:

1. `/opt/turbopi` → `turbopi:turbopi`
2. `/var/lib/turbopi` → `turbopi:turbopi` (mode 0750)
3. `/var/log/turbopi` → `turbopi:turbopi` (mode 0750)
4. `/etc/turbopi` → `root:turbopi` (mode 0750)
5. `/etc/turbopi/config.env` → `root:turbopi` (mode 0640)

### Release Updates (updater/install.py extract_tarball)

After extracting tarball to `/opt/turbopi/releases/X.Y.Z`, must:

```python
subprocess.run(['chown', '-R', 'turbopi:turbopi', dest_dir], check=False)
```

**Rationale**: GitHub Actions builds tarballs with UID/GID 1001:1001. Services cannot access files with wrong ownership, causing "Permission denied" on chdir.

### SystemD Unit Sync (updater/apply.py sync_systemd_units_from_release)

After extracting release, before restarting services:

```python
# Copy systemd/*.service from release to /etc/systemd/system/
# Run systemctl daemon-reload
```

**Rationale**: Updater service has `/etc/systemd/system` in ReadWritePaths, allowing it to update service definitions during releases.

## Common Permission Issues and Fixes

### Issue: API service cannot create update trigger file

**Symptom**: `Permission denied: /var/lib/turbopi/update-trigger.json.tmp`

**Root Cause**: `/var/lib/turbopi` owned by root or has incorrect permissions.

**Fix**:
```bash
sudo chown turbopi:turbopi /var/lib/turbopi
sudo chmod 0750 /var/lib/turbopi
```

### Issue: Services fail to start after update with "Permission denied" chdir

**Symptom**: Service fails immediately after update with permission error accessing `/opt/turbopi/current/src/`

**Root Cause**: Release directory extracted with wrong ownership (UID 1001:1001 from tarball).

**Fix**: Run ownership fix manually:
```bash
sudo chown -R turbopi:turbopi /opt/turbopi/releases/X.Y.Z
```

**Prevention**: Updater's `extract_tarball()` should run chown automatically after extraction.

### Issue: Systemd unit sync fails with "Read-only file system"

**Symptom**: Update fails at Step 4 with error writing to `/etc/systemd/system/`

**Root Cause**: `turbopi-updater.service` missing `/etc/systemd/system` in ReadWritePaths.

**Fix**: Update service unit and reload:
```bash
sudo nano /etc/systemd/system/turbopi-updater.service
# Add /etc/systemd/system to ReadWritePaths
sudo systemctl daemon-reload
sudo systemctl restart turbopi-updater.service
```

## Audit and Repair Script

For comprehensive permission fixes, run:

```bash
sudo bash /opt/turbopi/current/system/fix-permissions.sh
```

This script audits and repairs all directory ownership and permissions to match the canonical model.

## See Also

- [../config/SCHEMA.md](../config/SCHEMA.md) - Configuration file format
- [SETUP_AND_CONFIGURATION.md](./SETUP_AND_CONFIGURATION.md) - Installation guide
- [UPDATE_AND_RELEASE_MODEL.md](./UPDATE_AND_RELEASE_MODEL.md) - Update process
