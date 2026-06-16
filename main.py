import asyncio
import uuid
import json
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from .agent.graph import agent
app = FastAPI()

jobs = {}

class PromptRequest(BaseModel):
    prompt: str

async def generate_source_code(job_id:str,prompt:str):
    try:
        jobs[job_id] = {"status": "processing", "message": "Starting generation process...", "progress": 0}
        
        # Invoke the agent and capture the full state with status updates
        for result in agent.stream({"user_prompt": prompt,"job_id":job_id}):
        
            print(result)
            # Extract status information from the result
            current_node = result.get("current_node", "unknown")
            message = result.get("message", "Processing...")
            progress = result.get("progress", 50)
            
            jobs[job_id] = {
                "status": "processing",
                "message": message,
                "current_node": current_node,
                "progress": progress
            }
            
            # If the coder agent is done, mark as completed
            if result.get("status") == "DONE":
                jobs[job_id] = {
                    "status": "completed",
                    "message": "Code generation completed successfully!",
                    "current_node": "coder",
                    "progress": 100,
                    "download_url": f"/download/{job_id}"
                }
            else:
                # If still processing, continue polling or waiting
                jobs[job_id] = {
                    "status": "processing",
                    "message": message,
                    "current_node": current_node,
                    "progress": progress
                }
    except Exception as e:
        jobs[job_id] = {
            "status": "failed",
            "message": f"Error during generation: {str(e)}",
            "progress": 0
        }


@app.post("/generate")
async def start_generation(request: PromptRequest,background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())

    jobs[job_id]={"status":"queued","message":"Job added to queue"}

    background_tasks.add_task(generate_source_code,job_id,request.prompt)
    return {"job_id":job_id}



@app.get("/stream/{job_id}")
async def stream_status(job_id:str):
    async def event_generator():
        while True:
            job = jobs.get(job_id)
            if not job:
                yield {"data":json.dumps({"error":"Job not found"})}
                break
            yield {"data":json.dumps(job)}
            asyncio.sleep(1)
            if job["status"] == "completed":
                yield {"data":json.dumps({"error":"Job not found"})}
                break

    return EventSourceResponse(event_generator())


@app.get("/download/{job_id}")
async def download_file(job_id:str):
    """ Standard HTTP endpoint to serve the binary file."""
    file_path = f"/generated_code/{job_id}.zip"
    return FileResponse(path=file_path,filename="your_project.zip",media_type="application/zip")

