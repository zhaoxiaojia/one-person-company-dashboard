import shutil
import subprocess
from pathlib import Path
from typing import Any

import json5


class HealthService:
    def __init__(self, crew_project_path: Path, check_commands: bool = True):
        self.crew_project_path = Path(crew_project_path)
        self.check_commands = check_commands

    def check(self) -> dict[str, Any]:
        checks: list[dict[str, Any]] = []
        project_ok = self.crew_project_path.exists() and self.crew_project_path.is_dir()
        checks.append(self._item("CrewAI 项目路径", project_ok, self._project_message(project_ok)))
        if not project_ok:
            return self._result(checks)

        crew_file = self.crew_project_path / "crew.jsonc"
        crew_ok = crew_file.exists() and crew_file.is_file()
        crew_message = "已找到 crew.jsonc。"
        if crew_ok:
            try:
                json5.loads(crew_file.read_text(encoding="utf-8"))
            except Exception as exc:  # noqa: BLE001
                crew_ok = False
                crew_message = f"crew.jsonc 解析失败：{exc}"
        else:
            crew_message = "未找到 crew.jsonc，请检查项目路径。"
        checks.append(self._item("crew.jsonc", crew_ok, crew_message))

        agents_dir = self.crew_project_path / "agents"
        agents_ok = agents_dir.exists() and agents_dir.is_dir() and any(agents_dir.glob("*.jsonc"))
        checks.append(
            self._item(
                "智能体目录",
                agents_ok,
                "已找到 agents 目录和智能体配置。" if agents_ok else "未找到 agents 目录或目录中没有 .jsonc 智能体配置。",
            )
        )

        env_file = self.crew_project_path / ".env"
        env_ok = env_file.exists() and env_file.is_file()
        checks.append(self._item(".env 配置", env_ok, "已找到 .env。" if env_ok else "未找到 .env，请先配置模型 API。"))

        if self.check_commands:
            uv_ok, uv_message = self._run_command(["uv", "--version"], None, "uv")
            checks.append(self._item("uv 命令", uv_ok, uv_message))
            crewai_ok, crewai_message = self._run_command(["uv", "run", "crewai", "--version"], self.crew_project_path, "crewai")
            checks.append(self._item("crewai 命令", crewai_ok, crewai_message))

        return self._result(checks)

    def _run_command(self, command: list[str], cwd: Path | None, label: str) -> tuple[bool, str]:
        if shutil.which(command[0]) is None:
            return False, f"未找到 {command[0]} 命令，请先安装。"
        try:
            completed = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=20, check=False)
        except Exception as exc:  # noqa: BLE001
            return False, f"{label} 检查失败：{exc}"
        if completed.returncode == 0:
            return True, f"{label} 可用。"
        output = (completed.stderr or completed.stdout or "").strip()
        return False, f"{label} 不可用：{output[:300]}"

    def _project_message(self, ok: bool) -> str:
        if ok:
            return f"当前路径可用：{self.crew_project_path}"
        return f"CrewAI 项目路径不存在：{self.crew_project_path}"

    def _item(self, name: str, ok: bool, message: str) -> dict[str, Any]:
        return {"name": name, "ok": ok, "message": message}

    def _result(self, checks: list[dict[str, Any]]) -> dict[str, Any]:
        ok = all(item["ok"] for item in checks)
        first_failure = next((item for item in checks if not item["ok"]), None)
        return {
            "ok": ok,
            "checks": checks,
            "message": "健康检查通过，可以运行生产线。" if ok else first_failure["message"],
        }
