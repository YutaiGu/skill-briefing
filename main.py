import time
from sqlalchemy.orm import Session

from config import DOWNLOAD_INTERVAL, PROCESS_INTERVAL, CONFIG_JSON
from db import engine, clean_all, init_db, clean_entries
from downloader import downloader, import_external_entries
from transcriber import transcriber, check_whisper_model

def run() -> None:
    print("START")

    with Session(engine, future=True) as session:
        # ---- downloader ----
        downloader(session)
        time.sleep(10)

        # ---- process ----
        import_external_entries(session)
        transcriber(session)
        clean_all(session)
        clean_entries(session)
        time.sleep(10)
        
    print("END")

def main():
    init_db()
    check_whisper_model()
    run()

if __name__ == "__main__":
    main()
