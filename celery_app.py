import os
import logging
from dotenv import load_dotenv
from celery import Celery

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)

logger.info(f"Celery Broker URL: {REDIS_URL}")
logger.info(f"Celery Result Backend: {RESULT_BACKEND}")

celery = Celery(
    "code_buddy",
    broker=REDIS_URL,
    backend=RESULT_BACKEND,
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_send_sent_event=True,
    # Windows compatibility: Use 'solo' pool (no forking)
    worker_pool="solo",
    # Ensure Celery imports the tasks module (avoids circular imports)
    imports=["tasks"],
)

logger.info("Celery configured; tasks will be imported by worker")
