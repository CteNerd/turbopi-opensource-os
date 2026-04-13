# TurboPi Service Implementations

This directory contains the runtime service implementations for TurboPi OpenSource OS.

## Services

### API Backend (`src/api/`)
- **Purpose**: REST API backend for robot control and status
- **Port**: 8080 (configurable via API_PORT)
- **Key Endpoints**:
  - `GET /health` - System health status
- **Service**: `turbopi-api.service`

### Web UI (`src/ui/`)
- **Purpose**: Browser-based control interface
- **Port**: 8081 (configurable via UI_PORT)
- **Key Features**:
  - Status dashboard
  - Configuration interface
- **Service**: `turbopi-ui.service`

### Updater (`src/updater/`)
- **Purpose**: Manages software updates and releases
- **Mode**: Background service
- **Key Features**:
  - Update checking
  - Atomic installations
  - Rollback support
- **Service**: `turbopi-updater.service`

## Development Status

**Current Implementation**: Skeleton services providing basic functionality

These are minimal implementations that:
- ✅ Start correctly via systemd
- ✅ Load configuration from `/etc/turbopi/config.env`
- ✅ Provide structured logging with Python's `logging` module
- ✅ Support graceful shutdown

**Logging Standards**:
All services implement consistent logging with:
- Python's `logging` module with `basicConfig()` configuration
- Format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- LOG_LEVEL environment variable support (default: INFO)
- Output to stdout for systemd journal integration
- Appropriate log levels (info, error, warning) for different operations

**Future Enhancements** (subsequent EPICs):
- Full API implementation per OpenAPI spec
- Complete UI with teleoperation controls
- Full updater with release promotion
- Hardware abstraction layer integration (initial HAL primitives now in `src/hal/`)
- Safety system integration

## Installation

Install the runtime services:

```bash
cd system
sudo ./install-services.sh
```

This will:
1. Create `/opt/turbopi/current/` directory structure
2. Install service binaries
3. Create `/etc/turbopi/config.env` configuration
4. Install systemd service files
5. Enable services for automatic startup

## Configuration

All services load configuration from `/etc/turbopi/config.env` via systemd's `EnvironmentFile` directive.

Key configuration variables:
- `ROBOT_NAME` - Robot identifier
- `API_HOST`, `API_PORT` - API service binding
- `UI_HOST`, `UI_PORT` - UI service binding
- `AUTO_UPDATE` - Enable/disable automatic updates
- See `system/config.env.example` for complete list

## Testing

Test the installed services:

```bash
cd system
sudo ./test-services.sh
```

This verifies:
- Configuration file exists
- Services are installed and enabled
- Services can start successfully
- Health endpoint responds correctly

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

### Check Status
```bash
sudo systemctl status turbopi-api.service
sudo systemctl status turbopi-ui.service
sudo systemctl status turbopi-updater.service
```

### View Logs
```bash
sudo journalctl -u turbopi-api.service -f
sudo journalctl -u turbopi-ui.service -f
sudo journalctl -u turbopi-updater.service -f
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  systemd (init)                     │
│  Manages service lifecycle and dependencies         │
└──────────────┬────────────────────────────┬─────────┘
               │                            │
       ┌───────▼──────────┐        ┌────────▼─────────┐
       │  turbopi-api     │        │  turbopi-ui      │
       │  Port: 8080      │        │  Port: 8081      │
       │  User: turbopi   │        │  User: turbopi   │
       └──────────────────┘        └──────────────────┘
               │                            │
               └─────────┬──────────────────┘
                         │
                  ┌──────▼─────────┐
                  │ turbopi-updater│
                  │ User: root     │
                  │ (needs perms)  │
                  └────────────────┘
                         │
              ┌──────────▼──────────────┐
              │  /etc/turbopi/config.env│
              │  Shared configuration   │
              └─────────────────────────┘
```

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

/var/log/turbopi/              # Service logs (via journald)

/etc/systemd/system/           # Systemd service files
├── turbopi-api.service
├── turbopi-ui.service
└── turbopi-updater.service
```

## Security Considerations

- Services run as unprivileged `turbopi` user (except updater which needs root)
- Security hardening enabled in systemd service files:
  - `NoNewPrivileges=true`
  - `PrivateTmp=true`
  - `ProtectSystem=strict`
  - `ProtectHome=true`
- Configuration file contains no secrets in this skeleton
- Future: API keys and credentials will be stored securely

## Dependencies

- Python 3 (available by default on Raspberry Pi OS)
- systemd (standard on modern Linux)
- No additional Python packages required for skeleton services

## Development

### Testing Locally

You can run services directly for development:

```bash
# Set up environment
export ROBOT_NAME="TestBot"
export API_PORT=8080
export UI_PORT=8081

# Run API service
python3 src/api/main.py

# Run UI service (in another terminal)
python3 src/ui/main.py

# Run updater service (in another terminal)
python3 src/updater/main.py
```

### Adding Features

When implementing features in future EPICs:
1. Add code to the appropriate service (`src/api/`, `src/ui/`, `src/updater/`)
2. Update `system/config.env.example` if new config variables are needed
3. Test locally before installing via systemd
4. Update service file if new dependencies or permissions are needed
5. Update this README and relevant documentation

## References

- [System Configuration](../system/README.md)
- [API Specification](../docs/api/OPENAPI.yaml)
- [Architecture Overview](../docs/init/ARCHITECTURE.md)
- [Configuration Schema](../docs/config/SCHEMA.md)
