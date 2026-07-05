import asyncio
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from db.database import connect, init_db
from services.health_service import HealthService
from services.log_service import mask_sensitive_text


TOKEN_RE = re.compile(r"(?i)(input|prompt)\D+(\d+).*?(output|completion)\D+(\d+)")


class RunnerService:
    def __init__(self, crew_project_path: Path, db_path: Path, health_service: HealthService | None = None):
        self.crew_project_path = Path(crew_project_path)
        self.db_path = Path(db_path)
        self.health_service = health_service or HealthService(self.crew_project_path)
        self.subscribers: dict[int, set[asyncio.Queue[str]]] = {}
        init_db(self.db_path)

    def _has_active_run(self) -> bool:
        with connect(self.db_path) as connection:
            row = connection.execute("SELECT id FROM runs WHERE status = 'running' LIMIT 1").fetchone()
        return row is not None

    def create_run(self) -> int:
        if self._has_active_run():
            raise RuntimeError("已有生产线正在运行，请等待完成后再启动。")
        health = self.health_service.check()
        if not health["ok"]:
            raise RuntimeError(health["message"])
        started_at = datetime.now(timezone.utc).isoformat()
        with connect(self.db_path) as connection:
            cursor = connection.execute(
                "INSERT INTO runs (started_at, status, log_text) VALUES (?, 'running', '')",
                (started_at,),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def list_runs(self) -> list[dict[str, Any]]:
        with connect(self.db_path) as connection:
            rows = connection.execute("SELECT * FROM runs ORDER BY id DESC").fetchall()
        return [self._row_to_dict(row, include_log=False) for row in rows]

    def get_run(self, run_id: int) -> dict[str, Any] | None:
        with connect(self.db_path) as connection:
            row = connection.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        return self._row_to_dict(row, include_log=True) if row else None

    def subscribe(self, run_id: int) -> asyncio.Queue[str]:
        queue: asyncio.Queue[str] = asyncio.Queue()
        self.subscribers.setdefault(run_id, set()).add(queue)
        return queue

    def unsubscribe(self, run_id: int, queue: asyncio.Queue[str]) -> None:
        subscribers = self.subscribers.get(run_id)
        if not subscribers:
            return
        subscribers.discard(queue)
        if not subscribers:
            self.subscribers.pop(run_id, None)

    async def _publish(self, run_id: int, message: str) -> None:
        for queue in list(self.subscribers.get(run_id, set())):
            await queue.put(message)

    async def run_crew(self, run_id: int) -> None:
        started = datetime.now(timezone.utc)
        process = await asyncio.create_subprocess_exec(
            "uv",
            "run",
            "crewai",
            "run",
            cwd=self.crew_project_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        assert process.stdout is not None
        collected: list[str] = []
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            text = mask_sensitive_text(line.decode(errors="replace"))
            collected.append(text)
            self._append_log(run_id, text)
            await self._publish(run_id, text)
        return_code = await process.wait()
        ended = datetime.now(timezone.utc)
        log_text = "".join(collected)
        status = "success" if return_code == 0 else "failed"
        error_message = None if return_code == 0 else f"uv run crewai run exited with code {return_code}"
        input_tokens, output_tokens = self._parse_tokens(log_text)
        output_paths = self._scan_output_paths(started)
        with connect(self.db_path) as connection:
            connection.execute(
                """
                UPDATE runs
                SET ended_at = ?, status = ?, duration_ms = ?, input_tokens = ?,
                    output_tokens = ?, error_message = ?, output_paths_json = ?
                WHERE id = ?
                """,
                (
                    ended.isoformat(),
                    status,
                    int((ended - started).total_seconds() * 1000),
                    input_tokens,
                    output_tokens,
                    error_message,
                    json.dumps(output_paths, ensure_ascii=False),
                    run_id,
                ),
            )
            connection.commit()
        await self._publish(run_id, f"\n[run {status}]\n")

    def _append_log(self, run_id: int, text: str) -> None:
        with connect(self.db_path) as connection:
            connection.execute("UPDATE runs SET log_text = log_text || ? WHERE id = ?", (text, run_id))
            connection.commit()

    def _parse_tokens(self, log_text: str) -> tuple[int | None, int | None]:
        json_match = re.search(r'"prompt_tokens"\s*:\s*(\d+).*?"completion_tokens"\s*:\s*(\d+)', log_text, re.DOTALL)
        if json_match:
            return int(json_match.group(1)), int(json_match.group(2))
        match = TOKEN_RE.search(log_text)
        if not match:
            return None, None
        return int(match.group(2)), int(match.group(4))

    def _simplify_log(self, log_text: str) -> str:
        lines: list[str] = ["正在启动生产线"]
        keywords = ("task", "agent", "success", "failed", "error", "output", "finished", "completed", "writing")
        for raw_line in mask_sensitive_text(log_text).splitlines():
            line = raw_line.strip()
            if not line:
                continue
            lower = line.lower()
            if not any(keyword in lower for keyword in keywords):
                continue
            task_match = re.search(r"(?i)\btask\s+([A-Za-z0-9_\-]+)", line)
            agent_match = re.search(r"(?i)\bagent\s+([A-Za-z0-9_\-]+)", line)
            output_match = re.search(r"([^\s]+?\.(?:md|txt|json))\b", line, re.IGNORECASE)
            if task_match:
                lines.append(f"正在执行任务：{task_match.group(1)}")
            if agent_match:
                lines.append(f"当前智能体：{agent_match.group(1)}")
            if output_match:
                lines.append(f"输出文件：{output_match.group(1)}")
            if "error" in lower or "failed" in lower or "exception" in lower:
                lines.append(f"运行失败：{line}")
            elif "success" in lower or "finished" in lower or "completed" in lower:
                lines.append("运行成功")
        if not lines:
            return "暂无关键进度。需要排查时请切换到原始日志。"
        return "\n".join(lines[-80:])

    def _scan_output_paths(self, started: datetime) -> list[str]:
        outputs: list[str] = []
        for pattern in ("*.md", "*.txt", "*.json"):
            for path in self.crew_project_path.glob(pattern):
                modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
                if modified >= started:
                    outputs.append(str(path))
        return sorted(outputs)

    def _row_to_dict(self, row: sqlite3.Row, include_log: bool) -> dict[str, Any]:
        data = dict(row)
        data["output_paths"] = json.loads(data.pop("output_paths_json") or "[]")
        data["simple_log_text"] = self._simplify_log(data.get("log_text") or "")
        if not include_log:
            data.pop("log_text", None)
        return data
