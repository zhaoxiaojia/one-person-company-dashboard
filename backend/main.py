import asyncio
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from db.database import init_db
from services.crew_config_service import CrewConfigService
from services.runner_service import RunnerService
from settings import CREW_PROJECT_PATH, DB_PATH


app = FastAPI(title="One Person Company Dashboard")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

config_service = CrewConfigService(CREW_PROJECT_PATH)
runner_service = RunnerService(CREW_PROJECT_PATH, DB_PATH)


class InputsPayload(BaseModel):
    inputs: dict[str, Any]


class AgentPayload(BaseModel):
    content: dict[str, Any]


class TasksPayload(BaseModel):
    tasks: list[dict[str, Any]]


class ModelPayload(BaseModel):
    llm: str


@app.on_event("startup")
def startup() -> None:
    init_db(DB_PATH)


@app.get("/api/crew/summary")
def crew_summary() -> dict[str, Any]:
    summary = config_service.get_summary()
    summary["latest_run"] = runner_service.list_runs()[0] if runner_service.list_runs() else None
    return summary


@app.get("/api/agents")
def agents() -> list[dict[str, Any]]:
    return config_service.list_agents()


@app.get("/api/agents/{filename}")
def agent_detail(filename: str) -> dict[str, Any]:
    try:
        return config_service.get_agent(filename)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.put("/api/agents/{filename}")
def save_agent(filename: str, payload: AgentPayload) -> dict[str, Any]:
    try:
        return config_service.save_agent(filename, payload.content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/api/agents/{filename}")
def delete_agent(filename: str) -> dict[str, str]:
    try:
        config_service.delete_agent(filename)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "deleted"}


@app.get("/api/tasks")
def tasks() -> list[dict[str, Any]]:
    return config_service.list_tasks()


@app.put("/api/tasks")
def save_tasks(payload: TasksPayload) -> list[dict[str, Any]]:
    return config_service.save_tasks(payload.tasks)


@app.get("/api/crew/config")
def crew_config() -> dict[str, Any]:
    return config_service.get_config()


@app.patch("/api/crew/inputs")
def update_inputs(payload: InputsPayload) -> dict[str, Any]:
    return config_service.update_inputs(payload.inputs)


@app.get("/api/models/config")
def model_config() -> dict[str, Any]:
    return config_service.get_model_config()


@app.patch("/api/models/agents")
def update_models(payload: ModelPayload) -> list[dict[str, Any]]:
    return config_service.update_agent_models(payload.llm)


@app.get("/api/outputs")
def outputs() -> list[dict[str, Any]]:
    return config_service.list_outputs()


@app.get("/api/outputs/content")
def output_content(path: str) -> dict[str, Any]:
    try:
        return config_service.read_output(path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/runs")
async def create_run() -> dict[str, Any]:
    try:
        run_id = runner_service.create_run()
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    asyncio.create_task(runner_service.run_crew(run_id))
    return {"id": run_id, "status": "running"}


@app.get("/api/runs")
def runs() -> list[dict[str, Any]]:
    return runner_service.list_runs()


@app.get("/api/runs/{run_id}")
def run_detail(run_id: int) -> dict[str, Any]:
    run = runner_service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    return run


@app.websocket("/ws/runs/{run_id}/logs")
async def run_logs(websocket: WebSocket, run_id: int) -> None:
    await websocket.accept()
    existing = runner_service.get_run(run_id)
    if existing and existing.get("log_text"):
        await websocket.send_text(existing["log_text"])
    queue = runner_service.subscribe(run_id)
    try:
        while True:
            message = await queue.get()
            await websocket.send_text(message)
    except WebSocketDisconnect:
        runner_service.unsubscribe(run_id, queue)
