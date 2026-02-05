# google-media-backup Roadmap

**Version:** 1.0.0
**Last Updated:** February 03, 2026

---

## Vision

macOS menu bar app that downloads media from Google Drive/Photos and transcribes videos locally with Whisper.

## Current State

- **Status**: Active macOS app; feature set documented
- **Transcription**: Local whisper-cpp pipeline

## Phase Overview

- **Phase 1 (Core)**: Foundation and MVP scope
- **Phase 2 (Expansion)**: Feature depth and integrations
- **Phase 3 (Scale/Polish)**: Reliability, automation, and UX polish

## Phase 1: Core

### Google Drive Integration

- Download videos/docs
- Handle Google Docs export

### Google Photos Integration

- Download videos
- Album support

### Local Transcription

- whisper-cpp pipeline
- Model selection

### Menu Bar UI

- Background status
- Quick actions

## Phase 2: Expansion

### State Management

- Resume downloads
- Track status per file

### Auto-Sync

- Run on launch
- Configurable schedule

### Auto-Transcribe

- Queue transcriptions
- Progress feedback

## Phase 3: Scale & Polish

### Preferences

- Download filters
- Storage locations

### File Organization

- Drive/Photos folders
- Transcript placement

### Error Handling

- Retry strategy
- Failure reports

## Success Criteria

- All features implemented with tests, lint, typecheck, and build passing
- Documentation updated for any architecture or workflow changes
- No forbidden patterns; follow global standards

## Risks & Dependencies

- External API limits, vendor dependencies, or platform constraints
- Cross-platform requirements (Mac/Windows) where applicable
