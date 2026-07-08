
# cancellation.py
import redis
import os
from langchain_core.callbacks.base import BaseCallbackHandler

REDIS_URL = os.getenv("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

def is_cancelled(job_id: str) -> bool:
    return r.exists(f"cancel:{job_id}") == 1

class JobCancelledError(Exception):
    pass

class CancellationCallback(BaseCallbackHandler):
    raise_error = True  # Force LangChain to propagate exceptions instead of warning

    def __init__(self, job_id: str):
        self.job_id = job_id

    def _check(self):
        if is_cancelled(self.job_id):
            raise JobCancelledError(f"Job {self.job_id} cancelled.")

    def on_llm_new_token(self, token: str, **kwargs): self._check()
    def on_llm_start(self, *args, **kwargs):          self._check()
    def on_tool_start(self, *args, **kwargs):         self._check()
    def on_agent_action(self, *args, **kwargs):       self._check()
    def on_chain_start(self, *args, **kwargs):        self._check()