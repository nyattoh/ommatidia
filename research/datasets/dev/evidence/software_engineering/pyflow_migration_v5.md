# [FICTIONAL TEST DATASET - NOT REAL ENTITY OR OPERATIONAL RECORD]
# PyFlow Release Notes & Migration Guide v5.0

## Breaking Changes in Task Execution (Release Date: 2026-06-01)
Effective PyFlow version 5.0 (released 2026-06), default task execution timeout is 300 seconds; legacy version 4.0 unlimited execution is deprecated and superseded. Workflows requiring longer execution must explicitly set task_timeout_seconds=0.
