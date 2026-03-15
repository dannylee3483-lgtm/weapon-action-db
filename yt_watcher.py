"""
Weapon Action DB — YouTube URL 자동 채우기 워처

weapons.json을 주기적으로 감시하다가 YouTube embed URL이 없는 항목이 생기면
yt-dlp로 실제 watch?v= URL을 찾아 자동으로 교체합니다.

실행:
  python yt_watcher.py

필요:
  pip install yt-dlp
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_PATH  = Path(__file__).parent / "data" / "weapons.json"
POLL_SEC = 30  # weapons.json 감시 주기 (초)
REQ_GAP  = 3   # yt-dlp 요청 사이 간격 (과부하·차단 방지)

BOLD  = "\033[1m"
GREEN = "\033[32m"
YEL   = "\033[33m"
DIM   = "\033[90m"
RED   = "\033[31m"
RST   = "\033[0m"

def ts():
    return datetime.now().strftime("%H:%M:%S")

def log(msg):  print(f"  {DIM}[{ts()}]{RST} {msg}", flush=True)
def ok(msg):   print(f"  {DIM}[{ts()}]{RST} {GREEN}✓{RST} {msg}", flush=True)
def err(msg):  print(f"  {DIM}[{ts()}]{RST} {RED}✗{RST} {msg}", flush=True)

# ─── yt-dlp ───────────────────────────────────────────────────────
def find_ytdlp():
    for name in ("yt-dlp", "yt-dlp.exe"):
        r = subprocess.run(
            f"where {name}" if os.name == "nt" else f"which {name}",
            capture_output=True, text=True, shell=True
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip().splitlines()[0]
    return None

def search_video_id(ytdlp, game, action_name):
    """yt-dlp ytsearch1 로 첫 번째 video ID 반환"""
    query = f"{game} {action_name} gameplay"
    try:
        r = subprocess.run(
            [ytdlp, f"ytsearch1:{query}",
             "--get-id", "--no-playlist", "--quiet", "--no-warnings"],
            capture_output=True, text=True, timeout=30
        )
        lines = r.stdout.strip().splitlines()
        return lines[0].strip() if r.returncode == 0 and lines else None
    except Exception:
        return None

# ─── DB ───────────────────────────────────────────────────────────
def load_db():
    with open(DB_PATH, encoding="utf-8") as f:
        return json.load(f)

def save_db(data):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def needs_embed(w):
    yt = (w.get("mediaLinks") or {}).get("youtube") or ""
    return "watch?v=" not in yt

# ─── Git ──────────────────────────────────────────────────────────
def git_push(count):
    repo = DB_PATH.parent.parent
    msg  = f"yt-fill: update {count} youtube url{'s' if count != 1 else ''}"
    try:
        subprocess.run(["git", "add", "data/weapons.json"],
                       cwd=str(repo), capture_output=True, check=True)
        r = subprocess.run(["git", "commit", "-m", msg],
                           cwd=str(repo), capture_output=True, text=True)
        if r.returncode != 0:
            if "nothing to commit" in r.stdout + r.stderr:
                return
            err(f"git commit 실패: {(r.stderr or r.stdout).strip()[:100]}")
            return
        r2 = subprocess.run(["git", "push"],
                            cwd=str(repo), capture_output=True, text=True)
        if r2.returncode != 0:
            subprocess.run(["git", "pull", "--rebase", "origin", "main"],
                           cwd=str(repo), capture_output=True)
            r2 = subprocess.run(["git", "push"],
                                cwd=str(repo), capture_output=True, text=True)
        if r2.returncode == 0:
            ok(f"GitHub Push 완료  [{msg}]")
        else:
            err(f"git push 실패: {r2.stderr.strip()[:100]}")
    except FileNotFoundError:
        err("git 명령을 찾을 수 없습니다")
    except Exception as e:
        err(f"git 오류: {e}")

# ─── 처리 사이클 ──────────────────────────────────────────────────
def process_once(ytdlp, done_ids):
    db      = load_db()
    pending = [w for w in db["weapons"]
               if needs_embed(w) and w["id"] not in done_ids]
    if not pending:
        return

    log(f"embed URL 없는 항목 {len(pending)}개 발견 — 검색 시작")
    updated = 0

    for w in pending:
        vid = search_video_id(ytdlp, w.get("game", ""), w.get("actionName", ""))
        done_ids.add(w["id"])  # 성공/실패 무관하게 이번 세션 재시도 방지

        if vid:
            w["mediaLinks"]["youtube"] = f"https://www.youtube.com/watch?v={vid}"
            ok(f"[{w['id']}] {w.get('actionName','')}  →  {vid}")
            updated += 1
        else:
            err(f"[{w['id']}] {w.get('actionName','')}  →  영상 못 찾음")

        time.sleep(REQ_GAP)

    if updated:
        save_db(db)
        ok(f"{updated}개 URL 저장됨")
        git_push(updated)

# ─── 메인 ─────────────────────────────────────────────────────────
def main():
    print()
    print(f"  {BOLD}{YEL}📺  YouTube URL 워처{RST}")
    print(f"  {DIM}감시 주기: {POLL_SEC}초 | yt-dlp 요청 간격: {REQ_GAP}초{RST}")
    print(f"  {DIM}종료: Ctrl+C{RST}")
    print(f"  {'─' * 44}")
    print()

    ytdlp = find_ytdlp()
    if not ytdlp:
        err("yt-dlp를 찾을 수 없습니다.")
        print(f"  {DIM}설치: pip install yt-dlp{RST}")
        sys.exit(1)
    log(f"yt-dlp: {ytdlp}")

    done_ids = set()

    # 시작 즉시 1회 처리
    try:
        process_once(ytdlp, done_ids)
    except Exception as e:
        err(f"초기 처리 오류: {e}")

    log(f"{POLL_SEC}초마다 감시 중...")

    while True:
        try:
            time.sleep(POLL_SEC)
            process_once(ytdlp, done_ids)
        except KeyboardInterrupt:
            print(f"\n\n  워처 종료됨\n")
            sys.exit(0)
        except Exception as e:
            err(f"처리 오류: {e}")


if __name__ == "__main__":
    main()
