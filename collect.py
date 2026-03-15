"""
Weapon Action DB — 레퍼런스 수집기
Claude Code CLI(이미 설치된 `claude` 명령)를 사용합니다.
별도 API 키 불필요, 추가 과금 없음.

사용법:
  python collect.py -c 카타나 -n 5
  python collect.py -g "Sekiro" -n 3
  python collect.py -m parry -n 6
  python collect.py -c 대검 -g "Elden Ring" -n 3
  python collect.py -q "공중 콤보 메카닉이 있는 무기들" -n 4
  python collect.py -c 활 --dry-run
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

# Windows cp949 터미널에서 UTF-8 이모지 출력 보장
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# ─── 설정 ─────────────────────────────────────────────────────────
DB_PATH = Path(__file__).parent / "data" / "weapons.json"

CATEGORY_PREFIX = {
    "대검": "gs", "카타나": "kt", "쌍검": "db", "창": "sp",
    "도끼": "ax", "낫":  "sc", "해머": "hm", "채찍": "wh",
    "권투": "ft", "활":  "bw", "1H검": "sw", "마법": "mg",
    "방패": "sh", "기타": "et",
}

# ─── DB 유틸 ──────────────────────────────────────────────────────
def load_db():
    with open(DB_PATH, encoding="utf-8") as f:
        return json.load(f)

def save_db(data):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def next_id(db, category):
    prefix = CATEGORY_PREFIX.get(category, "et")
    nums = [
        int(w["id"].split("-")[1])
        for w in db["weapons"]
        if re.match(rf"^{re.escape(prefix)}-\d+$", w["id"])
    ]
    return f"{prefix}-{(max(nums) + 1 if nums else 1):03d}"

def yt_search_url(game, action_name):
    q = quote_plus(f"{game} {action_name} gameplay")
    return f"https://www.youtube.com/results?search_query={q}"

def git_auto_push(count, label=""):
    """weapons.json을 자동으로 git commit & push"""
    repo_dir = Path(__file__).parent
    parts = [f"auto: add {count} entr{'y' if count == 1 else 'ies'}"]
    if label:
        parts.append(f"({label})")
    commit_msg = " ".join(parts)
    try:
        subprocess.run(
            ["git", "add", "data/weapons.json"],
            cwd=str(repo_dir), check=True, capture_output=True
        )
        r = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=str(repo_dir), capture_output=True, text=True
        )
        if r.returncode != 0:
            out = r.stdout + r.stderr
            if "nothing to commit" in out:
                return  # 변경 없음 — 정상
            perr(f"git commit 실패: {(r.stderr or r.stdout).strip()[:200]}")
            return
        r2 = subprocess.run(
            ["git", "push"],
            cwd=str(repo_dir), capture_output=True, text=True
        )
        if r2.returncode != 0:
            # push 충돌 시 rebase 후 재시도
            subprocess.run(
                ["git", "pull", "--rebase", "origin", "main"],
                cwd=str(repo_dir), capture_output=True
            )
            r2 = subprocess.run(
                ["git", "push"],
                cwd=str(repo_dir), capture_output=True, text=True
            )
        if r2.returncode == 0:
            print(f"  [git] Push 완료  [{commit_msg}]", flush=True)
        else:
            perr(f"git push 실패: {r2.stderr.strip()[:200]}")
    except FileNotFoundError:
        perr("git 명령을 찾을 수 없습니다 (PATH 확인)")
    except Exception as e:
        perr(f"git 오류: {e}")

# ─── Claude CLI 호출 ──────────────────────────────────────────────
def find_claude_exe():
    """
    Claude Code CLI 실행 파일 경로를 자동으로 찾습니다.
    Windows: %APPDATA%\\Claude\\claude-code\\*\\claude.exe
    기타: PATH에서 claude 탐색
    """
    import glob

    # 1) PATH에서 claude 또는 claude.exe
    for name in ("claude", "claude.exe"):
        found = subprocess.run(
            f"where {name}" if os.name == "nt" else f"which {name}",
            capture_output=True, text=True, shell=True
        )
        if found.returncode == 0 and found.stdout.strip():
            return found.stdout.strip().splitlines()[0]

    # 2) Windows 전용: AppData에서 claude.exe 검색
    if os.name == "nt":
        appdata = os.environ.get("APPDATA", "")
        pattern = os.path.join(appdata, "Claude", "claude-code", "*", "claude.exe")
        matches = sorted(glob.glob(pattern), reverse=True)  # 최신 버전 우선
        if matches:
            return matches[0]

    return None

_CLAUDE_EXE = None  # 캐시

def get_claude_exe():
    global _CLAUDE_EXE
    if _CLAUDE_EXE is None:
        _CLAUDE_EXE = find_claude_exe()
    return _CLAUDE_EXE

def check_claude_cli():
    """claude 명령이 사용 가능한지 확인"""
    exe = get_claude_exe()
    if not exe:
        return False
    try:
        env = os.environ.copy()
        env["PATH"] = os.path.dirname(exe) + os.pathsep + env.get("PATH", "")
        result = subprocess.run(
            [exe, "--version"],
            capture_output=True, text=True, timeout=10, env=env
        )
        return result.returncode == 0
    except Exception:
        return False

def call_claude(prompt, timeout=300, model=None):
    """
    claude --print 으로 프롬프트를 전달하고 응답을 받습니다.
    Claude Code CLI의 기존 구독을 사용합니다 (API 키 불필요).
    """
    exe = get_claude_exe()
    if not exe:
        raise RuntimeError(
            "claude 실행 파일을 찾을 수 없습니다.\n"
            f"  탐색 위치: %APPDATA%\\Claude\\claude-code\\*\\claude.exe\n"
            f"  직접 경로를 collect.py의 find_claude_exe() 함수에 추가하세요."
        )
    # claude.exe 디렉토리를 PATH 앞에 추가
    # (claude.exe가 내부적으로 자신을 재호출할 때 PATH에서 못 찾는 문제 방지)
    env = os.environ.copy()
    env["PATH"] = os.path.dirname(exe) + os.pathsep + env.get("PATH", "")
    env.pop("CLAUDECODE", None)   # 중첩 세션 오류 방지 (Claude Code 내부에서 실행 시)

    cmd = [exe, "--print"]
    if model:
        cmd += ["--model", model]
    cmd.append(prompt)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            cwd=str(Path(__file__).parent),
            env=env,
        )

        if result.returncode != 0:
            err_out = result.stderr.strip() or result.stdout.strip() or "(출력 없음)"
            raise RuntimeError(
                f"claude 오류 (코드 {result.returncode}):\n{err_out[:600]}"
            )

        return result.stdout.strip()

    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Claude 응답 시간 초과 ({timeout}초). --count를 3 이하로 줄이거나 다시 시도하세요.")

# ─── 프롬프트 ─────────────────────────────────────────────────────
SCHEMA = """{
  "weaponCategory": "대검|카타나|쌍검|창|도끼|낫|해머|채찍|권투|활|1H검|마법",
  "weaponSubtype": "구체적인 무기 이름",
  "game": "정확한 게임 타이틀 (영문 공식명)",
  "developer": "개발사",
  "actionName": "액션 이름 (한글명 + 원어명 병기)",
  "actionType": "기본 공격|무기술|차지|카운터|패리|콤보|특수기|...",
  "description": "이 액션의 구체적인 동작을 2~3문장으로 설명",
  "motionType": ["slash|thrust|overhead|sweep|spin|charge|dodge-cancel|parry|counter|throw|combo|leap 중 해당하는 것들"],
  "element": {
    "type": "없음|불|얼음|번개|어둠|신성|독|출혈|중력|비전|바람|땅|물|기타",
    "effectColor": ["red", "orange", "blue", "yellow", "purple", "white", "gold", "green", "black", "cyan" 등 이펙트 대표 색상들],
    "effectStyle": ["slash-trail", "particle", "aura", "explosion", "beam", "wave", "shimmer", "none" 등 시각적 연출 방식]
  },
  "mechanics": {
    "startupSpeed": "very-fast|fast|medium|slow|very-slow",
    "range": "short|short-medium|medium|medium-long|long|very-long",
    "staggerPower": "very-low|low|medium|high|very-high|continuous",
    "comboRole": ["opener|extender|finisher|launcher|ender|punish 중 해당하는 것들"],
    "specialProperties": ["knockdown", "poise-breaking", "gap-closer", ... 특수 속성들],
    "resourceCost": "스태미나|FP|없음|쿨다운|기(Ki)|...",
    "frameApprox": {
      "startup": "~Xf 또는 추정값",
      "active": "~Xf 또는 추정값",
      "recovery": "~Xf 또는 추정값"
    }
  },
  "designNotes": "이 액션이 왜 잘 설계되었는지, 어떤 디자인 원칙이 담겼는지 3~5문장",
  "mediaLinks": {
    "youtube": "https://www.youtube.com/watch?v=VIDEO_ID 형식의 실제 영상 URL. 해당 게임의 대표적인 플레이 영상이나 기술 쇼케이스 URL을 최대한 기입. 확실하지 않으면 null (search_query URL 사용 금지)",
    "images": ["위키/공식 사이트 이미지 URL (없으면 빈 배열)"],
    "wiki": "게임 위키 URL (Fextralife, 공식 위키 등. 없으면 null)",
    "gif": "GIF 이미지 URL (없으면 null)"
  },
  "tags": ["관련 태그 5~10개 (영어 소문자, hyphen)"],
  "applicableWeapons": ["이 메카닉을 적용 가능한 무기 유형들"]
}"""

def build_prompt(category, game, mechanic, query, count, existing_games):
    conditions = []
    if category: conditions.append(f"무기 카테고리: **{category}**")
    if game:     conditions.append(f"게임: **{game}**")
    if mechanic: conditions.append(f"메카닉/특성: **{mechanic}**")
    if query:    conditions.append(f"자유 조건: **{query}**")

    already = ""
    if existing_games:
        top = sorted(existing_games)[:12]
        already = f"\n\n이미 DB에 포함된 게임: {', '.join(top)}\n가능하면 다양한 게임에서 수집해주세요."

    return f"""당신은 액션 게임 무기 액션 전문 연구자입니다.

아래 조건에 맞는 게임 무기 레퍼런스 **{count}개**를 수집하여 JSON 배열로 반환하세요.

## 수집 조건
{chr(10).join(conditions)}{already}

## 각 항목의 JSON 스키마
```json
{SCHEMA}
```

## 규칙
1. **실제 존재하는 게임의 정확한 액션**만 작성 (창작 금지)
2. `mediaLinks.youtube`: **반드시 `https://www.youtube.com/watch?v=VIDEO_ID` 형식**만 허용. 게임 플레이/기술 쇼케이스 영상 URL을 적극적으로 기입. 확실하지 않으면 null (검색 URL 절대 금지)
3. `mediaLinks.wiki`: Fextralife(예: https://eldenring.wiki.fextralife.com/...) 등 실제 URL
4. `designNotes`: 디자이너 관점에서 UX 원칙, 리스크-리워드 구조, 피드백 설계 구체적으로
5. `tags`: 영어 소문자 + hyphen (예: gap-closer, bleed-buildup, crowd-control)

## 응답 형식
반드시 아래 형식으로만 응답하세요 (다른 설명 없이 JSON만):

```json
[
  {{ 엔트리1 }},
  {{ 엔트리2 }}
]
```"""

# ─── 파싱 ─────────────────────────────────────────────────────────
def parse_entries(text):
    # 코드블록 안의 JSON 배열 추출
    m = re.search(r'```(?:json)?\s*(\[[\s\S]*?\])\s*```', text)
    if m:
        return json.loads(m.group(1))
    # 코드블록 없이 그냥 배열
    m = re.search(r'\[[\s\S]*\]', text)
    if m:
        return json.loads(m.group(0))
    raise ValueError("JSON 배열을 찾을 수 없습니다")

# ─── 출력 유틸 ────────────────────────────────────────────────────
BOLD  = "\033[1m"
GREEN = "\033[32m"
YEL   = "\033[33m"
DIM   = "\033[90m"
RED   = "\033[31m"
CYAN  = "\033[36m"
RST   = "\033[0m"

def pok(msg):  print(f"  {GREEN}✓{RST} {msg}")
def perr(msg): print(f"  {RED}✗{RST} {msg}")
def pdim(msg): print(f"  {DIM}{msg}{RST}")

# ─── 로그인 ───────────────────────────────────────────────────────
def do_login():
    """Claude 계정 로그인 — 새 터미널 창에서 claude 실행, /login 입력 안내"""
    exe = get_claude_exe()
    if not exe:
        perr("claude 실행 파일을 찾을 수 없습니다.")
        sys.exit(1)

    print()
    print(f"  {BOLD}{YEL}🔑 Claude 로그인{RST}")
    print(f"  {'─' * 44}")

    try:
        if os.name == "nt":
            # Windows: 새 cmd 창에서 claude 실행
            subprocess.Popen(
                ["cmd", "/c", "start", "cmd", "/k", exe],
                shell=False,
            )
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-a", "Terminal", exe])
        else:
            for term in ("x-terminal-emulator", "gnome-terminal", "xterm"):
                try:
                    subprocess.Popen([term, "-e", exe]); break
                except FileNotFoundError:
                    continue
    except Exception as e:
        perr(f"터미널 창 열기 실패: {e}")
        sys.exit(1)

    print(f"  {GREEN}새 터미널 창이 열렸습니다.{RST}")
    print(f"  터미널에 아래 명령을 입력하세요:")
    print(f"  {CYAN}{BOLD}  /login{RST}")
    print(f"  브라우저에서 로그인 완료 후 터미널을 닫아도 됩니다.")
    print(f"  {'─' * 44}")
    print()


# ─── 메인 ─────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        prog="collect.py",
        description="⚔️  Weapon Action DB — 레퍼런스 수집기 (Claude Code CLI 사용)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python collect.py -c 카타나 -n 5
  python collect.py -g "Sekiro" -n 3
  python collect.py -m parry -n 6
  python collect.py -c 대검 -g "Elden Ring" -n 3
  python collect.py -q "공중 콤보 메카닉이 있는 무기들" -n 4
  python collect.py -c 활 --dry-run
        """
    )
    parser.add_argument("-c", "--category",
                        choices=list(CATEGORY_PREFIX.keys()),
                        metavar=f"[{'|'.join(CATEGORY_PREFIX.keys())}]",
                        help="무기 카테고리")
    parser.add_argument("-g", "--game",     help="게임 이름 (예: Sekiro, Elden Ring)")
    parser.add_argument("-m", "--mechanic", help="메카닉 키워드 (예: parry, charge, bleed)")
    parser.add_argument("-q", "--query",    help="자유 검색어")
    parser.add_argument("-n", "--count",    type=int, default=3,
                        help="수집할 레퍼런스 수 (기본: 3, 최대: 8)")
    parser.add_argument("--dry-run",        action="store_true",
                        help="저장 없이 미리보기만")
    parser.add_argument("--model",          default=None,
                        metavar="MODEL_ID",
                        help="사용할 모델 (예: claude-opus-4-6, claude-sonnet-4-6, claude-haiku-4-5-20251001)")
    parser.add_argument("--login",          action="store_true",
                        help="Claude 계정 로그인 (브라우저 인증)")
    args = parser.parse_args()

    # 로그인 모드
    if args.login:
        do_login()
        return

    if not any([args.category, args.game, args.mechanic, args.query]):
        parser.print_help()
        print()
        perr("최소 하나의 조건을 지정하세요: -c, -g, -m, -q")
        print()
        sys.exit(1)

    args.count = min(max(1, args.count), 8)

    # ── 헤더
    print()
    print(f"  {BOLD}{YEL}⚔️  Weapon Action DB — 레퍼런스 수집기{RST}")
    print(f"  {DIM}Claude Code CLI 사용 (추가 과금 없음){RST}")
    print(f"  {'─' * 44}")
    if args.category: print(f"  카테고리 : {CYAN}{args.category}{RST}")
    if args.game:     print(f"  게임     : {CYAN}{args.game}{RST}")
    if args.mechanic: print(f"  메카닉   : {CYAN}{args.mechanic}{RST}")
    if args.query:    print(f"  검색어   : {CYAN}{args.query}{RST}")
    print(f"  수집 수  : {args.count}개")
    if args.model:    print(f"  모델     : {CYAN}{args.model}{RST}")
    if args.dry_run:  print(f"  모드     : {YEL}DRY RUN{RST}")
    print(f"  {'─' * 44}")

    # ── claude CLI 확인
    if not check_claude_cli():
        print()
        perr("'claude' 명령을 찾을 수 없습니다.")
        pdim("Claude Code CLI가 설치되어 있고 PATH에 등록되어 있는지 확인하세요.")
        print()
        sys.exit(1)

    # ── DB 로드
    db = load_db()
    existing_games = {w["game"] for w in db["weapons"]}
    pdim(f"현재 DB: {len(db['weapons'])}개 엔트리")

    # ── Claude 호출
    prompt = build_prompt(
        args.category, args.game, args.mechanic, args.query,
        args.count, existing_games
    )

    print(f"\n  {DIM}Claude에게 요청 중... (최대 3분 소요){RST}", flush=True)
    try:
        response_text = call_claude(prompt, model=args.model)
    except RuntimeError as e:
        perr(str(e))
        sys.exit(1)

    print(f"  {GREEN}Claude 응답 완료{RST}")

    # ── 파싱
    try:
        entries = parse_entries(response_text)
    except (ValueError, json.JSONDecodeError) as e:
        print()
        perr(f"JSON 파싱 실패: {e}")
        pdim("Claude 응답 (처음 500자):")
        print(response_text[:500])
        sys.exit(1)

    if not entries:
        perr("수집된 항목이 없습니다.")
        sys.exit(1)

    # ── 결과 처리 및 출력
    print()
    print(f"  {'─' * 44}")
    added = []

    for entry in entries:
        cat = entry.get("weaponCategory", args.category or "기타")
        entry["id"] = next_id(db, cat)
        entry["addedDate"] = datetime.now().strftime("%Y-%m-%d")

        # mediaLinks 보정
        ml = entry.setdefault("mediaLinks", {})
        yt = ml.get("youtube") or ""
        # 실제 embed URL이 없으면 검색 URL로 폴백 (나중에 직접 교체 가능)
        if not yt or "results?search_query" in yt or "search_query=" in yt:
            ml["youtube"] = yt_search_url(entry.get("game", ""), entry.get("actionName", ""))
        ml.setdefault("images", [])
        ml.setdefault("wiki", None)
        ml.setdefault("gif", None)

        pok(f"[{entry['id']}] {BOLD}{entry['actionName']}{RST}")
        pdim(f"     {entry.get('game', '-')} / {cat} / {entry.get('actionType', '-')}")
        yt_display = ml['youtube'] or "(영상 없음)"
        pdim(f"     YT {yt_display[:70]}")
        if ml.get("wiki"):   pdim(f"     📖 {ml['wiki']}")
        if ml.get("images"): pdim(f"     🖼️  이미지 {len(ml['images'])}개")
        if ml.get("gif"):    pdim(f"     🎞️  GIF 있음")
        print()

        db["weapons"].append(entry)
        added.append(entry)

    db["lastUpdated"] = datetime.now().strftime("%Y-%m-%d")

    print(f"  {'─' * 44}")
    print(f"  {BOLD}{len(added)}개 수집 완료{RST}")

    if args.dry_run:
        print(f"  {YEL}[DRY RUN] weapons.json에 저장하지 않음{RST}")
    else:
        save_db(db)
        pok(f"weapons.json 저장됨 (총 {len(db['weapons'])}개)")
        label = args.category or args.game or args.mechanic or args.query or ""
        git_auto_push(len(added), label)
    print()


if __name__ == "__main__":
    main()
