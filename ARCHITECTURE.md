# google-media-backup Architecture

**Version:** 1.0.0
**Last Updated:** February 03, 2026

---

## System Overview

macOS menu bar app that downloads media from Google Drive/Photos and transcribes videos locally with Whisper.

## High-Level Diagram

```
Users / Operators
        │
        ▼
google-media-backup Core
        │
        ├── Local State / Data Storage
        └── External Integrations / APIs
        │
        ▼
Outputs (UI, Reports, Exports, Logs)
```

## Technology Stack

- Swift (macOS) UI
- Google APIs
- whisper-cpp
- ffmpeg

## Directory Structure (Top-Level)

```
GoogleMediaBackup/
README.md
ROADMAP.md
```

## Data Flow

1. User initiates action (UI/CLI/task).
2. Core logic processes input, validates rules, and triggers integrations.
3. State is persisted (local files, DB, or external systems).
4. Output is rendered to UI, exported, or logged.

## Security & Quality

- Follow global forbidden/required patterns and lint/typecheck rules
- No hardcoded secrets; use environment variables
- Log errors through approved logger patterns (no console.*)

## Observability

- Structured logs for key workflows
- Health checks for integrations and background tasks
