# Release Install Layout

This document defines the directory structure and symlink strategy for TurboPi OS releases, enabling atomic version switching and safe rollback.

## Overview

The release install layout supports:
- **Atomic version switching** - Zero-downtime updates via symlink swap
- **Previous version preserved** - Automatic rollback on failure
- **Multiple versions coexist** - Clean separation between releases
- **Version-agnostic service paths** - Services reference `/opt/turbopi/current`

## Directory Structure

```
/opt/turbopi/
├── releases/              # All installed release versions
│   ├── 0.1.0/            # Example: Release version 0.1.0
│   │   ├── bin/          # Service launcher scripts
│   │   │   ├── api       # API service executable
│   │   │   ├── ui        # UI service executable
│   │   │   └── updater   # Updater service executable
│   │   ├── src/          # Service implementations
│   │   │   ├── api/
│   │   │   │   └── main.py
│   │   │   ├── ui/
│   │   │   │   └── main.py
│   │   │   └── updater/
│   │   │       └── main.py
│   │   ├── lib/          # Shared libraries (if needed)
│   │   └── metadata.json # Release metadata and checksums
│   ├── 0.1.1/            # Example: Release version 0.1.1
│   │   └── ...           # Same structure as 0.1.0
│   └── 0.0.9/            # Example: Previous release
│       └── ...           # Same structure as 0.1.0
├── current -> releases/0.1.0   # Symlink to active release
├── previous -> releases/0.0.9  # Symlink to previous release
└── downloads/            # Temporary download staging area
    └── ...               # Downloaded artifacts before verification

/etc/turbopi/
└── config.env            # Runtime configuration (shared across versions)

/var/log/turbopi/         # Service logs (shared across versions)
└── ...

/var/lib/turbopi/         # Persistent state data (shared across versions)
└── ...
```

## Symlink Strategy

### Current Release (`/opt/turbopi/current`)

The `current` symlink points to the active release that services are running from.

- **Purpose**: Provides a stable, version-agnostic path for systemd services
- **Target**: Points to `/opt/turbopi/releases/<version>`
- **Update Method**: Atomic symlink swap using `ln -sfn`
- **Accessed By**: All systemd service units via `ExecStart=/opt/turbopi/current/bin/<service>`

**Example:**
```bash
/opt/turbopi/current -> /opt/turbopi/releases/0.1.0
```

### Previous Release (`/opt/turbopi/previous`)

The `previous` symlink points to the last known working release for rollback.

- **Purpose**: Enables automatic rollback on failed health checks
- **Target**: Points to `/opt/turbopi/releases/<previous-version>`
- **Update Method**: Set to old `current` value before updating `current`
- **Accessed By**: Updater service during rollback operations

**Example:**
```bash
/opt/turbopi/previous -> /opt/turbopi/releases/0.0.9
```

## Atomic Version Switching

Version switching is atomic and follows this sequence:

### Update Sequence

1. **Download** - Fetch new release to `/opt/turbopi/downloads/<version>/`
2. **Verify** - Check signature and checksum
3. **Extract** - Unpack to `/opt/turbopi/releases/<version>/`
4. **Update Previous** - Point `previous` to current `current` target
   ```bash
   ln -sfn "$(readlink /opt/turbopi/current)" /opt/turbopi/previous
   ```
5. **Switch Current** - Point `current` to new release atomically
   ```bash
   ln -sfn /opt/turbopi/releases/<version> /opt/turbopi/current
   ```
6. **Restart Services** - Reload services using new code (in dependency order)
   ```bash
   systemctl restart turbopi-api.service
   systemctl restart turbopi-ui.service
   systemctl restart turbopi-updater.service  # Last, as it performs the update
   ```
7. **Health Check** - Verify services are healthy
8. **Cleanup** - Remove download staging directory (only if health check passed; preserve failed releases for debugging)

### Rollback Sequence

If health checks fail after update:

1. **Save Old Previous** - Store the target of `previous` before update (e.g., 0.1.0)
2. **Switch Current** - Point `current` back to `previous` target
   ```bash
   ln -sfn "$(readlink /opt/turbopi/previous)" /opt/turbopi/current
   ```
3. **Restore Previous** - Restore `previous` to the saved version from step 1 (to enable further rollback if needed)
   ```bash
   # Example: if old previous was 0.1.0
   ln -sfn /opt/turbopi/releases/0.1.0 /opt/turbopi/previous
   ```
4. **Restart Services** - Reload services with previous version
5. **Health Check** - Verify rollback succeeded
6. **Log Failure** - Record rollback reason for user visibility

### Atomicity Guarantees

- `ln -sfn` performs atomic symlink replacement (single syscall)
- Services reading from `/opt/turbopi/current` see either old or new version, never a partial state
- Failed updates do not leave the system in a broken state
- Rollback restores the exact previous configuration

## Version Preservation

### Automatic Cleanup

- Keep **current** release (active)
- Keep **previous** release (for rollback)
- Keep up to **2 additional older releases** (configurable)
- Remove releases older than retention policy

### Manual Cleanup

Administrators can manually remove old releases:

```bash
# List installed releases
ls -la /opt/turbopi/releases/

# Remove a specific release (only if not current or previous)
rm -rf /opt/turbopi/releases/0.0.8
```

**Safety**: The updater service will refuse to remove releases pointed to by `current` or `previous` symlinks.

## Release Metadata

Each release directory contains a `metadata.json` file with release information:

```json
{
  "version": "0.1.0",
  "release_date": "2024-01-15T14:30:00Z",
  "checksum": "sha256:abc123...",
  "signature": "-----BEGIN PGP SIGNATURE-----...",
  "install_date": "2024-01-20T09:15:00Z",
  "source_url": "https://github.com/CteNerd/turbopi-opensource-os/releases/download/v0.1.0/turbopi-0.1.0.tar.gz",
  "requires_reboot": false,
  "health_check_passed": true
}
```

### Metadata Fields

- `version` - Semantic version string (e.g., "0.1.0")
- `release_date` - When the release was published (ISO 8601 format: `YYYY-MM-DDTHH:MM:SSZ`)
- `checksum` - SHA256 checksum for verification
- `signature` - PGP signature for authenticity (future)
- `install_date` - When this release was installed on this robot (ISO 8601 format: `YYYY-MM-DDTHH:MM:SSZ`)
- `source_url` - Download URL for this release
- `requires_reboot` - Whether this release requires a system reboot
- `health_check_passed` - Result of post-install health check

## Shared Resources

### Configuration (`/etc/turbopi/config.env`)

Runtime configuration is stored outside `/opt/turbopi` and shared across all releases.

- **Location**: `/etc/turbopi/config.env`
- **Format**: Shell environment variables
- **Permissions**: `640` (root:turbopi)
- **Upgrade Behavior**: Preserved across updates

### Logs (`/var/log/turbopi/`)

Service logs are managed by systemd/journald and shared across releases.

- **Storage**: systemd journal (queryable via `journalctl`)
- **Retention**: Per system journald configuration
- **Upgrade Behavior**: Continuous logging across version changes

### Persistent Data (`/var/lib/turbopi/`)

Any persistent application state (databases, caches) is stored outside releases.

- **Location**: `/var/lib/turbopi/`
- **Ownership**: `turbopi:turbopi`
- **Upgrade Behavior**: Preserved across updates
- **Migration**: Handled by post-install scripts if schema changes

## Service Integration

### Systemd Service Files

Service files reference the `current` symlink for version-agnostic execution:

```ini
[Service]
Type=simple
User=turbopi
EnvironmentFile=/etc/turbopi/config.env
ExecStart=/opt/turbopi/current/bin/api
Restart=always
```

### Version-Agnostic Paths

Services must use `/opt/turbopi/current` not absolute version paths:

- ✅ **Correct**: `/opt/turbopi/current/bin/api`
- ❌ **Wrong**: `/opt/turbopi/releases/0.1.0/bin/api`

This ensures services automatically use the new version after symlink swap.

## Installation Requirements

### Filesystem Requirements

- `/opt/turbopi` must be writable by updater service (runs as root)
- Sufficient disk space for multiple concurrent releases (estimated 100MB per release)
- Filesystem must support symbolic links (standard on ext4, btrfs, xfs)

### Permissions

```bash
/opt/turbopi/                     # root:root 755
/opt/turbopi/releases/            # root:root 755
/opt/turbopi/releases/<version>/  # root:root 755 (read-only to prevent privilege escalation)
/opt/turbopi/current              # root:root (symlink - permissions from target)
/opt/turbopi/previous             # root:root (symlink - permissions from target)
/opt/turbopi/downloads/           # root:root 700
```

**Security Note**: Release directories must be owned by `root:root` and not writable by unprivileged users. Since the updater service runs as root and executes code from these directories, making them writable by the `turbopi` user would allow privilege escalation if that account were compromised. The API and UI services run as the unprivileged `turbopi` user and only need read access to the release directories.

### Initial Installation

On first boot, the install script creates the initial release:

**Note**: Development installations use the `-dev` suffix (e.g., `0.1.0-dev`) to distinguish them from official tagged releases.

```bash
# Create directory structure
mkdir -p /opt/turbopi/releases/0.1.0-dev
mkdir -p /opt/turbopi/downloads

# Copy initial installation
cp -r /path/to/repo/src/* /opt/turbopi/releases/0.1.0-dev/

# Create initial symlinks
ln -sfn /opt/turbopi/releases/0.1.0-dev /opt/turbopi/current
ln -sfn /opt/turbopi/releases/0.1.0-dev /opt/turbopi/previous

# Set permissions (root-owned for security)
chown -R root:root /opt/turbopi/releases/0.1.0-dev
chmod -R 755 /opt/turbopi/releases/0.1.0-dev
```

## Update Protocol Integration

This layout is designed to work with the update protocol defined in [PROTOCOL.md](./PROTOCOL.md).

### Update Flow

1. **Fetch** - Download release metadata from GitHub
2. **Download** - Download artifact to `/opt/turbopi/downloads/<version>/`
3. **Verify** - Check checksum matches metadata
4. **Extract** - Unpack to `/opt/turbopi/releases/<version>/`
5. **Update Symlinks** - Atomically update `previous` and `current`
6. **Restart** - Restart services via systemd
7. **Health Check** - Verify new version works
8. **Rollback** - Automatically rollback if health check fails
9. **Cleanup** - Remove old downloads and releases per retention policy

### Reboot Handling

If `metadata.json` indicates `requires_reboot: true`:

1. Complete symlink update
2. Create reboot marker: `/var/lib/turbopi/pending-reboot`
3. Display reboot notification in UI
4. Reboot system via `systemctl reboot`
5. After reboot, run health check
6. Remove reboot marker on success

## Migration from Current Layout

The current installation uses `/opt/turbopi/current/` directly. Migration to versioned layout:

### Migration Script

```bash
#!/bin/bash
# Migrate from direct current/ to versioned releases layout

# Backup current installation
CURRENT_VERSION=$(grep VERSION /etc/turbopi/config.env | cut -d= -f2)
mkdir -p /opt/turbopi/releases
mv /opt/turbopi/current /opt/turbopi/releases/${CURRENT_VERSION}

# Create symlinks
ln -sfn /opt/turbopi/releases/${CURRENT_VERSION} /opt/turbopi/current
ln -sfn /opt/turbopi/releases/${CURRENT_VERSION} /opt/turbopi/previous

# Create metadata
cat > /opt/turbopi/releases/${CURRENT_VERSION}/metadata.json << EOF
{
  "version": "${CURRENT_VERSION}",
  "install_date": "$(date -Iseconds)",
  "source": "migration",
  "health_check_passed": true
}
EOF
```

This migration is non-breaking - services continue to work via the `current` symlink.

## Examples

### Example: Fresh Install (0.1.0)

```bash
/opt/turbopi/
├── releases/
│   └── 0.1.0/
│       ├── bin/
│       ├── src/
│       └── metadata.json
├── current -> releases/0.1.0
└── previous -> releases/0.1.0
```

### Example: After First Update (0.1.1)

```bash
/opt/turbopi/
├── releases/
│   ├── 0.1.0/
│   └── 0.1.1/
├── current -> releases/0.1.1
└── previous -> releases/0.1.0
```

### Example: After Second Update (0.1.2)

```bash
/opt/turbopi/
├── releases/
│   ├── 0.1.0/           # First additional older release (kept per retention policy)
│   ├── 0.1.1/           # Previous release
│   └── 0.1.2/           # Current release
├── current -> releases/0.1.2
└── previous -> releases/0.1.1
```

### Example: After Third Update (0.1.3)

```bash
/opt/turbopi/
├── releases/
│   ├── 0.1.0/           # Second additional older release (kept - at retention limit of 4)
│   ├── 0.1.1/           # First additional older release (kept)
│   ├── 0.1.2/           # Previous release
│   └── 0.1.3/           # Current release
├── current -> releases/0.1.3
└── previous -> releases/0.1.2
```

### Example: After Fourth Update (0.1.4) with Cleanup

```bash
/opt/turbopi/
├── releases/
│   ├── 0.1.1/           # First additional older release (kept)
│   ├── 0.1.2/           # Second additional older release (kept)
│   ├── 0.1.3/           # Previous release
│   └── 0.1.4/           # Current release
├── current -> releases/0.1.4
└── previous -> releases/0.1.3

# Note: 0.1.0 was removed during cleanup (exceeded retention: current + previous + 2 = 4 max)
```

### Example: After Failed Update (Rollback)

```bash
# Before update
current -> releases/0.1.1
previous -> releases/0.1.0

# Update to 0.1.2 attempted
current -> releases/0.1.2   # New version
previous -> releases/0.1.1  # Previous working version

# Health check fails - rollback
current -> releases/0.1.1   # Rolled back
previous -> releases/0.1.0  # Restored to enable further rollback if needed

# Note: If rollback also fails, both symlinks would point to the same version,
# losing the ability to rollback further. The system should enter safe mode.
```

## References

- [Update Protocol](./PROTOCOL.md) - Update execution flow
- [Update and Release Model](../init/UPDATE_AND_RELEASE_MODEL.md) - High-level release strategy
- [Runtime Service Skeleton](../init/RUNTIME_SERVICE_SKELETON.md) - Service integration

## Acceptance Criteria

This document satisfies the acceptance criteria:

✅ **AC1: /opt/turbopi/releases/** - Defined versioned release directory structure  
✅ **AC2: Atomic version switching** - Documented symlink strategy for zero-downtime updates  
✅ **AC3: Previous version preserved** - Documented `previous` symlink and rollback mechanism  
✅ **AC4: Follows PROTOCOL.md** - Aligned with update steps and reboot rules
