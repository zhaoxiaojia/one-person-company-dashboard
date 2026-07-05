# One Person Company Dashboard

Local Web Dashboard for the `anime_story_company` CrewAI project.

## Features in MVP

- Read current Crew name, agents, tasks, and inputs.
- Edit `inputs.story_idea` in `crew.jsonc`.
- Create, edit, and delete Agent JSONC files.
- Create, edit, delete, and reorder Tasks in `crew.jsonc`.
- Create a timestamped `.bak` before saving `crew.jsonc`.
- Run `uv run crewai run` from the configured CrewAI project directory.
- Stream stdout/stderr logs in the browser.
- Store run history in SQLite.
- Mask API keys and bearer tokens before logs reach the frontend.
- Preview Markdown, text, and JSON output files.
- View masked model environment fields and bulk update all Agent `llm` values.
- View a simple workflow diagram based on current Task order.

The interface intentionally remains local-first and lightweight; it is not a multi-user hosted control plane.

## Project Path

The backend defaults to:

```bash
/Users/chao.li/one-person-company/anime_story_company
```

Override it with:

```bash
export CREW_PROJECT_PATH="/absolute/path/to/crew/project"
```

## Backend

```bash
cd /Users/chao.li/one-person-company/one-person-company-dashboard/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Backend URL: `http://localhost:8000`

## Frontend

```bash
cd /Users/chao.li/one-person-company/one-person-company-dashboard/frontend
npm install
npm run dev
```

Frontend URL: `http://localhost:5173`

## Validation

1. Open `http://localhost:5173`.
2. Dashboard shows `anime_story_company`, 3 Agents, and 3 Tasks.
3. Agents page lists the current `agents/*.jsonc` files.
4. Tasks page lists the 3 tasks from `crew.jsonc`.
5. Crew Config can save a new `story_idea`.
6. Runs page can start `uv run crewai run`.
7. Logs stream in the browser.
8. Finished runs appear in the history list.
9. Agents and Tasks pages can save edits and create `.bak` files.
10. Outputs, Models, and Flow pages render current project state.

## Tests

```bash
cd /Users/chao.li/one-person-company/one-person-company-dashboard/backend
python3 -m pytest -q

cd /Users/chao.li/one-person-company/one-person-company-dashboard/frontend
npm run build
```
