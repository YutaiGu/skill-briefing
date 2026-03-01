from __future__ import annotations

import argparse
import json
from pathlib import Path


def _resolve_config_path() -> Path:
    base_dir = Path(__file__).resolve().parent
    config_path = base_dir / "config.json"
    legacy_path = base_dir / "backend" / "data" / "config.json"
    if config_path.exists():
        return config_path
    if legacy_path.exists():
        return legacy_path
    return config_path


CONFIG_PATH = _resolve_config_path()


def _load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config not found: {CONFIG_PATH}")
    try:
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        raise RuntimeError(f"Failed to read config: {CONFIG_PATH}") from e
    if not isinstance(cfg, dict):
        raise RuntimeError("Invalid config format: expected JSON object")
    return cfg


def _save_config(cfg: dict) -> None:
    CONFIG_PATH.write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _parse_value(raw: str):
    text = raw.strip()
    if text.lower() in {"none", "null"}:
        return None
    if text.lower() == "true":
        return True
    if text.lower() == "false":
        return False
    try:
        return json.loads(text)
    except Exception:
        return text


def add_source(url: str) -> None:
    cfg = _load_config()
    urls = cfg.get("SOURCE_URLS")
    if not isinstance(urls, list):
        urls = []

    url = url.strip()
    if not url:
        raise ValueError("source_url is empty")

    if url in urls:
        print(f"SOURCE_URLS already contains: {url}")
        return

    urls.append(url)
    cfg["SOURCE_URLS"] = urls
    _save_config(cfg)
    print(f"Added source_url: {url}")


def delete_source(url: str) -> None:
    cfg = _load_config()
    urls = cfg.get("SOURCE_URLS")
    if not isinstance(urls, list):
        urls = []

    url = url.strip()
    if not url:
        raise ValueError("source_url is empty")

    if url not in urls:
        print(f"SOURCE_URLS does not contain: {url}")
        return

    urls = [x for x in urls if x != url]
    cfg["SOURCE_URLS"] = urls
    _save_config(cfg)
    print(f"Deleted source_url: {url}")


def set_config_key(key: str, value_raw: str) -> None:
    key = key.strip()
    if not key:
        raise ValueError("key is empty")

    cfg = _load_config()
    value = _parse_value(value_raw)
    cfg[key] = value
    _save_config(cfg)
    print(f"Set {key} = {value!r}")


def show_config() -> None:
    cfg = _load_config()
    print(json.dumps(cfg, ensure_ascii=False, indent=2))


def run() -> None:
    import time
    from sqlalchemy.orm import Session

    from db import engine, clean_all, init_db, clean_entries
    from downloader import downloader
    from transcriber import transcriber, check_whisper_model

    init_db()
    check_whisper_model()

    print("START")
    with Session(engine, future=True) as session:
        downloader(session)
        time.sleep(10)
        transcriber(session)
        time.sleep(10)
        clean_entries(session)
        clean_all(session)
    print("END")


def main():
    parser = argparse.ArgumentParser(
        prog="briefing",
        description="Run briefing pipeline or update config.json",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-add", metavar="source_url", help="add one SOURCE_URLS item")
    group.add_argument("-delete", metavar="source_url", help="delete one SOURCE_URLS item")
    group.add_argument("-set", nargs=2, metavar=("KEY", "VALUE"), help="set config key")
    group.add_argument("-show", action="store_true", help="show config.json")
    args = parser.parse_args()

    if args.add:
        add_source(args.add)
        return

    if args.delete:
        delete_source(args.delete)
        return

    if args.set:
        key, value = args.set
        set_config_key(key, value)
        return

    if args.show:
        show_config()
        return

    run()

if __name__ == "__main__":
    main()
