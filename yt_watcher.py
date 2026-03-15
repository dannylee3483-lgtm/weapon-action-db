"""
Weapon Action DB — YouTube URL 자동 채우기 워처 (Claude 판별 버전)

weapons.json을 주기적으로 감시하다가 YouTube embed URL이 없는 항목이 생기면
yt-dlp로 후보 5개 검색 → Claude가 최적 영상 선택 → 자동 교체 + git push

실행:
  python yt_watcher.py

필요:
  pip install yt-dlp
  (Claude CLI: collect.py와 공유)
"""

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# collect.py의 Claude CLI 호출 함수 재사용
sys.path.insert(0, str(Path(__file__).parent))
from collect import call_claude

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_PATH  = Path(__file__).parent / "data" / "weapons.json"
POLL_SEC = 30   # weapons.json 감시 주기 (초)
REQ_GAP  = 5    # 항목 사이 간격 (yt-dlp + Claude 호출 포함)
CANDIDATES = 5  # 후보 영상 수

BOLD  = "\033[1m"
GREEN = "\033[32m"
YEL   = "\033[33m"
DIM   = "\033[90m"
RED   = "\033[31m"
CYAN  = "\033[36m"
RST   = "\033[0m"

def ts():
    return datetime.now().strftime("%H:%M:%S")

def log(msg):  print(f"  {DIM}[{ts()}]{RST} {msg}", flush=True)
def ok(msg):   print(f"  {DIM}[{ts()}]{RST} {GREEN}✓{RST} {msg}", flush=True)
def err(msg):  print(f"  {DIM}[{ts()}]{RST} {RED}✗{RST} {msg}", flush=True)
def dim(msg):  print(f"  {DIM}[{ts()}] {msg}{RST}", flush=True)

# ─── yt-dlp ───────────────────────────────────────────────────────
def find_ytdlp():
    """yt-dlp 실행 커맨드 반환 (list 형태). PATH에 없으면 python -m yt_dlp 로 폴백."""
    # 1) yt-dlp 실행 파일이 PATH에 있는지 확인
    for name in ("yt-dlp", "yt-dlp.exe"):
        r = subprocess.run(
            f"where {name}" if os.name == "nt" else f"which {name}",
            capture_output=True, text=True, shell=True
        )
        if r.returncode == 0 and r.stdout.strip():
            return [r.stdout.strip().splitlines()[0]]
    # 2) python -m yt_dlp 폴백
    try:
        r = subprocess.run(
            [sys.executable, "-m", "yt_dlp", "--version"],
            capture_output=True, text=True
        )
        if r.returncode == 0:
            return [sys.executable, "-m", "yt_dlp"]
    except Exception:
        pass
    return None

def search_candidates(ytdlp, game, action_name, n=CANDIDATES):
    """yt-dlp로 후보 영상 n개 검색 → [(id, title, channel), ...] 반환"""
    query = f"{game} {action_name} gameplay"
    try:
        r = subprocess.run(
            ytdlp + [f"ytsearch{n}:{query}",
             "--dump-json", "--flat-playlist", "--quiet", "--no-warnings"],
            capture_output=True, text=True, timeout=40
        )
        results = []
        for line in r.stdout.strip().splitlines():
            try:
                info    = json.loads(line)
                vid_id  = info.get("id", "")
                title   = info.get("title", "")
                channel = info.get("channel") or info.get("uploader") or ""
                if vid_id and len(vid_id) == 11:
                    results.append((vid_id, title, channel))
            except json.JSONDecodeError:
                continue
        return results
    except Exception as e:
        err(f"yt-dlp 오류: {e}")
        return []

# ─── Claude 판별 ──────────────────────────────────────────────────
def pick_best_video(candidates, game, action_name, description=""):
    """
    Claude에게 후보 영상 중 최적 선택 요청.
    반환: 선택된 video_id (str) 또는 None
    """
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0][0]

    lines = "\n".join(
        f"{i+1}. 제목: {title}  |  채널: {channel}  |  ID: {vid_id}"
        for i, (vid_id, title, channel) in enumerate(candidates)
    )
    desc_hint = f"\n액션 설명: {description}" if description else ""

    prompt = f"""당신은 게임 영상 전문가입니다.
다음 YouTube 검색 결과 중 "{game}" 게임의 "{action_name}" 액션을 가장 잘 보여주는 영상 1개를 고르세요.{desc_hint}

후보 영상:
{lines}

선택 기준 (우선순위 순):
1. 해당 게임·해당 액션이 실제로 등장하는 영상
2. 게임플레이·액션 쇼케이스 (리뷰·튜토리얼보다 우선)
3. 조회 수나 채널 신뢰도가 높을 것 같은 영상

응답 형식: 선택한 영상의 ID(11자리)만 한 줄로 반환. 그 외 어떤 설명도 붙이지 마세요.
예시: dQw4w9WgXcQ"""

    try:
        response = call_claude(prompt, timeout=60).strip()
        # 11자리 YouTube ID 추출
        m = re.search(r'\b([A-Za-z0-9_-]{11})\b', response)
        if m:
            vid_id = m.group(1)
            valid  = {v for v, _, _ in candidates}
            if vid_id in valid:
                return vid_id
        # fallback: 후보 목록에 없으면 첫 번째
        return candidates[0][0]
    except Exception as e:
        err(f"Claude 판별 오류: {e}")
        return candidates[0][0]

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
            print(f"  [git] Push 완료  [{msg}]", flush=True)
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
        wid    = w["id"]
        game   = w.get("game", "")
        action = w.get("actionName", "")
        desc   = w.get("description", "")
        done_ids.add(wid)  # 성공/실패 무관 — 이 세션에선 재시도 안 함

        dim(f"[{wid}] {game} / {action} — 후보 검색 중...")
        candidates = search_candidates(ytdlp, game, action)

        if not candidates:
            err(f"[{wid}] 후보 영상 없음")
            time.sleep(REQ_GAP)
            continue

        dim(f"[{wid}] 후보 {len(candidates)}개 → Claude 판별 중...")
        vid = pick_best_video(candidates, game, action, desc)

        if vid:
            # 선택된 영상 제목 찾기
            chosen_title = next((t for v, t, _ in candidates if v == vid), "")
            w["mediaLinks"]["youtube"] = f"https://www.youtube.com/watch?v={vid}"
            ok(f"[{wid}] {action}")
            dim(f"     → {vid}  {chosen_title[:60]}")
            updated += 1
        else:
            err(f"[{wid}] 영상 선택 실패")

        time.sleep(REQ_GAP)

    if updated:
        save_db(db)
        ok(f"{updated}개 URL 저장됨")
        git_push(updated)

# ─── 메인 ─────────────────────────────────────────────────────────
def main():
    print()
    print(f"  {BOLD}{YEL}📺  YouTube URL 워처{RST}  {DIM}(Claude 판별 모드){RST}")
    print(f"  {DIM}감시 주기: {POLL_SEC}초 · 후보: {CANDIDATES}개 · 간격: {REQ_GAP}초{RST}")
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
