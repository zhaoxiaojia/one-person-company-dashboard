import asyncio
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from db.database import init_db
from services.crew_config_service import CrewConfigService
from services.dashboard_config_service import DashboardConfigService
from services.health_service import HealthService
from services.runner_service import RunnerService
from settings import DASHBOARD_CONFIG_PATH, DB_PATH, DEFAULT_CREW_PROJECT_PATH


app = FastAPI(title="One Person Company Dashboard")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

dashboard_config_service = DashboardConfigService(DASHBOARD_CONFIG_PATH, DEFAULT_CREW_PROJECT_PATH)


class Services:
    def __init__(self) -> None:
        self.set_crew_project_path(dashboard_config_service.get_crew_project_path())

    def set_crew_project_path(self, crew_project_path) -> None:
        self.crew_project_path = crew_project_path
        self.config = CrewConfigService(crew_project_path)
        self.health = HealthService(crew_project_path)
        self.runner = RunnerService(crew_project_path, DB_PATH, self.health)


services = Services()


class InputsPayload(BaseModel):
    inputs: dict[str, Any]


class AgentPayload(BaseModel):
    content: dict[str, Any]


class TasksPayload(BaseModel):
    tasks: list[dict[str, Any]]


class ModelPayload(BaseModel):
    llm: str


class SettingsPayload(BaseModel):
    crew_project_path: str


@app.on_event("startup")
def startup() -> None:
    init_db(DB_PATH)


@app.get("/api/crew/summary")
def crew_summary() -> dict[str, Any]:
    summary = services.config.get_summary()
    runs = services.runner.list_runs()
    summary["latest_run"] = runs[0] if runs else None
    return summary


@app.get("/api/agents")
def agents() -> list[dict[str, Any]]:
    return services.config.list_agents()


@app.get("/api/agents/{filename}")
def agent_detail(filename: str) -> dict[str, Any]:
    try:
        return services.config.get_agent(filename)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=f"未找到智能体文件：{filename}") from exc


@app.put("/api/agents/{filename}")
def save_agent(filename: str, payload: AgentPayload) -> dict[str, Any]:
    try:
        return services.config.save_agent(filename, payload.content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"智能体文件名不合法：{exc}") from exc


@app.delete("/api/agents/{filename}")
def delete_agent(filename: str) -> dict[str, str]:
    try:
        services.config.delete_agent(filename)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"未找到智能体文件：{filename}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"智能体文件名不合法：{exc}") from exc
    return {"status": "已删除"}


@app.get("/api/tasks")
def tasks() -> list[dict[str, Any]]:
    return services.config.list_tasks()


@app.put("/api/tasks")
def save_tasks(payload: TasksPayload) -> list[dict[str, Any]]:
    return services.config.save_tasks(payload.tasks)


@app.get("/api/crew/config")
def crew_config() -> dict[str, Any]:
    return services.config.get_config()


@app.patch("/api/crew/inputs")
def update_inputs(payload: InputsPayload) -> dict[str, Any]:
    return services.config.update_inputs(payload.inputs)


@app.get("/api/models/config")
def model_config() -> dict[str, Any]:
    return services.config.get_model_config()


@app.patch("/api/models/agents")
def update_models(payload: ModelPayload) -> list[dict[str, Any]]:
    return services.config.update_agent_models(payload.llm)


@app.get("/api/outputs")
def outputs() -> list[dict[str, Any]]:
    return services.config.list_outputs()


@app.get("/api/outputs/content")
def output_content(path: str) -> dict[str, Any]:
    try:
        return services.config.read_output(path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"未找到输出文件：{path}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="输出文件路径不合法。") from exc


@app.get("/api/settings")
def get_settings() -> dict[str, Any]:
    return dashboard_config_service.get_settings()


@app.put("/api/settings")
def save_settings(payload: SettingsPayload) -> dict[str, Any]:
    settings = dashboard_config_service.save_crew_project_path(payload.crew_project_path)
    services.set_crew_project_path(dashboard_config_service.get_crew_project_path())
    return settings


@app.get("/api/health")
def health() -> dict[str, Any]:
    return services.health.check()


@app.post("/api/runs")
async def create_run() -> dict[str, Any]:
    try:
        run_id = services.runner.create_run()
    except RuntimeError as exc:
        status_code = 409 if "已有生产线正在运行" in str(exc) else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    asyncio.create_task(services.runner.run_crew(run_id))
    return {"id": run_id, "status": "running"}


@app.get("/api/runs")
def runs() -> list[dict[str, Any]]:
    return services.runner.list_runs()


@app.get("/api/runs/{run_id}")
def run_detail(run_id: int) -> dict[str, Any]:
    run = services.runner.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="未找到运行记录。")
    return run


@app.websocket("/ws/runs/{run_id}/logs")
async def run_logs(websocket: WebSocket, run_id: int) -> None:
    await websocket.accept()
    existing = services.runner.get_run(run_id)
    if existing and existing.get("log_text"):
        await websocket.send_text(existing["log_text"])
    queue = services.runner.subscribe(run_id)
    try:
        while True:
            message = await queue.get()
            await websocket.send_text(message)
    except WebSocketDisconnect:
        services.runner.unsubscribe(run_id, queue)
