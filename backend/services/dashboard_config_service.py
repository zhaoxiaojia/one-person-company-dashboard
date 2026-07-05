import json
import os
from pathlib import Path
from typing import Any


class DashboardConfigService:
    def __init__(self, config_path: Path, default_crew_project_path: Path):
        self.config_path = Path(config_path)
        self.default_crew_project_path = Path(default_crew_project_path)

    def get_crew_project_path(self) -> Path:
        return Path(self.get_settings()["crew_project_path"])

    def get_settings(self) -> dict[str, Any]:
        local_path = self._read_local_path()
        env_path = os.getenv("CREW_PROJECT_PATH")
        if local_path:
            path = local_path
            source = "local"
        elif env_path:
            path = Path(env_path)
            source = "environment"
        else:
            path = self.default_crew_project_path
            source = "default"
        return {
            "crew_project_path": str(Path(path).expanduser().resolve()),
            "source": source,
            "default_crew_project_path": str(self.default_crew_project_path.expanduser().resolve()),
            "config_path": str(self.config_path.resolve()),
        }

    def save_crew_project_path(self, crew_project_path: Path | str) -> dict[str, Any]:
        path = Path(crew_project_path).expanduser().resolve()
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps({"crew_project_path": str(path)}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return self.get_settings()

    def _read_local_path(self) -> Path | None:
        if not self.config_path.exists():
            return None
        data = json.loads(self.config_path.read_text(encoding="utf-8"))
        value = data.get("crew_project_path")
        return Path(value).expanduser() if value else None
