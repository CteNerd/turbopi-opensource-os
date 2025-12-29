# TurboPi Updater Module

This module implements the complete update orchestration system for TurboPi OS, following the specifications in `docs/updater/PROTOCOL.md` and `docs/updater/RELEASE_INSTALL_LAYOUT.md`.

## Architecture

### Core Modules

#### `download.py` - Download & Verification
- Downloads update artifacts from release URLs
- Verifies SHA256 checksums
- Redacts sensitive URLs in logs
- Handles network errors gracefully

#### `install.py` - Installation & Extraction
- Extracts tarballs to versioned release directories (`/opt/turbopi/releases/<version>`)
- Validates release structure (bin/, src/api, src/ui, src/updater)
- Creates and manages metadata.json files
- **Security**: Blocks path traversal and unsafe symlink attacks in tarballs
- Supports Python 3.12+ data filter for enhanced tarball security

#### `health.py` - Health Checks
- Checks systemd service status for all TurboPi services
- Waits for services to become active with configurable timeouts
- Provides detailed service logs for debugging
- Post-update health verification

#### `apply.py` - Update Orchestration
- Coordinates complete update flow: download → verify → extract → switch → restart → health check
- **Atomic symlink switching**: Uses `ln -sfn` for zero-downtime updates
- Service restart in dependency order (api → ui → updater)
- **Automatic rollback**: Reverts to previous version on health check failure
- Handles reboot requirements with clear logging

#### `main.py` - Updater Service
- Background service for update management
- Integrates orchestrator via `apply_update_to_system()` method
- Configuration loading from environment variables

## Service Management

### Service List

The three TurboPi services are defined in `health.py` as a constant:

```python
TURBOPI_SERVICES = [
    'turbopi-api.service',
    'turbopi-ui.service',
    'turbopi-updater.service'
]
```

This constant is shared across modules to ensure consistency in service ordering and health checks.

### Service Restart Order

Services are restarted in dependency order during updates:
1. **turbopi-api.service** - Base API service
2. **turbopi-ui.service** - UI service (depends on API)
3. **turbopi-updater.service** - Updater service (last, as it performs the update)

## Update Flow

### Successful Update

```
1. Download artifact to /opt/turbopi/downloads/<version>/
2. Verify SHA256 checksum
3. Extract to /opt/turbopi/releases/<version>/
4. Validate release structure
5. Update symlinks atomically:
   - previous → old current
   - current → new release
6. Restart services in dependency order
7. Wait for services to become active
8. Run health check
9. Update metadata with health status
✓ Update complete
```

### Failed Update with Rollback

```
1-6. (same as successful update)
7. Health check FAILS ✗
8. Rollback initiated:
   - current → old current (previous)
   - previous → old previous
9. Restart services with old version
10. Verify rollback health check
✓ Rollback complete, system operational
```

### Critical Failure

If rollback also fails:
- System enters inconsistent state
- Detailed service logs captured
- Manual intervention required
- `UpdateError` raised with diagnostic information

## Security Features

### Tarball Extraction Security

1. **Path Traversal Protection**: Blocks paths starting with `..` or absolute paths
2. **Symlink Security**: Validates symlinks don't point outside destination directory
3. **Hardlink Security**: Validates hardlinks don't point outside destination directory
4. **Python 3.12+ Filter**: Uses `filter='data'` for extractall() when available

### Exception Handling

- System exceptions (`KeyboardInterrupt`, `SystemExit`) are allowed to propagate
- Specific exceptions caught where appropriate
- No bare `except:` clauses that could mask errors

## Usage

### Apply an Update

```python
from apply import apply_update

# Apply update with automatic rollback on failure
success = apply_update(
    version='0.1.0',
    download_url='https://github.com/.../turbopi-0.1.0.tar.gz',
    checksum='sha256:abc123...',
    requires_reboot=False
)

if success:
    print("Update successful")
else:
    print("Update failed and rolled back")
```

### Via Updater Service

```python
from main import UpdaterService

service = UpdaterService()

success = service.apply_update_to_system(
    version='0.1.0',
    url='https://github.com/.../turbopi-0.1.0.tar.gz',
    checksum='abc123...',
    requires_reboot=False
)
```

## Testing

84 comprehensive tests covering:
- 16 tests: install.py (extraction, validation, metadata, path traversal)
- 15 tests: health.py (service checks, wait-for-active, timeouts)
- 19 tests: apply.py (orchestration, symlink switching, rollback)
- 3 integration tests: end-to-end flow, rollback verification, sequential updates
- 6 existing tests: backward compatibility
- 25 tests: download.py (existing download/verification tests)

Run all tests:
```bash
cd src/updater
for test_file in test_*.py; do python3 "$test_file"; done
```

## Error Handling

### Exception Hierarchy

- `DownloadError`: Download or network failures
- `ChecksumError`: Checksum verification failures
- `InstallError`: Installation or extraction failures
- `UpdateError`: Update orchestration failures
- `RollbackError`: Rollback failures (critical)

### Failure Modes

1. **Download failure**: No changes made, safe to retry
2. **Install failure**: No changes made, safe to retry
3. **Health check failure**: Automatic rollback, system remains operational
4. **Rollback failure**: Manual intervention required, diagnostic logs captured

## Configuration

Environment variables (loaded from `/etc/turbopi/config.env`):

- `ROBOT_NAME`: Robot identifier
- `AUTO_UPDATE`: Enable automatic updates (default: false)
- `DOWNLOAD_DIR`: Download directory (default: /opt/turbopi/downloads)
- `LOG_LEVEL`: Logging level (default: INFO)

## Protocol Compliance

Fully implements `docs/updater/PROTOCOL.md`:
- ✅ Download artifact + checksum
- ✅ Verify checksum
- ✅ Extract to releases/<version>
- ✅ Update symlink atomically
- ✅ Restart services
- ✅ Run health check
- ✅ Rollback on failure

Follows `docs/updater/RELEASE_INSTALL_LAYOUT.md`:
- ✅ Versioned release directories
- ✅ Atomic symlink switching (current/previous)
- ✅ Metadata tracking per release
- ✅ Service dependency ordering

## See Also

- [Update Protocol](../../docs/updater/PROTOCOL.md)
- [Release Install Layout](../../docs/updater/RELEASE_INSTALL_LAYOUT.md)
- [Runtime Service Skeleton](../../docs/init/RUNTIME_SERVICE_SKELETON.md)
