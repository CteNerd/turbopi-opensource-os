# TurboPi – Open, Safe, UI-Driven Robotics Platform

TurboPi is an open, modular robotics platform designed for Raspberry Pi–based robots.
It prioritizes safety, transparency, and controlled updates while enabling teleoperation,
autonomy, vision, and voice interaction.

## Core Principles

- Safety first (E-Stop always wins)
- Manual control before autonomy
- Explicit promotion of releases (no forced updates)
- UI-managed configuration and updates
- Cloud-assisted intelligence, local real-time control
- Open source–friendly with supply-chain protections

## High-Level Capabilities

- Web UI for control, video, configuration, and updates
- Emergency Access Point + Home Wi-Fi
- Signed, promoted releases with rollback
- Object detection and follow behaviors
- Voice interaction with wake-word support ("Jarvis")
- Extensible architecture with a future ROS 2 migration path

See [ARCHITECTURE.md](./ARCHITECTURE.md) for system design.

For ROS 2 adoption sequencing and boundaries, see [ROS2_MIGRATION_RUNWAY.md](./ROS2_MIGRATION_RUNWAY.md).

For a practical hardware readiness status, missing data checklist, and staged integration plan for the Hiwonder TurboPi kit, see [HIWONDER_TURBOPI_READINESS_PLAN.md](./HIWONDER_TURBOPI_READINESS_PLAN.md).
