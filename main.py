import time
from sqlalchemy.orm import Session

from config import DOWNLOAD_INTERVAL, PROCESS_INTERVAL, CONFIG_JSON
from db import engine, clean_all, init_db, clean_entries
from downloader import downloader, import_external_entries
from transcriber import transcriber, check_whisper_model

def run() -> None:
    download_timer = 0
    process_timer = 0
    print("START")
    
    while True:
        now = time.time()

        with Session(engine, future=True) as session:
            # ---- downloader ----
            if now - download_timer >= DOWNLOAD_INTERVAL:
                downloader(session)
                download_timer = now
                time.sleep(10)

            # ---- process ----
            if now - process_timer >= PROCESS_INTERVAL:
                import_external_entries(session)
                transcriber(session)
                clean_all(session)
                clean_entries(session)
                process_timer = now
                time.sleep(10)

def load_config():
    if not CONFIG_JSON.exists():
        raise FileNotFoundError(
            f"Config not found at {CONFIG_JSON}. Start the API once to generate defaults."
        )
    #with CONFIG_JSON.open("r", encoding="utf-8") as f:
    #    return json.load(f)

def main():
    load_config()
    init_db()
    check_whisper_model()
    run()

if __name__ == "__main__":
    main()
