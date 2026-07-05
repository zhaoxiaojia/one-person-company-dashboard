import json
import sqlite3
from pathlib import Path

import pytest

from services.crew_config_service import CrewConfigService
from services.log_service import mask_sensitive_text
from services.runner_service import RunnerService


@pytest.fixture()
def crew_project(tmp_path: Path) -> Path:
    project = tmp_path / "anime_story_company"
    agents_dir = project / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "writer.jsonc").write_text(
        """
        {
          // comments are valid in agent files
          "role": "Writer",
          "goal": "Write a story",
          "llm": "openai/deepseek-chat",
          "tools": ["FileReadTool"],
          "settings": {"allow_delegation": false}
        }
        """,
        encoding="utf-8",
    )
    (project / "crew.jsonc").write_text(
        """
        {
          "name": "anime_story_company",
          "agents": ["writer"],
          "tasks": [
            {
              "name": "write_story_task",
              "description": "Write {story_idea}",
              "expected_output": "Markdown",
              "agent": "writer"
            }
          ],
          "process": "sequential",
          "verbose": false,
          "memory": false,
          "inputs": {"story_idea": "old idea"}
        }
        """,
        encoding="utf-8",
    )
    return project


def test_reads_agent_jsonc(crew_project: Path):
    service = CrewConfigService(crew_project)

    agents = service.list_agents()

    assert agents == [
        {
            "filename": "writer.jsonc",
            "role": "Writer",
            "goal": "Write a story",
            "llm": "openai/deepseek-chat",
            "tools": ["FileReadTool"],
            "allow_delegation": False,
        }
    ]


def test_reads_tasks_from_crew_jsonc(crew_project: Path):
    service = CrewConfigService(crew_project)

    tasks = service.list_tasks()

    assert tasks[0]["name"] == "write_story_task"
    assert tasks[0]["description"] == "Write {story_idea}"
    assert tasks[0]["expected_output"] == "Markdown"
    assert tasks[0]["agent"] == "writer"


def test_updates_inputs_and_creates_backup(crew_project: Path):
    service = CrewConfigService(crew_project)

    updated = service.update_inputs({"story_idea": "new idea"})

    assert updated["inputs"]["story_idea"] == "new idea"
    backups = list(crew_project.glob("crew.jsonc.*.bak"))
    assert len(backups) == 1
    assert "old idea" in backups[0].read_text(encoding="utf-8")
    saved = json.loads((crew_project / "crew.jsonc").read_text(encoding="utf-8"))
    assert saved["inputs"]["story_idea"] == "new idea"


def test_creates_updates_and_deletes_agent_file(crew_project: Path):
    service = CrewConfigService(crew_project)
    payload = {
        "role": "Editor",
        "goal": "Polish scripts",
        "backstory": "Experienced short-video editor",
        "llm": "openai/gpt-4o-mini",
        "tools": ["FileReadTool"],
        "settings": {"verbose": False, "allow_delegation": False},
    }

    created = service.save_agent("editor.jsonc", payload)
    updated = service.save_agent("editor.jsonc", {**payload, "llm": "deepseek/deepseek-chat"})
    service.delete_agent("editor.jsonc")

    assert created["filename"] == "editor.jsonc"
    assert updated["llm"] == "deepseek/deepseek-chat"
    assert not (crew_project / "agents" / "editor.jsonc").exists()
    assert list((crew_project / "agents").glob("editor.jsonc.*.bak"))


def test_updates_tasks_and_order_with_backup(crew_project: Path):
    service = CrewConfigService(crew_project)
    tasks = [
        {
            "name": "review_story_task",
            "description": "Review",
            "expected_output": "Final",
            "agent": "writer",
        },
        {
            "name": "write_story_task",
            "description": "Write",
            "expected_output": "Draft",
            "agent": "writer",
        },
    ]

    updated = service.save_tasks(tasks)

    assert [task["name"] for task in updated] == ["review_story_task", "write_story_task"]
    assert list(crew_project.glob("crew.jsonc.*.bak"))


def test_bulk_updates_agent_models_with_backups(crew_project: Path):
    service = CrewConfigService(crew_project)

    updated = service.update_agent_models("deepseek/deepseek-chat")

    assert updated[0]["llm"] == "deepseek/deepseek-chat"
    assert list((crew_project / "agents").glob("writer.jsonc.*.bak"))


def test_lists_output_files_and_reads_content(crew_project: Path):
    (crew_project / "short_anime_script.md").write_text("# Script\nContent", encoding="utf-8")
    (crew_project / "data.json").write_text('{"ok": true}', encoding="utf-8")
    service = CrewConfigService(crew_project)

    outputs = service.list_outputs()
    content = service.read_output("short_anime_script.md")

    assert [output["name"] for output in outputs] == ["data.json", "short_anime_script.md"]
    assert content["content"] == "# Script\nContent"
    assert content["kind"] == "markdown"


def test_rejects_output_path_traversal(crew_project: Path):
    service = CrewConfigService(crew_project)

    with pytest.raises(ValueError, match="invalid output path"):
        service.read_output("../crew.jsonc")


def test_masks_sensitive_log_values():
    raw = (
        "OPENAI_API_KEY=sk-1234567890abcdef\n"
        "Authorization: Bearer sk-anothersecretvalue\n"
        "plain sk-abcdefghijklmnopqrstuvwxyz123456"
    )

    masked = mask_sensitive_text(raw)

    assert "sk-1234567890abcdef" not in masked
    assert "sk-anothersecretvalue" not in masked
    assert "sk-abcdefghijklmnopqrstuvwxyz123456" not in masked
    assert "OPENAI_API_KEY=***" in masked
    assert "Authorization: Bearer ***" in masked


def test_parses_common_token_log_formats(tmp_path: Path):
    runner = RunnerService(tmp_path, tmp_path / "runs.sqlite")

    assert runner._parse_tokens("Token Usage: Input Tokens: 123 Output Tokens: 456") == (123, 456)
    assert runner._parse_tokens('{"prompt_tokens": 11, "completion_tokens": 22}') == (11, 22)


def test_runner_rejects_second_active_run(tmp_path: Path):
    db_path = tmp_path / "runs.sqlite"
    connection = sqlite3.connect(db_path)
    connection.execute(
        """
        CREATE TABLE runs (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          started_at TEXT NOT NULL,
          ended_at TEXT,
          status TEXT NOT NULL,
          duration_ms INTEGER,
          input_tokens INTEGER,
          output_tokens INTEGER,
          error_message TEXT,
          log_text TEXT NOT NULL DEFAULT '',
          output_paths_json TEXT NOT NULL DEFAULT '[]'
        )
        """
    )
    connection.execute(
        "INSERT INTO runs (started_at, status, log_text) VALUES ('2026-07-05T00:00:00Z', 'running', '')"
    )
    connection.commit()
    connection.close()
    runner = RunnerService(tmp_path, db_path)

    with pytest.raises(RuntimeError, match="已有生产线正在运行"):
        runner.create_run()
