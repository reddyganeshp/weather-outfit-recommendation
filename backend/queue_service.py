"""
Queue Service
Simulates AWS SQS (or any message queue) for async outfit recommendation jobs.
In production this is replaced by boto3 SQS calls — the interface stays identical.
"""

from __future__ import annotations
import threading
import time
import logging
from datetime import datetime
from outfit_engine import OutfitEngine

logger = logging.getLogger(__name__)
_engine = OutfitEngine()


class QueueService:
    """
    Thread-safe in-memory job queue.
    Production deployment: swap _queue for boto3 SQS and _results for DynamoDB/Redis.
    """

    def __init__(self):
        self._queue: list[dict] = []
        self._results: dict[str, dict] = {}
        self._lock = threading.Lock()
        self._worker = threading.Thread(target=self._process_loop, daemon=True)
        self._worker.start()
        logger.info("QueueService initialised (in-memory mode)")

    def enqueue(self, payload: dict) -> str:
        with self._lock:
            self._queue.append(payload)
        logger.info("Job %s enqueued", payload.get("job_id"))
        return payload["job_id"]

    def get_result(self, job_id: str) -> dict | None:
        with self._lock:
            return self._results.get(job_id)

    # ── background worker ──

    def _process_loop(self):
        """Continuously process queued jobs."""
        while True:
            job = None
            with self._lock:
                if self._queue:
                    job = self._queue.pop(0)
            if job:
                self._process(job)
            else:
                time.sleep(0.2)

    def _process(self, job: dict):
        job_id = job["job_id"]
        logger.info("Processing job %s", job_id)
        try:
            result = _engine.recommend(
                temperature=job["temperature"],
                weather_condition=job["weather_condition"],
                humidity=job.get("humidity", 50),
                wind_speed=job.get("wind_speed", 0),
                occasion=job.get("occasion", "casual"),
                gender=job.get("gender", "unisex"),
                preferred_colors=job.get("preferred_colors", [])
            )
            with self._lock:
                self._results[job_id] = {
                    "status": "complete",
                    "job_id": job_id,
                    "completed_at": datetime.utcnow().isoformat(),
                    "recommendation": result
                }
            logger.info("Job %s complete", job_id)
        except Exception as exc:
            logger.error("Job %s failed: %s", job_id, exc)
            with self._lock:
                self._results[job_id] = {
                    "status": "failed",
                    "job_id": job_id,
                    "error": str(exc)
                }
