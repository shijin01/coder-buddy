from typing import Optional
from pydantic import BaseModel,Field,ConfigDict
class File(BaseModel):
    path:str = Field(
        description="The path to the file to be created or modified"
    )
    purpose:str = Field(
        description="The purpose of the file. Eg:- 'main application logic','data processing module', etc."
    )
class Plan(BaseModel):
    name:str = Field(
        description="The name of the app to be built"
    )
    description:str = Field(
        description="A oneline description of the app to be built, e.g. A web application"
    )
    techstach: str = Field(
        description="The tech stack to be used for the app. e.g. 'python', 'javascript'"
    )
    features:list[str] = Field(
        description="A list of features that the app should have, eg:'User authentication'"
    )
    files: list[File] = Field(
        description= "" \
        "A list of files to be created, each with a 'path' and 'purpose'"
    )

class ImplementationTask(BaseModel):
    filepath: str = Field(description="The path to the file to be modified")
    task_description: str = Field(description="A detailed description of the task to be performed on the file, e.g. 'add user authentication', 'implement data processing logic', etc.")

class TaskPlan(BaseModel):
    implementation_steps: list[ImplementationTask] = Field(description="A list of steps to be taken to implement the task")
    model_config = ConfigDict(extra="allow")
 
class CoderState(BaseModel):
    task_plan: TaskPlan = Field(description=" The plan for the task to be implemented")
    current_step_idx:int  = Field(0,description=" The index of the current step in the implementation steps")
    current_file_content:Optional[str] = Field(default=None, description=" The content of the file currently edited or created.")

class JobStatus(BaseModel):
    status: str = Field(description="Current job status: queued, planning, architecting, coding, completed, failed")
    message: str = Field(description="Detailed message about current job status")
    current_node: Optional[str] = Field(default=None, description="The current node being processed")
    progress: Optional[int] = Field(default=0, description="Progress percentage (0-100)")
    
