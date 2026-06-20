import json
import logging
import asyncio
import redis
from celery_app import celery

import threading
from celery.contrib.abortable import AbortableTask
from agent.graph import build_agent
import zipfile
import os
from cancellation import JobCancelledError

import ctypes
from agent.tools import PROJECT_ROOT
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(name)s] - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Use synchronous Redis for Celery task compatibility
REDIS_URL = os.getenv("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
r = redis.Redis.from_url(REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=5,
    socket_timeout=5,
)

def update_job_state_sync(job_id: str, state: dict):
    """Synchronously update job state in Redis (for Celery tasks)."""
    try:
        r.setex(f"job:{job_id}", 3600, json.dumps(state))
        logger.info(f"[Redis] Updated job:{job_id} - Status: {state.get('status')}, Progress: {state.get('progress')}%")
    except Exception as e:
        logger.error(f"[Redis] Failed to update job:{job_id} - {e}")
        raise

@celery.task(name="tasks.generate_source_code_task", bind=True, acks_late=True)
def generate_source_code_task(self, job_id: str, prompt: str):
    try:
        update_job_state_sync(job_id=job_id, state={
            "status": "processing",
            "message": "Starting generation process...",
            "progress": 0,
            "task_id": self.request.id,
        })

        agent = build_agent(job_id=job_id)  # your graph with cancellable_node wrappers
        result_count = 0

        for result in agent.stream({"user_prompt": prompt, "job_id": job_id}):
            result_count += 1
            try:
                value = dict(list(result.values())[0])
                current_node = value.get("current_node", "unknown")
                message     = value.get("message", "Processing...")
                progress    = value.get("progress", 50)
                status      = value.get("status", "processing")

                logger.info(f"[AGENT] Node: {current_node} | Progress: {progress}% | Status: {status}")

                update_job_state_sync(job_id=job_id, state={
                    "status": "processing",
                    "message": message,
                    "current_node": current_node,
                    "progress": progress,
                    "task_id": self.request.id,
                })

                if status == "DONE":
                    break

            except JobCancelledError:
                raise  # Don't swallow it in the inner except

            except Exception as e:
                logger.error(f"[TASK] Error on result #{result_count}: {e}", exc_info=True)
                continue

        # ── Completed ─────────────────────────────────────────────────────────
        update_job_state_sync(job_id=job_id, state={
            "status": "completed",
            "message": "Code generation completed successfully!",
            "progress": 100,
            "download_url": f"/download/{job_id}",
            "task_id": self.request.id,
        })

        source_path = PROJECT_ROOT / job_id
        zip_path = (PROJECT_ROOT / f"{job_id}.zip").resolve()
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(source_path):
                for file in files:
                    full_path = os.path.join(root, file)
                    relative_path = os.path.relpath(full_path, source_path)
                    zipf.write(full_path, relative_path)

        return {"status": "completed", "job_id": job_id, "results": result_count}

    # ── Cancelled ─────────────────────────────────────────────────────────────
    except JobCancelledError:
        logger.warning(f"[TASK CANCELLED] Job {job_id} cancelled mid-node")
        update_job_state_sync(job_id=job_id, state={
            "status": "cancelled",
            "message": "Job cancelled by user.",
            "progress": 0,
            "task_id": self.request.id,
        })
        r.delete(f"cancel:{job_id}")
        return {"status": "cancelled", "job_id": job_id}
    except Exception as exc:
        logger.error("=" * 80, exc_info=False)
        logger.error(f"[TASK ERROR] Job {job_id} failed with exception: {str(exc)}", exc_info=True)
        logger.error("=" * 80, exc_info=False)
        
        try:
            update_job_state_sync(job_id=job_id, state={
                "status": "failed",
                "message": f"Error during generation: {str(exc)}",
                "progress": 0,
                "error": str(exc),
                "task_id": self.request.id
            })
        except Exception as redis_err:
            logger.error(f"[TASK] Failed to update error state in Redis: {redis_err}")
        
        raise
    
