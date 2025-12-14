# Setup & Configuration

## First Boot Experience

1. Bot boots into AP mode
2. User connects to Setup UI
3. Wizard collects:
   - Wi-Fi credentials
   - API keys
   - Wake word
4. Config written to `/etc/turbopi/config.env`
5. Services restarted automatically

## Configuration Rules

- Secrets never stored in repo
- Secrets never exposed to browser JS
- All services load config via systemd
