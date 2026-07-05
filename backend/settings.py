from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CREW_PROJECT_PATH = (BASE_DIR.parent.parent / "anime_story_company").resolve()
CREW_PROJECT_PATH = Path(os.getenv("CREW_PROJECT_PATH", DEFAULT_CREW_PROJECT_PATH)).resolve()
DB_PATH = Path(os.getenv("DASHBOARD_DB_PATH", BASE_DIR / "dashboard.sqlite3")).resolve()
DASHBOARD_CONFIG_PATH = Path(os.getenv("DASHBOARD_CONFIG_PATH", BASE_DIR / "dashboard_config.json")).resolve()
