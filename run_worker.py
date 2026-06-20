#!/usr/bin/env python
"""
Run Celery worker with correct module path.
Windows-compatible version using 'solo' pool.
Usage: python run_worker.py
"""
import os
import sys
from pathlib import Path

# Ensure project root is in Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

if __name__ == "__main__":
    from celery_app import celery
    
    try:
        # Use solo pool - no forking, runs in main process
        # This is the only reliable way to run Celery on Windows
        worker = celery.Worker(
            queues=['celery'],
            loglevel='info',
            pool='solo',  # Windows-compatible
        )
        worker.start()
    except KeyboardInterrupt:
        print("\n\n👋 Worker stopped")
    except Exception as e:
        print(f"\n❌ Error starting worker: {e}")
        sys.exit(1)
