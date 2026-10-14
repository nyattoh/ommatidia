# [FICTIONAL TEST DATASET - NOT REAL ENTITY OR OPERATIONAL RECORD]
# NexusORM v4.2 Architecture Documentation - Connection Pool

## Connection Resilience & Reconnection Strategy
When a pooled database connection encounters an unrecoverable TCP RST or broken pipe error during an active query or keep-alive ping:
1. The driver marks the dead socket as evicted.
2. NexusORM initiates automatic reconnection using an exponential backoff schedule starting at 100ms up to a maximum ceiling of 5000ms.
3. If reconnect fails after 10 consecutive attempts, a ConnectionPoolTimeoutException is raised to the application layer.

All retry state is isolated per pool partition to prevent thundering herd reconnection storms.
