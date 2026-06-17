from dotenv import load_dotenv
load_dotenv()
# from langchain_groq import ChatGroq/
from langchain_ollama import ChatOllama
# from langchain_openai import ChatOpenAI
# from langchain_google_genai import ChatGoogleGenerativeAI
import time
from groq import RateLimitError


from .prompt import planner_prompt,architect_prompt,coder_system_prompt

from .states import Plan,TaskPlan,CoderState


from langgraph.constants import END
from langgraph.graph import StateGraph
from langchain.agents import create_agent
from .tools import *



# llm = ChatGroq(model="openai/gpt-oss-120b")
llm = ChatOllama(model="llama3.1")
# llm = ChatOpenAI(model="gpt-5.4-mini")

# llm = ChatGoogleGenerativeAI(model='models/gemini-2.5-flash')

def planner_agent(state: dict) -> dict:
    user_prompt= state["user_prompt"]
    state["current_node"] = "planner"
    state["status"] = "planning"
    state["message"] = "Analyzing prompt and creating plan..."
    resp = llm.with_structured_output(Plan).invoke(planner_prompt(user_prompt=user_prompt))
    return {"plan":resp, "current_node": "planner", "status": "planning", "message": "Plan created successfully","job_id":state["job_id"], "progress": 25}

def architect_agent(state: dict) -> dict:
    plan = state["plan"]
    state["current_node"] = "architect"
    state["status"] = "architecting"
    state["message"] = "Drafting architecture and implementation plan..."
    resp = llm.with_structured_output(TaskPlan).invoke(architect_prompt(plan=plan))
    if resp is None:
        raise ValueError("Architect did not return a valid response.")
    
    resp.plan = plan
    return {"task_plan":resp, "current_node": "architect", "status": "architecting", "message": "Architecture designed successfully","job_id":state["job_id"], "progress": 50}

def coder_agent(state: dict) -> dict:
    coder_state = state.get("coder_state")
    if coder_state is None:
        coder_state = CoderState(task_plan=state["task_plan"],current_step_idx=0)
    steps = coder_state.task_plan.implementation_steps
    if coder_state.current_step_idx >= len(steps):
        return {"coder_state":coder_state, "status":"DONE", "current_node": "coder", "message": "All files generated successfully","job_id":state["job_id"], "progress": 100}
    
    current_task = steps[coder_state.current_step_idx]
    total_steps = len(steps)
    progress = 50 + int((coder_state.current_step_idx / total_steps) * 50)
    
    state["current_node"] = "coder"
    state["status"] = "coding"
    state["message"] = f"Writing source code ({coder_state.current_step_idx + 1}/{total_steps}): {current_task.filepath}"
    state["progress"] = progress
    
    existing_content = read_file.run({"path":current_task.filepath,"job_id":state["job_id"]})
    user_prompt = (
        f"Task: {current_task.task_description}\n"
        f"File: {current_task.filepath}\n"
        f"Existing content:\n{existing_content}\n"
         f"job_id:\n{state['job_id']}\n"
        "Use write_file(path,job_id, content) to save your changes."
    )

    system_prompt = coder_system_prompt(job_id=state["job_id"])
    # resp = llm.invoke(system_prompt + user_prompt)
    coder_tools =[read_file,list_files,write_file,get_current_directory]
    react_agent = create_agent(model=llm,tools=coder_tools)
    max_retries = 4
    for attempt in range(max_retries):
        try:
            react_agent.invoke({
                "messages": [
                    {"role":"system","content":system_prompt},
                    {"role":"user","content":user_prompt},
                ]
            })
            break
        except RateLimitError as e:
            if attempt == max_retries - 1:
                raise
            backoff = 1 * (2 ** attempt)
            time.sleep(backoff)
    coder_state.current_step_idx += 1
    return {"coder_state": coder_state, "current_node": "coder", "status": "coding", "message": f"Completed: {current_task.filepath}","job_id":state["job_id"], "progress": progress}
    

graph = StateGraph(dict)

graph.add_node("planner",planner_agent)
graph.add_node("architect",architect_agent)
graph.add_node("coder",coder_agent)


graph.add_edge(start_key="planner",end_key="architect")
graph.add_edge(start_key="architect",end_key="coder")


graph.add_conditional_edges(
    source="coder",
    path= lambda s: "END" if s.get("status") == "DONE" else "coder",
    path_map= {"END":END,"coder":"coder"}
)
graph.set_entry_point("planner")

agent = graph.compile()

# user_prompt= "Create a simple calculator web app"

# result = agent.invoke({"user_prompt":user_prompt,"job_id":"1254788512165"})
# print(result)