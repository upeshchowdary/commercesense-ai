"""
test_task_queue.py — Tests for asynchronous task queue, retries, idempotency, and crash recovery.
"""

from __future__ import annotations

import pytest

from tasks.task_queue import DurableTaskQueue, TaskStatus, generate_task_key, task


def test_task_queue_basic_execution():
    """Verifies that a registered task can be enqueued and executed."""
    q = DurableTaskQueue()

    def multiply(x: int, y: int) -> int:
        return x * y

    q.register("multiply", multiply)
    job = q.enqueue("multiply", 6, 7)
    assert job.status == TaskStatus.PENDING

    count = q.run_worker_cycle()
    assert count == 1

    processed_job = q.get_job(job.id)
    assert processed_job is not None
    assert processed_job.status == TaskStatus.COMPLETED
    assert processed_job.result == 42
    assert processed_job.attempts == 1


def test_task_queue_transient_retry():
    """Verifies automatic retries with exponential backoff on transient errors."""
    q = DurableTaskQueue()
    call_log = []

    def flaky_service():
        call_log.append(1)
        if len(call_log) < 3:
            raise ConnectionError("Temporary timeout")
        return "recovered"

    q.register("flaky_service", flaky_service)
    job = q.enqueue("flaky_service", max_retries=4, retry_delay_seconds=0.01)

    # Attempt 1 -> Fails, transitions to RETRYING
    q.run_worker_cycle()
    j = q.get_job(job.id)
    assert j.status == TaskStatus.RETRYING
    assert j.attempts == 1

    # Attempt 2 -> Fails, transitions to RETRYING
    q.run_worker_cycle()
    j = q.get_job(job.id)
    assert j.status == TaskStatus.RETRYING
    assert j.attempts == 2

    # Attempt 3 -> Succeeds, transitions to COMPLETED
    q.run_worker_cycle()
    j = q.get_job(job.id)
    assert j.status == TaskStatus.COMPLETED
    assert j.result == "recovered"
    assert j.attempts == 3


def test_task_queue_max_retries_failure():
    """Verifies that exceeding max_retries marks the job as FAILED."""
    q = DurableTaskQueue()

    def persistent_failure():
        raise RuntimeError("Permanent error")

    q.register("persistent_failure", persistent_failure)
    job = q.enqueue("persistent_failure", max_retries=2, retry_delay_seconds=0.01)

    # 3 total attempts: 1 initial + 2 retries
    q.run_worker_cycle()
    q.run_worker_cycle()
    q.run_worker_cycle()

    j = q.get_job(job.id)
    assert j.status == TaskStatus.FAILED
    assert j.attempts == 3
    assert "Permanent error" in (j.error or "")


def test_task_queue_strict_idempotency():
    """Ensures that enqueuing with the same idempotency key does not duplicate work."""
    q = DurableTaskQueue()
    execution_counter = {"count": 0}

    def critical_payment(account: str, amount: int):
        execution_counter["count"] += 1
        return f"Paid {amount} to {account}"

    q.register("critical_payment", critical_payment)
    key = "tx-2026-10-31-001"

    j1 = q.enqueue("critical_payment", "seller-42", 500, idempotency_key=key)
    j2 = q.enqueue("critical_payment", "seller-42", 500, idempotency_key=key)

    # Same job reference must be returned
    assert j1.id == j2.id

    # Execute
    q.run_worker_cycle()
    assert execution_counter["count"] == 1
    assert j1.status == TaskStatus.COMPLETED

    # Subsequent enqueue with same key after completion still returns existing completed job
    j3 = q.enqueue("critical_payment", "seller-42", 500, idempotency_key=key)
    assert j3.id == j1.id
    assert j3.status == TaskStatus.COMPLETED


def test_task_queue_restart_recovery():
    """Simulates worker crash, process reboot, and successful resumption of queued work."""
    q1 = DurableTaskQueue()

    def background_worker(value: str) -> str:
        return f"processed: {value}"

    q1.register("background_worker", background_worker)
    job_queued = q1.enqueue("background_worker", "important_report")
    assert job_queued.status == TaskStatus.PENDING

    # Export state to simulate persistent database backing
    saved_state = q1.export_state()

    # Create new queue instance simulating worker process reboot
    q2 = DurableTaskQueue()
    q2.register("background_worker", background_worker)
    q2.import_state(saved_state)

    # Worker picks up job after restart
    assert q2.get_job(job_queued.id).status == TaskStatus.PENDING
    q2.run_worker_cycle()

    completed = q2.get_job(job_queued.id)
    assert completed.status == TaskStatus.COMPLETED
    assert completed.result == "processed: important_report"


def test_task_decorator_integration():
    """Verifies the @task decorator helper."""
    q = DurableTaskQueue()

    @task(name="decorated_calc", queue=q)
    def my_calc(a: int, b: int) -> int:
        return a + b

    job = my_calc.enqueue(10, 20)
    assert job.status == TaskStatus.PENDING

    q.run_worker_cycle()
    assert job.status == TaskStatus.COMPLETED
    assert job.result == 30


def test_task_queue_thread_concurrency():
    """Verifies that concurrent enqueues across multiple threads operate safely without race conditions."""
    import concurrent.futures

    q = DurableTaskQueue()

    def process_item(item_id: int):
        return f"done_{item_id}"

    q.register("process_item", process_item)

    def worker_thread(thread_idx: int):
        for i in range(25):
            q.enqueue("process_item", thread_idx * 1000 + i)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(worker_thread, idx) for idx in range(5)]
        for f in futures:
            f.result()

    jobs = q.list_jobs()
    assert len(jobs) == 125
    assert len(set(j.id for j in jobs)) == 125
