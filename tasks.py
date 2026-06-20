import json
import logging
import asyncio
import redis
from celery_app import celery
from agent.graph import agent
import zipfile
import os
import shutil
from agent.tools import PROJECT_ROOT
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(name)s] - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Use synchronous Redis for Celery task compatibility
redis_sync_client = redis.Redis(
    host="127.0.0.1",
    port=6379,
    db=0,
    decode_responses=True,
    socket_connect_timeout=5,
    socket_timeout=5,
)

def update_job_state_sync(job_id: str, state: dict):
    """Synchronously update job state in Redis (for Celery tasks)."""
    try:
        redis_sync_client.setex(f"job:{job_id}", 3600, json.dumps(state))
        logger.info(f"[Redis] Updated job:{job_id} - Status: {state.get('status')}, Progress: {state.get('progress')}%")
    except Exception as e:
        logger.error(f"[Redis] Failed to update job:{job_id} - {e}")
        raise

@celery.task(name="tasks.generate_source_code_task", bind=True)
def generate_source_code_task(self, job_id: str, prompt: str):
    """Celery task that runs code generation via the agent."""
    logger.info("=" * 80)
    logger.info(f"[TASK START] Task ID: {self.request.id} | Job ID: {job_id}")
    logger.info(f"[TASK START] Prompt: {prompt[:50]}...")
    logger.info("=" * 80)
    
    try:
        # Mark as processing
        logger.info(f"[TASK] Setting job to 'processing' state")
        update_job_state_sync(job_id=job_id, state={
            "status": "processing", 
            "message": "Starting generation process...", 
            "progress": 0,
            "task_id": self.request.id,
            "started_at": str(asyncio.get_event_loop().time()) if asyncio else "unknown"
        })
        
        # Run agent
        logger.info(f"[TASK] Starting agent.stream() for job_id: {job_id}")
        result_count = 0
        
        for result in agent.stream({"user_prompt": prompt, "job_id": job_id}):
            result_count += 1
            logger.debug(f"[TASK] Agent stream result #{result_count}: {result}")
            
            try:
                value = dict(list(result.values())[0])
                current_node = value.get("current_node", "unknown")
                message = value.get("message", "Processing...")
                progress = value.get("progress", 50)
                status = value.get("status", "processing")
                
                logger.info(f"[AGENT] Node: {current_node} | Progress: {progress}% | Status: {status}")
                
                # Update Redis
                update_job_state_sync(job_id=job_id, state={
                    "status": "processing",
                    "message": message,
                    "current_node": current_node,
                    "progress": progress,
                    "task_id": self.request.id
                })
                
                # Check if done
                if status == "DONE":
                    logger.info(f"[AGENT] Agent reported DONE status")
                    break
                    
            except Exception as e:
                logger.error(f"[TASK] Error processing result #{result_count}: {e}", exc_info=True)
                continue
        
        logger.info(f"[TASK] Agent stream completed. Processed {result_count} results")
        
        # Mark as completed
        logger.info(f"[TASK] Marking job as completed")
        update_job_state_sync(job_id=job_id, state={
            "status": "completed",
            "message": "Code generation completed successfully!",
            "current_node": "coder",
            "progress": 100,
            "download_url": f"/download/{job_id}",
            "task_id": self.request.id
        })
        
        logger.info("=" * 80)
        logger.info(f"[TASK SUCCESS] Job {job_id} completed successfully")
        logger.info("=" * 80)


        source_path =PROJECT_ROOT / job_id
        zipfilename = f"{job_id}.zip"
        zip_path =  (PROJECT_ROOT/zipfilename).resolve()
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(source_path):  #
                for file in files:
                    # Get full path of the file on disk
                    full_path = os.path.join(root, file)  #

                    # Get relative path to maintain the correct internal folder structure
                    relative_path = os.path.relpath(
                        full_path, source_path
                    )  #

                    # Write file to the archive
                    zipf.write(full_path, relative_path)
            zipf.write(source_path, arcname=source_path.name)
        # if zip_path.exists():
        #     try:
        #         shutil.rmtree(source_path.absolute().as_posix())
        #     except:
        #         print("Cannot delete directory.")
        return {"status": "completed", "job_id": job_id, "results": result_count}

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
