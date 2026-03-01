from __future__ import annotations

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
AUDIO_DIR = DATA_DIR / "audio"
OUTPUT_DIR = BASE_DIR / "output"
TEMPORARY_DIR = DATA_DIR / "temporary"
PENDING_FILE = DATA_DIR / ".pending.json"
CONFIG_JSON = BASE_DIR / "config.json"
_LEGACY_CONFIG_JSON = BASE_DIR / "backend" / "data" / "config.json"
DB_URL = f"sqlite:///{(DATA_DIR / 'db.sqlite3').as_posix()}"

if not CONFIG_JSON.exists() and _LEGACY_CONFIG_JSON.exists():
    CONFIG_JSON = _LEGACY_CONFIG_JSON

if not CONFIG_JSON.exists():
    raise FileNotFoundError(f"Missing configuration. Please save the configuration once in the panel first.")

try:
    _cfg = json.loads(CONFIG_JSON.read_text(encoding="utf-8"))
except Exception as e:
    raise RuntimeError(f"Failed to read config.json: {CONFIG_JSON}") from e

if not isinstance(_cfg, dict):
    raise RuntimeError(f"Invalid config.json format (expected object): {CONFIG_JSON}")


def _get(name: str, default):
    return _cfg.get(name, default)


UPDATE_LIMIT = int(_get("UPDATE_LIMIT", 2))
POOL_NUM = int(_get("POOL_NUM", 1))
TRANSCRIBER_LIMIT = _get("TRANSCRIBER_LIMIT", None)
if TRANSCRIBER_LIMIT is not None:
    TRANSCRIBER_LIMIT = int(TRANSCRIBER_LIMIT)
DOWNLOAD_INTERVAL = int(_get("DOWNLOAD_INTERVAL", 21600))
PROCESS_INTERVAL = int(_get("PROCESS_INTERVAL", 600))
ENTRIES_LIMIT = f"1-{int(_get('ENTRIES_LIMIT', 2))}"
SOURCE_URLS = [str(x).strip() for x in _get("SOURCE_URLS", []) if str(x).strip()]

api_model = {
    "whisper_model": str(_get("whisper_model", "small")),
}

def check_config() -> tuple[bool, list[str], list[str]]:
    for d in [DATA_DIR, AUDIO_DIR, OUTPUT_DIR, TEMPORARY_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    if not PENDING_FILE.exists():
        PENDING_FILE.write_text("{}", encoding="utf-8")

    return True, [], []
