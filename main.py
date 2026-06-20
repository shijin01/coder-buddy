import asyncio
import uuid
import json
import logging
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from fastapi.sse import EventSourceResponse,ServerSentEvent
from tasks import generate_source_code_task
from pathlib import Path
import shutil

from celery_app import celery

from celery_app import celery
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from agent.tools import PROJECT_ROOT
import zipfile
import os
app = FastAPI()

redis_pool = redis.ConnectionPool.from_url(
    "redis://127.0.0.1:6379/0",
    decode_responses=True,
    socket_connect_timeout=5,
    socket_timeout=5,
)
redis_client = redis.Redis(connection_pool=redis_pool)


@app.on_event("startup")
async def startup_check_redis():
    try:
        await redis_client.ping()
    except redis.exceptions.RedisError as exc:
        raise RuntimeError(f"Redis startup check failed: {exc}") from exc


class PromptRequest(BaseModel):
    prompt: str

async def update_job_state(job_id:str,state:dict):
    await redis_client.setex(f"job:{job_id}",3600,json.dumps(state))


@app.post("/generate")
async def start_generation(request: PromptRequest):
    job_id = str(uuid.uuid4())
    await update_job_state(job_id=job_id,state={"status":"queued","message":"Job added to queue"})
    generate_source_code_task.apply_async(
        args=[job_id, request.prompt], 
        task_id=job_id
    )
    return {"job_id":job_id}

@app.post("/api/v1/cancel/{job_id}")
async def cancel_job(job_id: str):
   
    await redis_client.set(f"cancel:{job_id}", "1", ex=3600)
    # Update the Redis state so the SSE stream knows to close
    await redis_client.setex(
        f"job:{job_id}",
        3600,
        json.dumps({"status": "cancelled", "message": "Job was cancelled by the user."})
    )
    
    return {"message": "Job cancelled successfully."}

@app.get("/stream/{job_id}",response_class=EventSourceResponse)
async def stream_status(job_id:str):
    prevstatus = {}
    while True:
        try:
            raw_job = await redis_client.getex(f"job:{job_id}")
        except redis.exceptions.RedisError as exc:
            yield ServerSentEvent(data={"error": "Redis unavailable", "detail": str(exc)})
            break

        if not raw_job:
            yield ServerSentEvent(data={"error":"Job not found"})
            break

        try:
            job = json.loads(raw_job)
        except (TypeError, json.JSONDecodeError) as exc:
            yield ServerSentEvent(data={"error": "Invalid job payload", "detail": str(exc)})
            break

        if job.get("status") == "failed":
            yield ServerSentEvent(data=job)
            break

        if job.get("status") == "cancelled":
            yield ServerSentEvent(data=job)
            break

        if prevstatus != job:
            prevstatus = job
            yield ServerSentEvent(data=job)

        if job.get("status") == "completed":
            yield ServerSentEvent(data="Completed you can download it using the job_id")
            break

        await asyncio.sleep(0.1)



@app.get("/download/{job_id}")
async def download_file(job_id:str):
    """ Standard HTTP endpoint to serve the binary file."""
    file_path = f"/generated_code/{job_id}.zip"
    source_path =PROJECT_ROOT / job_id
    zipfilename = f"{job_id}.zip"
    zip_path =  (PROJECT_ROOT/zipfilename).resolve()
    if zip_path.exists():
        return FileResponse(path=zip_path.absolute().as_posix(),filename="your_project.zip",media_type="application/zip")
    else:
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
        if zip_path.exists():
            # try:
            #     shutil.rmtree(source_path.absolute().as_posix())
            # except:
            #     print("Cannot delete directory.")
            return FileResponse(path=file_path,filename="your_project.zip",media_type="application/zip")
    return {"message":"Something went wrong. Cannot return zip file."}
        

