# System Architecture

## High-Level Overview

The system is composed of loosely coupled services running on the robot:

- UI (browser-based)
- API Backend
- Hardware Abstraction Layer (HAL)
- Control & Safety Engine
- Vision Pipeline
- Voice Pipeline
- Updater Service

Real-time control and safety logic always execute locally.
Cloud services are used only for non-blocking intelligence (STT, TTS, conversation).

## Trust Boundaries

- Browser UI is untrusted
- API backend enforces all permissions
- No cloud service may directly issue motor commands
- Voice commands must pass intent parsing and safety arbitration

## Data Flow (Simplified)

UI → API → Control Arbiter → HAL → Motors  
Camera → Vision → Behavior → Control Arbiter  
Mic → Wake Word → STT → Intent Parser → Control Arbiter  

## Update Flow

UI → Updater API → Updater Service → Signed Release → Health Check → Activate/Rollback
