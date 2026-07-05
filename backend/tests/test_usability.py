import json
import sqlite3
from pathlib import Path

import pytest

from services.dashboard_config_service import DashboardConfigService
from services.health_service import HealthService
from services.runner_service import RunnerService


@pytest.fixture()
def valid_crew_project(tmp_path: Path) -> Path:
    project = tmp_path / "crew"
    agents = project / "agents"
    agents.mkdir(parents=True)
    (project / "crew.jsonc").write_text(
        '{"name":"demo","agents":["writer"],"tasks":[],"inputs":{}}',
        encoding="utf-8",
    )
    (agents / "writer.jsonc").write_text('{"role":"Writer"}', encoding="utf-8")
    (project / ".env").write_text("OPENAI_API_KEY=sk-test-secret\n", encoding="utf-8")
    return project


def test_dashboard_config_prefers_saved_path_over_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    default_path = tmp_path / "default"
    env_path = tmp_path / "env"
    saved_path = tmp_path / "saved"
    config_path = tmp_path / "dashboard_config.json"
    monkeypatch.setenv("CREW_PROJECT_PATH", str(env_path))
    service = DashboardConfigService(config_path, default_path)

    before = service.get_settings()
    service.save_crew_project_path(saved_path)
    after = service.get_settings()

    assert before["crew_project_path"] == str(env_path.resolve())
    assert before["source"] == "environment"
    assert after["crew_project_path"] == str(saved_path.resolve())
    assert after["source"] == "local"
    assert json.loads(config_path.read_text(encoding="utf-8"))["crew_project_path"] == str(saved_path.resolve())


def test_health_check_reports_missing_crew_json_in_chinese(tmp_path: Path):
    project = tmp_path / "bad_crew"
    project.mkdir()
    service = HealthService(project)

    result = service.check()

    assert result["ok"] is False
    assert "未找到 crew.jsonc" in result["message"]
    assert any(check["name"] == "crew.jsonc" and check["ok"] is False for check in result["checks"])


def test_health_check_validates_project_files_before_tools(valid_crew_project: Path):
    service = HealthService(valid_crew_project, check_commands=False)

    result = service.check()

    assert result["ok"] is True
    assert result["message"] == "健康检查通过，可以运行生产线。"


def test_runner_rejects_unhealthy_project_with_chinese_error(tmp_path: Path):
    db_path = tmp_path / "runs.sqlite"
    runner = RunnerService(tmp_path / "missing_crew", db_path)

    with pytest.raises(RuntimeError, match="CrewAI 项目路径不存在"):
        runner.create_run()

    assert not db_path.exists() or sqlite3.connect(db_path).execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 0


def test_runner_active_run_error_is_chinese(tmp_path: Path, valid_crew_project: Path):
    db_path = tmp_path / "runs.sqlite"
    runner = RunnerService(valid_crew_project, db_path)
    connection = sqlite3.connect(db_path)
    connection.execute(
        "INSERT INTO runs (started_at, status, log_text) VALUES ('2026-07-05T00:00:00Z', 'running', '')"
    )
    connection.commit()
    connection.close()

    with pytest.raises(RuntimeError, match="已有生产线正在运行"):
        runner.create_run()


def test_simplifies_english_log_into_chinese_summary(tmp_path: Path):
    runner = RunnerService(tmp_path, tmp_path / "runs.sqlite")
    raw_log = "\n".join(
        [
            "Starting CrewAI run",
            "Task plan_story_task assigned to agent project_manager",
            "Agent novel_writer is working",
            "Writing output file short_anime_script.md",
            "Completed successfully",
            "Error: sample failure",
            "OPENAI_API_KEY=sk-secret-value",
        ]
    )

    simple = runner._simplify_log(raw_log)

    assert "正在启动生产线" in simple
    assert "正在执行任务：plan_story_task" in simple
    assert "当前智能体：project_manager" in simple
    assert "当前智能体：novel_writer" in simple
    assert "输出文件：short_anime_script.md" in simple
    assert "运行成功" in simple
    assert "运行失败：Error: sample failure" in simple
    assert "sk-secret-value" not in simple


def test_finalizes_story_outputs_from_modified_story_file(tmp_path: Path, valid_crew_project: Path):
    db_path = tmp_path / "runs.sqlite"
    runner = RunnerService(valid_crew_project, db_path)
    story_file = valid_crew_project / "short_anime_script.md"
    story_file.write_text("# 最终故事\n\n这是最终剧本内容。", encoding="utf-8")

    paths = runner._finalize_story_output(1, "# log", "success")
    run = runner._build_story_fields({"output_paths": paths, "log_text": "# log"})

    latest = valid_crew_project / "outputs" / "latest_story.md"
    archived = valid_crew_project / "outputs" / "runs" / "run_1_story.md"
    assert latest.read_text(encoding="utf-8") == "# 最终故事\n\n这是最终剧本内容。"
    assert archived.read_text(encoding="utf-8") == "# 最终故事\n\n这是最终剧本内容。"
    assert str(latest) in paths
    assert str(archived) in paths
    assert run["story_output_path"] == "outputs/runs/run_1_story.md"
    assert run["story_markdown"].startswith("# 最终故事")
    assert run["story_message"] == "已提取最终故事。"


def test_finalizes_raw_log_when_story_cannot_be_extracted(tmp_path: Path, valid_crew_project: Path):
    runner = RunnerService(valid_crew_project, tmp_path / "runs.sqlite")
    raw_log = "OPENAI_API_KEY=sk-secret-value\nshort log"

    paths = runner._finalize_story_output(2, raw_log, "success")
    run = runner._build_story_fields({"output_paths": paths, "log_text": raw_log})

    raw_path = valid_crew_project / "outputs" / "runs" / "run_2_raw.md"
    assert raw_path.exists()
    assert "sk-secret-value" not in raw_path.read_text(encoding="utf-8")
    assert str(raw_path) in paths
    assert run["story_output_path"] == "outputs/runs/run_2_raw.md"
    assert run["story_markdown"] == ""
    assert run["story_message"] == "未提取到最终故事，请查看原始日志。"


def test_lists_nested_output_files(valid_crew_project: Path):
    outputs_dir = valid_crew_project / "outputs" / "runs"
    outputs_dir.mkdir(parents=True)
    (valid_crew_project / "outputs" / "latest_story.md").write_text("# latest", encoding="utf-8")
    (outputs_dir / "run_1_story.md").write_text("# story", encoding="utf-8")

    from services.crew_config_service import CrewConfigService

    outputs = CrewConfigService(valid_crew_project).list_outputs()

    assert "outputs/latest_story.md" in [item["path"] for item in outputs]
    assert "outputs/runs/run_1_story.md" in [item["path"] for item in outputs]
