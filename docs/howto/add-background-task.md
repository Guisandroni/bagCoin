# Background operations

The development stack has no task queue or scheduler. Existing operations run in the backend request flow; do not use the removed worker commands for new tasks.

For a new background operation, first establish its reliability and scheduling requirements. See [the development setup](../../README.md#desenvolvimento-local) for the services currently available.
