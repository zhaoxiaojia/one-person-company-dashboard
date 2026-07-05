import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import json5


class CrewConfigService:
    def __init__(self, crew_project_path: Path):
        self.crew_project_path = Path(crew_project_path)

    @property
    def crew_file(self) -> Path:
        return self.crew_project_path / "crew.jsonc"

    @property
    def agents_dir(self) -> Path:
        return self.crew_project_path / "agents"

    def _read_jsonc(self, path: Path) -> dict[str, Any]:
        return json5.loads(path.read_text(encoding="utf-8"))

    def _backup_file(self, path: Path) -> Path | None:
        if not path.exists():
            return None
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
        backup_path = path.with_name(f"{path.name}.{timestamp}.bak")
        shutil.copy2(path, backup_path)
        return backup_path

    def _write_json(self, path: Path, data: dict[str, Any] | list[dict[str, Any]]) -> None:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _safe_agent_path(self, filename: str) -> Path:
        if not filename.endswith(".jsonc") or "/" in filename or "\\" in filename or filename.startswith("."):
            raise ValueError("invalid agent filename")
        return self.agents_dir / filename

    def _safe_output_path(self, relative_path: str) -> Path:
        path = (self.crew_project_path / relative_path).resolve()
        root = self.crew_project_path.resolve()
        if root not in path.parents or path.suffix.lower() not in {".md", ".txt", ".json"}:
            raise ValueError("invalid output path")
        return path

    def read_crew(self) -> dict[str, Any]:
        return self._read_jsonc(self.crew_file)

    def list_agents(self) -> list[dict[str, Any]]:
        agents: list[dict[str, Any]] = []
        for path in sorted(self.agents_dir.glob("*.jsonc")):
            data = self._read_jsonc(path)
            settings = data.get("settings") or {}
            agents.append(
                {
                    "filename": path.name,
                    "role": data.get("role"),
                    "goal": data.get("goal"),
                    "llm": data.get("llm"),
                    "tools": data.get("tools", []),
                    "allow_delegation": settings.get("allow_delegation"),
                }
            )
        return agents

    def get_agent(self, filename: str) -> dict[str, Any]:
        path = self._safe_agent_path(filename)
        data = self._read_jsonc(path)
        return {"filename": path.name, "content": data, **self._agent_summary(path, data)}

    def save_agent(self, filename: str, content: dict[str, Any]) -> dict[str, Any]:
        path = self._safe_agent_path(filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._backup_file(path)
        self._write_json(path, content)
        return self._agent_summary(path, content)

    def delete_agent(self, filename: str) -> None:
        path = self._safe_agent_path(filename)
        if not path.exists():
            raise FileNotFoundError(filename)
        self._backup_file(path)
        path.unlink()

    def _agent_summary(self, path: Path, data: dict[str, Any]) -> dict[str, Any]:
        settings = data.get("settings") or {}
        return {
            "filename": path.name,
            "role": data.get("role"),
            "goal": data.get("goal"),
            "llm": data.get("llm"),
            "tools": data.get("tools", []),
            "allow_delegation": settings.get("allow_delegation"),
        }

    def list_tasks(self) -> list[dict[str, Any]]:
        tasks = self.read_crew().get("tasks", [])
        return [
            {
                "name": task.get("name"),
                "description": task.get("description"),
                "expected_output": task.get("expected_output"),
                "agent": task.get("agent"),
            }
            for task in tasks
        ]

    def save_tasks(self, tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        crew = self.read_crew()
        self._backup_file(self.crew_file)
        crew["tasks"] = tasks
        self._write_json(self.crew_file, crew)
        return self.list_tasks()

    def get_config(self) -> dict[str, Any]:
        crew = self.read_crew()
        return {
            "name": crew.get("name"),
            "agents": crew.get("agents", []),
            "tasks": crew.get("tasks", []),
            "process": crew.get("process"),
            "verbose": crew.get("verbose"),
            "memory": crew.get("memory"),
            "inputs": crew.get("inputs", {}),
        }

    def get_summary(self) -> dict[str, Any]:
        crew = self.read_crew()
        return {
            "name": crew.get("name"),
            "agent_count": len(crew.get("agents", [])),
            "task_count": len(crew.get("tasks", [])),
        }

    def update_inputs(self, inputs: dict[str, Any]) -> dict[str, Any]:
        crew = self.read_crew()
        self._backup_file(self.crew_file)
        crew["inputs"] = inputs
        self._write_json(self.crew_file, crew)
        return self.get_config()

    def update_agent_models(self, llm: str) -> list[dict[str, Any]]:
        for path in sorted(self.agents_dir.glob("*.jsonc")):
            data = self._read_jsonc(path)
            self._backup_file(path)
            data["llm"] = llm
            self._write_json(path, data)
        return self.list_agents()

    def list_outputs(self) -> list[dict[str, Any]]:
        output_files: list[dict[str, Any]] = []
        outputs_dir = self.crew_project_path / "outputs"
        seen: set[Path] = set()
        for suffix in ("*.md", "*.txt", "*.json"):
            for path in self.crew_project_path.glob(suffix):
                if path.name.endswith(".bak") or path in seen:
                    continue
                seen.add(path)
                stat = path.stat()
                output_files.append(
                    {
                        "name": path.name,
                        "path": str(path.relative_to(self.crew_project_path)),
                        "size": stat.st_size,
                        "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                        "kind": self._output_kind(path),
                    }
                )
        if outputs_dir.exists():
            for suffix in ("*.md", "*.txt", "*.json"):
                for path in outputs_dir.rglob(suffix):
                    if path.name.endswith(".bak") or path in seen:
                        continue
                    seen.add(path)
                    stat = path.stat()
                    output_files.append(
                        {
                            "name": path.name,
                            "path": str(path.relative_to(self.crew_project_path)),
                            "size": stat.st_size,
                            "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                            "kind": self._output_kind(path),
                        }
                    )
        return sorted(output_files, key=lambda item: item["name"])

    def read_output(self, relative_path: str) -> dict[str, Any]:
        path = self._safe_output_path(relative_path)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(relative_path)
        return {
            "name": path.name,
            "path": str(path.relative_to(self.crew_project_path)),
            "kind": self._output_kind(path),
            "content": path.read_text(encoding="utf-8"),
        }

    def get_model_config(self) -> dict[str, Any]:
        env_path = self.crew_project_path / ".env"
        values: dict[str, str] = {}
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if not line or line.strip().startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                values[key] = self._mask_env_value(key, value)
        return {"env": values, "agent_llms": self.list_agents()}

    def _mask_env_value(self, key: str, value: str) -> str:
        if any(part in key.upper() for part in ("KEY", "TOKEN", "SECRET", "PASSWORD")):
            stripped = value.strip().strip("\"'")
            if len(stripped) <= 8:
                return "***"
            return f"{stripped[:4]}...{stripped[-4:]}"
        return value

    def _output_kind(self, path: Path) -> str:
        if path.suffix.lower() == ".md":
            return "markdown"
        if path.suffix.lower() == ".json":
            return "json"
        return "text"
