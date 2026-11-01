# CommerceSense AI v3 — Task Queue Evaluation & Architecture Spike

> **Document:** `docs/TASK_QUEUE_EVALUATION.md`  
> **Status:** Completed Phase 1 Architecture Spike  
> **Date:** October 31, 2026  

---

## 1. Executive Summary

As part of Phase 1 (Free-Only Infrastructure & Data Foundations), CommerceSense AI v3 evaluated background asynchronous task queue mechanisms to support long-running operations:
1. Amazon SP-API asynchronous report generation (1–15 minute wait times)
2. StatsForecast batch model fitting across the catalog
3. GDELT 2.0 and public RSS news syndication polling
4. Automation rule evaluation and Action Center proposal generation

The evaluation assessed **Chancy** (a PostgreSQL-native asynchronous job queue) alongside a **Durable Task Queue** adapter with Valkey / Celery fallback capabilities.

---

## 2. Evaluation Spike Results

The automated evaluation spike (`tasks/evaluation.py`) verified five core architectural invariants:

```
+=================================================================+
|         COMMERCESENSE AI v3 TASK QUEUE EVALUATION REPORT        |
+=================================================================+
| Chancy Library Installed:         YES (v0.26.0)                 |
| Basic Task Enqueue & Execution:   PASS [OK]                     |
| Transient Retry & Backoff:        PASS [OK]                     |
| Max Retries Failure Bound:        PASS [OK]                     |
| Strict Idempotency Guard:         PASS [OK]                     |
| Crash Recovery & Resume:          PASS [OK]                     |
+=================================================================+
| Overall Task Queue Spike Verdict: ALL CHECKS PASSED [READY]     |
+=================================================================+
```

### Detailed Evaluation Invariants

1. **Transient Fault Retries & Exponential Backoff:**
   - Simulated intermittent network failures during upstream data calls.
   - Verified the queue transitions job status through `RETRYING` with progressive backoff delays, executing cleanly on recovery without task starvation.

2. **Terminal Failure Protection:**
   - Tasks encountering unrecoverable errors halt when `attempts > max_retries`.
   - Guaranteed transition to `FAILED` with captured stack trace, preventing infinite retry loops.

3. **Strict Idempotency Enforcement:**
   - Tasks submitted with duplicate `idempotency_key` identifiers or identical payload hashes are deduplicated.
   - Multiple identical submissions return the existing job reference, preventing duplicate purchase order generation or duplicate SP-API report requests.

4. **Crash Resilience & State Recovery:**
   - Verified that when worker processes terminate abruptly mid-queue, serialized job state (persisted in PostgreSQL / SQLite) is safely restored by subsequent worker instances.
   - Zero job loss; pending tasks execute to completion upon restart.

5. **Chancy Compatibility:**
   - Verified `chancy` v0.26.0 installs cleanly on Python 3.10 and Python 3.13.
   - Native integration with PostgreSQL and `psycopg` pool provides zero-broker queue operations directly within PostgreSQL 16.
   - Automatic fallback to `DurableTaskQueue` ensures local/demo development operates with zero Docker dependencies.

---

## 3. Recommended Production Topology

- **Production / Staging:** PostgreSQL 16+ as primary relational store and Chancy job table store.
- **Local / Demo / Pytest:** In-Memory / SQLite durable queue requiring zero external daemons.
- **Worker Process:** `worker/run_worker.py` polling for background tasks.
