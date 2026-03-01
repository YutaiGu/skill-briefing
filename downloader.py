from yt_dlp import YoutubeDL
from datetime import datetime
import hashlib
import json
import os
import contextlib

from config import AUDIO_DIR, ENTRIES_LIMIT, SOURCE_URLS, UPDATE_LIMIT, PENDING_FILE, BASE_DIR
from db import Video, update_entries, init_entries, get_undownloaded, get_entries_by_ids, save_entries

def downloader(session) -> None:
    for source_url in SOURCE_URLS:
        entries = fetch_all_entries(source_url)
        n = init_entries(session, entries)
        print(f"Inited {n} entries.")
        videos = get_undownloaded(session, source_url, UPDATE_LIMIT)

        ok = 0
        fail = 0
        for v in videos:
            entry = download_entry(v)
            if entry.downloaded == 0:
                fail += 1
            else:
                ok += 1
            update_entries(session, [entry])
        print(f"Download finished: {ok} succeeded, {fail} failed.")

def firefox_cookie_available() -> bool:
    try:
        with open(os.devnull, "w") as devnull, \
            contextlib.redirect_stderr(devnull), \
            contextlib.redirect_stdout(devnull):
            with YoutubeDL({
                "cookiesfrombrowser": ("firefox",),
                "quiet": True,
                "skip_download": True,
            }) as ydl:
                ydl.cookiejar  # Trigger loading
        return True
    except Exception:
        return False

def find_cookies_txt() -> bool:
    p = BASE_DIR / "cookies.txt"
    if p.exists() and p.is_file():
        return True
    return False

def make_local_audio_id(filename: str) -> str:
    # 24-char id for external audio files
    return hashlib.sha1(filename.encode("utf-8")).hexdigest()[:24]

def make_video_id(webpage_url: str) -> str:
    # 16-char id for webpage url
    return hashlib.sha1(webpage_url.encode("utf-8")).hexdigest()[:16]

def fetch_all_entries(source_url: str) -> list:
    '''
    Fetch and normalize video entries from a source URL.

    entry: 
        source            Guaranteed  <-
        extractor         Nullable    <-
        upload_date       Nullable    <-
        duration          Nullable    <-
        language          Nullable    <-
        title             Nullable    <-
        webpage_url       Guaranteed  <-
        inserted_at       Not set here
        downloaded        Not set here
        downloaded_at     Not set here
        file_path         Not set here
        download_error    Not set here
        transcribed       Not set here
        summarized        Not set here
        pushed            Not set here
        video_id          Guaranteed  <-
    '''
    try:
        ydl_opts = {
            "skip_download": True,
            "quiet": True,
            "noprogress": True,
            "no_warnings": True,
            "playlist_items": ENTRIES_LIMIT,
            "extract_flat": True,
        }

        if firefox_cookie_available():
            ydl_opts["cookiesfrombrowser"] = ("firefox",)
        elif find_cookies_txt():
            ydl_opts["cookiefile"] = str(BASE_DIR / "cookies.txt")

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(source_url, download=False)
        if not info:
            return []
    except Exception as e:
        print(e)
        return []
   
    raw_entries = info.get("entries")
    if raw_entries is None:
        raw_entries = [info]  # Single video
    
    entries = []
    for e in raw_entries:
        if not isinstance(e, dict):
            continue
        
        # check entry is a single downloadable item (video)
        if "entries" in e:
            print(f"{source_url} is not a video page.")
            return []
        
        webpage_url = e.get("webpage_url") or e.get("original_url") or e.get("url")
        if not webpage_url:
            continue

        entry = {
            "source": source_url,
            "extractor": e.get("extractor") or e.get("extractor_key"),
            "upload_date": e.get("upload_date"),
            "duration": e.get("duration"),
            "language": e.get("language"),
            "title": e.get("title"),
            "webpage_url": webpage_url,
            "video_id": make_video_id(webpage_url),
        }

        entries.append(entry)

    print(f"Fetched {len(entries)} entries from {source_url}")
    entries = list(reversed(entries))  # # old -> new
    return entries

def download_entry(entry: Video) -> bool:
    '''
    Download one entry
    
    entry: 
        source            Exist
        extractor         Nullable
        upload_date       Nullable
        duration          Nullable
        language          Nullable
        title             Nullable
        webpage_url       Exist
        inserted_at       Exist
        downloaded        Exist     <-
        downloaded_at     Nullable  <-
        file_path         Nullable  <-
        download_error    Nullable  <-
        transcribed       Exist
        summarized        Exist
        pushed            Exist
        video_id          Exist
    '''
    outtmpl = str(AUDIO_DIR / f"{entry.video_id}.%(ext)s")
    out_path = AUDIO_DIR / f"{entry.video_id}.mp3"

    ydl_opts = {
        "quiet": True,
        "noprogress": True,
        "no_warnings": True,
        "format": "bestaudio/best",
        "noplaylist": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "outtmpl": outtmpl,
    }

    if firefox_cookie_available():
        ydl_opts["cookiesfrombrowser"] = ("firefox",)
    elif find_cookies_txt():
        ydl_opts["cookiefile"] = str(BASE_DIR / "cookies.txt")

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(entry.webpage_url, download=True)

        if out_path.exists():
            entry.downloaded = 1
            entry.downloaded_at = datetime.now().isoformat(timespec="seconds")
            entry.file_path = str(out_path)
            entry.download_error = None
            return entry

        # ffmpeg did not create MP3
        entry.downloaded = 0
        entry.download_error = "mp3 not created"
        print(f"{entry.webpage_url} download failed: mp3 not created.")
        return entry
    except Exception as ex:
        entry.downloaded = 0
        entry.download_error = f"{type(ex).__name__}: {ex}"
        print(f"{entry.webpage_url} download failed. {ex}")
        return entry
