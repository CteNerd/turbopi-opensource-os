# Runtime Service Skeleton

This document describes the runtime service skeleton implementation for TurboPi OpenSource OS.

## Overview

The runtime service skeleton establishes a consistent runtime model using systemd and shared configuration. It provides the foundation for all TurboPi services with standardized:

- Service lifecycle management via systemd
- Shared configuration via `/etc/turbopi/config.env`
- Logging and monitoring
- Security hardening

## Services

### API Backend (`turbopi-api.service`)
- **Port**: 8080 (configurable)
- **Purpose**: REST API for robot control and system management
- **Implementation**: Python HTTP server
- **User**: `turbopi` (unprivileged)

**Key Features**:
- Health endpoint at `/health`
- System status monitoring (uptime, CPU temperature, version)
- Configuration loading from environment

### Web UI (`turbopi-ui.service`)
- **Port**: 8081 (configurable)
- **Purpose**: Browser-based control interface
- **Implementation**: Python HTTP server
- **User**: `turbopi` (unprivileged)

**Key Features**:
- Simple status dashboard
- Configuration display
- Foundation for future UI features

### Updater (`turbopi-updater.service`)
- **Port**: N/A (background service)
- **Purpose**: Software update management
- **Implementation**: Python daemon
- **User**: `root` (requires elevated permissions for updates)

**Key Features**:
- Background monitoring
- Configuration-based auto-update control
- Foundation for release promotion system

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  systemd (init)                     │
│                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │
│  │ turbopi-api  │  │ turbopi-ui   │  │ turbopi- │ │
│  │              │  │              │  │ updater  │ │
│  │ Port: 8080   │  │ Port: 8081   │  │          │ │
│  └──────┬───────┘  └──────┬───────┘  └────┬─────┘ │
│         │                  │               │       │
└─────────┼──────────────────┼───────────────┼───────┘
          │                  │               │
          └──────────┬───────┴───────────────┘
                     │
          ┌──────────▼──────────────┐
          │ /etc/turbopi/config.env │
          │   Shared Configuration  │
          └─────────────────────────┘
```

## Configuration

All services load configuration from `/etc/turbopi/config.env` via systemd's `EnvironmentFile` directive.

### Configuration File Location
- **Path**: `/etc/turbopi/config.env`
- **Permissions**: `640` (readable by root and turbopi group, writable by root)
- **Format**: Shell environment variable format

### Key Configuration Variables

```bash
# Robot Identity
ROBOT_NAME=TurboPi
WAKE_WORD=Jarvis
VERSION=0.1.0-dev

# Service Configuration
API_HOST=0.0.0.0
API_PORT=8080
UI_HOST=0.0.0.0
UI_PORT=8081

# Safety Parameters
MAX_LINEAR_SPEED=0.5
MAX_ANGULAR_SPEED=1.2
DEADMAN_TIMEOUT_MS=500
MANUAL_OVERRIDE_TIMEOUT_MS=500

# Update Configuration
AUTO_UPDATE=false
AUTO_UPDATE_CHANNEL=stable
AUTO_UPDATE_SCHEDULE_UTC=03:00

# Logging
LOG_LEVEL=INFO
```

See `system/config.env.example` for complete configuration template.

## Installation

### Prerequisites
- Raspberry Pi OS (Debian-based)
- Python 3 (pre-installed on Raspberry Pi OS)
- systemd (standard on modern Linux)
- Root access

### Installation Steps

1. Clone or download the TurboPi repository:
   ```bash
   git clone https://github.com/CteNerd/turbopi-opensource-os.git
   cd turbopi-opensource-os
   ```

2. Run the installation script:
   ```bash
   cd system
   sudo ./install-services.sh
   ```

The installation script will:
- Create `/opt/turbopi/current/` directory structure
- Install service binaries and implementations
- Create default `/etc/turbopi/config.env` configuration
- Create `turbopi` system user
- Install systemd service files
- Enable services for automatic startup

3. Customize configuration:
   ```bash
   sudo nano /etc/turbopi/config.env
   ```

4. Start services:
   ```bash
   sudo systemctl start turbopi-api.service
   sudo systemctl start turbopi-ui.service
   sudo systemctl start turbopi-updater.service
   ```

## Testing

### Automated Testing

Run the test suite to verify installation:

```bash
cd system
sudo ./test-services.sh
```

The test script verifies:
- ✓ Configuration file exists
- ✓ Systemd service files are installed
- ✓ Services are enabled for boot
- ✓ Services are running (if started)
- ✓ Health endpoint responds correctly
- ✓ Configuration is loaded by services

### Manual Testing

#### Test Health Endpoint
```bash
curl http://localhost:8080/health
```

Expected response:
```json
{
  "status": "ok",
  "uptime": 123.45,
  "cpu_temp": 45.6,
  "version": "0.1.0-dev",
  "timestamp": "2025-12-17T00:00:00.000000Z"
}
```

#### Test Web UI
Open in browser: `http://localhost:8081/`

Expected: Simple status dashboard showing:
- Robot name
- Service status
- Configuration status

#### Check Service Status
```bash
sudo systemctl status turbopi-api.service
sudo systemctl status turbopi-ui.service
sudo systemctl status turbopi-updater.service
```

#### View Service Logs
```bash
sudo journalctl -u turbopi-api.service -f
sudo journalctl -u turbopi-ui.service -f
sudo journalctl -u turbopi-updater.service -f
```

## Service Management

### Start Services
```bash
sudo systemctl start turbopi-api.service
sudo systemctl start turbopi-ui.service
sudo systemctl start turbopi-updater.service
```

### Stop Services
```bash
sudo systemctl stop turbopi-api.service
sudo systemctl stop turbopi-ui.service
sudo systemctl stop turbopi-updater.service
```

### Restart Services
```bash
sudo systemctl restart turbopi-api.service
sudo systemctl restart turbopi-ui.service
sudo systemctl restart turbopi-updater.service
```

### Enable Services (Auto-start on Boot)
```bash
sudo systemctl enable turbopi-api.service
sudo systemctl enable turbopi-ui.service
sudo systemctl enable turbopi-updater.service
```

### Disable Services
```bash
sudo systemctl disable turbopi-api.service
sudo systemctl disable turbopi-ui.service
sudo systemctl disable turbopi-updater.service
```

## Security

### Service User
- API and UI services run as unprivileged `turbopi` user
- Updater service runs as `root` (requires elevated permissions for system updates)

### Security Hardening
All services use systemd security features:
- `NoNewPrivileges=true` - Prevents privilege escalation
- `PrivateTmp=true` - Isolated temporary directories
- `ProtectSystem=strict` - Read-only system directories
- `ProtectHome=true` - Inaccessible home directories
- `ReadWritePaths` - Limited write access to specific directories

### Configuration Security
- Configuration file readable by all services
- No secrets stored in skeleton implementation
- Future: API keys and credentials will use secure storage

## Directory Structure

```
/opt/turbopi/
├── current/                    # Current installation
│   ├── bin/                   # Service wrapper scripts
│   │   ├── api               # API service launcher
│   │   ├── ui                # UI service launcher
│   │   └── updater           # Updater service launcher
│   └── src/                  # Service implementations
│       ├── api/
│       │   └── main.py      # API service code
│       ├── ui/
│       │   └── main.py      # UI service code
│       └── updater/
│           └── main.py      # Updater service code

/etc/turbopi/
└── config.env                 # Runtime configuration

/etc/systemd/system/           # Systemd service files
├── turbopi-api.service
├── turbopi-ui.service
└── turbopi-updater.service

/var/log/turbopi/              # Service logs (via journald)
```

## Troubleshooting

### Service Won't Start

Check service status:
```bash
sudo systemctl status turbopi-api.service
```

View detailed logs:
```bash
sudo journalctl -u turbopi-api.service -n 50
```

Common issues:
- Port already in use: Check if another process is using port 8080/8081
- Permission denied: Ensure service files have correct permissions
- Missing dependencies: Ensure Python 3 is installed

### Health Endpoint Not Responding

1. Check if API service is running:
   ```bash
   sudo systemctl is-active turbopi-api.service
   ```

2. Check if port is listening:
   ```bash
   sudo netstat -tulpn | grep 8080
   ```

3. Test with verbose output:
   ```bash
   curl -v http://localhost:8080/health
   ```

### Configuration Not Loading

1. Check if config file exists:
   ```bash
   ls -la /etc/turbopi/config.env
   ```

2. Verify EnvironmentFile directive in service:
   ```bash
   grep EnvironmentFile /etc/systemd/system/turbopi-api.service
   ```

3. Check service logs for configuration values:
   ```bash
   sudo journalctl -u turbopi-api.service | grep "Robot Name"
   ```

## Acceptance Criteria

This implementation satisfies all acceptance criteria:

### ✅ AC1: API, UI, updater start on boot
- All services installed with systemd
- Services enabled via `systemctl enable`
- Automatic startup on system boot
- Verified with `systemctl is-enabled`

### ✅ AC2: config.env loaded via systemd
- Configuration file created at `/etc/turbopi/config.env`
- Services configured with `EnvironmentFile=/etc/turbopi/config.env`
- Environment variables loaded before service starts
- Verified in service logs

### ✅ AC3: Health endpoint available
- API service provides `/health` endpoint
- Returns JSON with system status
- Includes uptime, CPU temperature, version
- Verified with `curl http://localhost:8080/health`

## Future Enhancements

This skeleton provides the foundation for future EPICs:

- **EPIC 3: Setup Wizard** - UI-driven onboarding
- **EPIC 4: Release Promotion** - Full updater implementation
- **EPIC 8: Core Control API** - Complete API per OpenAPI spec
- **EPIC 10: Observability** - Enhanced logging and monitoring

## References

- [System Configuration](../../system/README.md)
- [Service Implementations](../../src/README.md)
- [API Specification](../api/OPENAPI.yaml)
- [Architecture Overview](ARCHITECTURE.md)
- [Configuration Schema](../config/SCHEMA.md)
- [Epic Roadmap](EPICS_ROADMAP.md)
