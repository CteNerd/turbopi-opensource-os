# Session Handoff - Robot Access (2026-04-14)

## Current status
- You successfully identified the active robot host as 192.168.1.221.
- SSH on 192.168.1.221 is reachable and reports OpenSSH_9.2p1 (Debian).
- Auth methods on 192.168.1.221 allow both publickey and password.
- You are now able to proceed with setup over SSH.

## Important findings from this session
- 192.168.1.221: active robot host (OpenSSH_9.2p1).
- 192.168.1.116: OpenSSH_7.6, key-only auth (likely prior target/alternate host state).
- 192.168.1.67, 192.168.1.166, 192.168.1.253: Dropbear-based appliance/router-like endpoints, not the main robot shell target for this flow.
- 192.168.149.1 was not reachable during this phase.

## SSH commands that worked for diagnosis
- ping -c 1 192.168.1.221
- nc -v -w 2 192.168.1.221 22
- ssh pi@192.168.1.221

## Next setup steps on robot (from repo root)
1. Home Wi-Fi setup:
   - cd /home/pi/turbopi-opensource-os/system
   - sudo ./install-home-wifi.sh
2. Runtime service install:
   - sudo ./install-services.sh
3. Start runtime services now:
   - sudo systemctl start turbopi-api.service turbopi-ui.service turbopi-updater.service
4. Verify:
   - sudo systemctl status turbopi-home-wifi.service --no-pager
   - sudo systemctl status turbopi-api.service turbopi-ui.service turbopi-updater.service --no-pager
   - ip -4 addr show wlan0
   - ip -4 addr show wlan1

## Optional SSH hardening / lockout prevention
- Ensure pi password is known:
  - sudo passwd pi
- Ensure password auth is enabled (if desired for recovery):
  - sudo sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config
  - sudo systemctl restart ssh

## SCP this handoff file to robot
From your Mac, run:
- scp docs/copilot/SESSION_HANDOFF_2026-04-14_ROBOT_ACCESS.md pi@192.168.1.221:/home/pi/

Then on robot:
- cat /home/pi/SESSION_HANDOFF_2026-04-14_ROBOT_ACCESS.md

## Resume checklist later
- Confirm robot IP still 192.168.1.221
- SSH in as pi
- Run install-home-wifi.sh
- Run install-services.sh
- Verify services and interface IPs
- Open UI on port 8081 from same network
