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
        output_paths.extend(self._finalize_story_output(run_id, log_text, status))
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

    def _finalize_story_output(self, run_id: int, log_text: str, status: str) -> list[str]:
        outputs_dir = self.crew_project_path / "outputs"
        run_outputs_dir = outputs_dir / "runs"
        run_outputs_dir.mkdir(parents=True, exist_ok=True)
        story = self._extract_story_markdown(log_text)
        if story:
            latest_path = outputs_dir / "latest_story.md"
            run_path = run_outputs_dir / f"run_{run_id}_story.md"
            latest_path.write_text(story, encoding="utf-8")
            run_path.write_text(story, encoding="utf-8")
            return [str(latest_path), str(run_path)]
        raw_path = run_outputs_dir / f"run_{run_id}_raw.md"
        raw_path.write_text(mask_sensitive_text(log_text), encoding="utf-8")
        return [str(raw_path)]

    def _extract_story_markdown(self, log_text: str) -> str:
        for name in ("short_anime_script.md", "code_fate_improved.md", "anime_episode_outline.md"):
            path = self.crew_project_path / name
            if path.exists() and path.stat().st_size > 20:
                return path.read_text(encoding="utf-8").strip()
        markdown_blocks = [block.strip() for block in mask_sensitive_text(log_text).split("\n\n") if len(block.strip()) > 500]
        if markdown_blocks:
            return markdown_blocks[-1]
        return ""

    def _build_story_fields(self, data: dict[str, Any]) -> dict[str, str]:
        output_paths = data.get("output_paths") or []
        story_path = ""
        for raw_path in reversed(output_paths):
            path = Path(raw_path)
            if not path.is_absolute():
                path = self.crew_project_path / path
            if path.name.endswith("_story.md") and path.exists():
                story_path = str(path)
                break
        if not story_path:
            for raw_path in reversed(output_paths):
                path = Path(raw_path)
                if not path.is_absolute():
                    path = self.crew_project_path / path
                if path.name.endswith("_raw.md") and path.exists():
                    relative = str(path.relative_to(self.crew_project_path))
                    return {
                        "story_output_path": relative,
                        "story_markdown": "",
                        "story_message": "未提取到最终故事，请查看原始日志。",
                    }
            return {"story_output_path": "", "story_markdown": "", "story_message": "暂无最终故事。"}
        path = Path(story_path)
        return {
            "story_output_path": str(path.relative_to(self.crew_project_path)),
            "story_markdown": path.read_text(encoding="utf-8"),
            "story_message": "已提取最终故事。",
        }

    def _row_to_dict(self, row: sqlite3.Row, include_log: bool) -> dict[str, Any]:
        data = dict(row)
        data["output_paths"] = json.loads(data.pop("output_paths_json") or "[]")
        data["simple_log_text"] = self._simplify_log(data.get("log_text") or "")
        data.update(self._build_story_fields(data))
        if not include_log:
            data.pop("log_text", None)
        return data
