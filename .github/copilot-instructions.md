# Gosimine Copilot Instructions

## Working Method

1. Research first. Inspect the relevant area and explain the findings.
2. Agree once. Agree on the approach and boundaries for the feature.
3. Implement fully. Make the needed changes and test them, stopping only if the original decision needs to change.

Do not require approval for each individual action within an agreed work package. Pause for renewed agreement when new evidence materially changes the intended behavior, data compatibility, architecture, dependencies, risk, or delivery scope.

## Communication

- Keep updates and results raw and concise: findings, decision, action, and result.
- Avoid unnecessary explanation, summaries, or broad speculative proposals.
- When clarification is needed, use numbered questions.

## Session Startup

- At the start of feature work, read `SYSTEM_GOAL.md` and `DATABASE_API.md`.
- Summarize the current agreed architecture before proposing changes.
- Before changing project rules, read this file.

## Project Conventions

- Gosimine is a local-first PySide6 desktop application backed by SQLite.
- Before changing persistence, read `SYSTEM_GOAL.md` and `DATABASE_API.md`.
- Keep persistence and data models in `src/gosimine/database.py`; keep Qt widgets and user interactions in `src/gosimine/app.py`.
- Treat `data/gosimine.sqlite3` as user data. Never delete, reset, or rewrite it during development or tests.
- Use parameterized SQLite queries, explicit commits for writes, and typed dataclasses for persisted entities.
- Make schema changes backward-compatible and cover database behavior with temporary-database tests in `tests/`.
- Preserve existing user changes and avoid unrelated refactors.
- Do not commit, create branches, install dependencies, or change project tooling unless the user explicitly approves it.
