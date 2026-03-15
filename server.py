"""
Weapon Action DB — 로컬 개발 서버
127.0.0.1:4200 에만 바인드 (외부 접근 차단)

정적 파일 서빙 + /api/collect 수집 API (SSE 스트리밍)
"""

import http.server
import json
import math
import os
import re
import socketserver
import subprocess
import sys
import webbrowser
from pathlib import Path

HOST     = "127.0.0.1"
PORT     = 4200
BASE_DIR = Path(__file__).parent

# ANSI 코드 제거 (collect.py 출력 클린업용)
ANSI = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

CATEGORIES = [
    "대검", "카타나", "쌍검", "창", "도끼",
    "낫", "해머", "채찍", "권투", "활", "1H검", "마법", "방패",
]

# ─── 핸들러 ───────────────────────────────────────────────────────
class Handler(http.server.SimpleHTTPRequestHandler):

    # ── 로깅
    def log_message(self, format, *args):
        try:
            line   = args[0] if args else ""
            if not isinstance(line, str):
                return  # log_error 등 비-HTTP 로그는 무시
            method = line.split(" ")[0]
            path   = line.split(" ")[1] if " " in line else "-"
            code   = args[1] if len(args) > 1 else "-"
            color  = "\033[32m" if str(code).startswith("2") \
                else "\033[33m" if str(code).startswith("3") \
                else "\033[31m"
            print(f"  {color}{code}\033[0m  {method} {path}")
        except Exception:
            pass

    # ── CORS + 캐시 헤더 (정적 파일용)
    def end_headers(self):
        if not self.path.startswith("/api/"):
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Access-Control-Allow-Origin",  f"http://{HOST}:{PORT}")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    # ── send_error 오버라이드 (소켓 끊김 무시)
    def send_error(self, code, message=None, explain=None):
        try:
            super().send_error(code, message, explain)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

    # ── OPTIONS (CORS preflight)
    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    # ── GET 라우팅
    def do_GET(self):
        if self.path.startswith("/.well-known/"):
            self.send_response(204)
            self.end_headers()
            return
        if self.path == "/api/categories":
            self._send_json({"categories": CATEGORIES})
        elif self.path == "/api/db-stats":
            self._db_stats()
        elif self.path.startswith("/data/weapons.json"):
            # weapons.json은 항상 최신 버전 제공 (캐시 금지)
            self._serve_weapons_json()
        else:
            super().do_GET()

    def _serve_weapons_json(self):
        try:
            path = BASE_DIR / "data" / "weapons.json"
            with open(path, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_error(500, str(e))

    # ── POST 라우팅
    def do_POST(self):
        if self.path == "/api/collect":
            self._handle_collect()
        elif self.path == "/api/login":
            self._handle_login()
        else:
            self.send_error(404, "Not found")

    # ── DB 통계
    def _db_stats(self):
        try:
            db_path = BASE_DIR / "data" / "weapons.json"
            with open(db_path, encoding="utf-8") as f:
                db = json.load(f)
            self._send_json({
                "count":    len(db["weapons"]),
                "updated":  db.get("lastUpdated", ""),
                "categories": list({w["weaponCategory"] for w in db["weapons"]}),
                "games":     list({w["game"] for w in db["weapons"]}),
            })
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    # ── JSON 응답 헬퍼
    def _send_json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ── SSE 이벤트 전송 헬퍼 (False = 클라이언트 끊김)
    def _sse(self, data: str, event: str = "message") -> bool:
        try:
            clean = data.replace("\n", " ").replace("\r", "")
            msg = f"event: {event}\ndata: {clean}\n\n"
            self.wfile.write(msg.encode("utf-8"))
            self.wfile.flush()
            return True
        except (BrokenPipeError, ConnectionResetError, OSError):
            return False

    # ── collect.py 1배치 실행 헬퍼
    # 반환: (client_alive, items_collected, proc_ok)
    def _run_one_batch(self, args) -> tuple:
        batch_collected = 0
        try:
            proc = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                cwd=str(BASE_DIR),
            )
            for raw_line in iter(proc.stdout.readline, ""):
                line = ANSI.sub("", raw_line).rstrip()
                if not line:
                    continue
                if line.strip().startswith("[git]"):
                    event = "git"  # git push 결과 — 수집 카운트 제외
                elif line.strip().startswith("✓"):
                    event = "ok"
                    batch_collected += 1
                elif line.strip().startswith("✗"):
                    event = "error"
                elif "─" in line:
                    event = "sep"
                elif "완료" in line or "저장됨" in line:
                    event = "done-line"
                elif "요청 중" in line or "Claude" in line:
                    event = "wait"
                else:
                    event = "log"
                if not self._sse(line, event):
                    proc.kill()
                    proc.wait()
                    return False, batch_collected, False  # 클라이언트 끊김
            proc.wait()
            return True, batch_collected, proc.returncode == 0
        except Exception as e:
            self._sse(str(e), "collect-error")
            return True, batch_collected, False

    # ── /api/login — Claude 로그인 SSE 스트리밍
    def _handle_login(self):
        self.send_response(200)
        self.send_header("Content-Type",  "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        collect_py = str(BASE_DIR / "collect.py")
        args = [sys.executable, collect_py, "--login"]

        self._sse("🔑 Claude 로그인 시작...", "start")
        self._sse("브라우저가 자동으로 열립니다. 로그인 후 이 창으로 돌아오세요.", "wait")
        self._sse("─" * 46, "sep")

        try:
            proc = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                cwd=str(BASE_DIR),
            )
            for raw_line in iter(proc.stdout.readline, ""):
                line = ANSI.sub("", raw_line).rstrip()
                if not line:
                    continue
                if line.strip().startswith("✓"):
                    event = "ok"
                elif line.strip().startswith("✗"):
                    event = "error"
                elif "─" in line:
                    event = "sep"
                else:
                    event = "log"
                self._sse(line, event)
            proc.wait()
            if proc.returncode == 0:
                self._sse("0", "login-done")
            else:
                self._sse(str(proc.returncode), "login-error")
        except Exception as e:
            self._sse(str(e), "login-error")

    # ── /api/collect — SSE 스트리밍 (일반 배치 / 무한 모드)
    def _handle_collect(self):
        BATCH_SIZE = 3

        # 요청 파싱
        try:
            length = int(self.headers.get("Content-Length", 0))
            body   = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, ValueError):
            self.send_error(400, "Invalid JSON")
            return

        infinite    = body.get("infinite", False)
        total_count = int(body.get("totalCount", body.get("count", BATCH_SIZE)))
        num_batches = math.ceil(total_count / BATCH_SIZE)

        # SSE 헤더
        self.send_response(200)
        self.send_header("Content-Type",  "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        # 공통 base 인수 (무한 모드에서는 -c 제외 — 루프마다 지정)
        collect_py = str(BASE_DIR / "collect.py")
        base_args  = [sys.executable, collect_py]
        if not infinite and body.get("category"): base_args += ["-c", str(body["category"])]
        if body.get("game"):     base_args += ["-g", str(body["game"])]
        if body.get("mechanic"): base_args += ["-m", str(body["mechanic"])]
        if body.get("query"):    base_args += ["-q", str(body["query"])]
        if body.get("model"):    base_args += ["--model", str(body["model"])]
        if body.get("dryRun"):   base_args += ["--dry-run"]

        model_short = {
            "claude-opus-4-6":           "Opus 4.6",
            "claude-sonnet-4-6":         "Sonnet 4.6",
            "claude-haiku-4-5-20251001": "Haiku 4.5",
        }.get(body.get("model", ""), body.get("model", "Sonnet 4.6"))

        try:
            # ── 무한 모드 ─────────────────────────────────────────
            if infinite:
                self._sse(
                    f"무한 수집 시작 [{model_short}] · 전 카테고리 순환 · 중단 버튼으로 정지",
                    "start"
                )
                cat_idx     = 0
                total_added = 0
                round_num   = 0

                while True:
                    if cat_idx % len(CATEGORIES) == 0:
                        round_num += 1
                        if not self._sse(f"── 라운드 {round_num} · {len(CATEGORIES)}개 카테고리 순환 시작 ──", "sep"):
                            break

                    cat  = CATEGORIES[cat_idx % len(CATEGORIES)]
                    args = base_args + ["-c", cat, "-n", str(BATCH_SIZE)]

                    if not self._sse(f"[{cat}] 수집중 · 누적 {total_added}개", "batch"):
                        break

                    alive, batch_collected, proc_ok = self._run_one_batch(args)
                    if not alive:
                        break  # 사용자가 중단 버튼 클릭
                    if not proc_ok:
                        if not self._sse("이 배치 실패 — 다음 카테고리로 넘어갑니다", "error"):
                            break

                    total_added += batch_collected
                    if not self._sse(str(batch_collected), "batch-done"):
                        break

                    cat_idx += 1

                self._sse(f"무한 수집 중단 · 총 {total_added}개 추가됨", "done-line")
                self._sse(str(total_added), "collect-done")

            # ── 일반 배치 모드 ────────────────────────────────────
            else:
                parts = [v for k, v in [
                    ("category", body.get("category")),
                    ("game",     body.get("game")),
                    ("mechanic", body.get("mechanic")),
                    ("query",    body.get("query")),
                ] if v]
                label = f"{' · '.join(parts) if parts else '전체'} [{model_short}]"
                self._sse(f"수집 시작: {label} — 목표 {total_count}개 ({num_batches}배치)", "start")

                collected_total = 0
                empty_streak    = 0

                for batch_idx in range(num_batches):
                    remaining  = total_count - collected_total
                    this_batch = min(BATCH_SIZE, remaining)
                    args       = base_args + ["-n", str(this_batch)]

                    if not self._sse("─" * 46, "sep"): return
                    if not self._sse(
                        f"배치 {batch_idx + 1}/{num_batches}  ({collected_total}/{total_count}개 완료)",
                        "batch"
                    ): return

                    alive, batch_collected, proc_ok = self._run_one_batch(args)
                    if not alive:
                        return
                    if not proc_ok:
                        self._sse(str(1), "collect-error")
                        return

                    collected_total += batch_collected
                    if not self._sse(str(batch_collected), "batch-done"): return

                    if batch_collected == 0:
                        empty_streak += 1
                        if empty_streak >= 2:
                            self._sse("빈 배치 2회 연속 — 수집 종료", "error")
                            break
                    else:
                        empty_streak = 0

                self._sse(f"전체 수집 완료 · 총 {collected_total}개 추가됨", "done-line")
                self._sse(str(collected_total), "collect-done")

        except Exception as e:
            self._sse(str(e), "collect-error")


# ─── 서버 시작 ────────────────────────────────────────────────────
def main():
    os.chdir(BASE_DIR)

    # Windows 콘솔 UTF-8 강제 (이모지 인코딩 오류 방지)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print()
    print("  \033[33m[Weapon Action DB]\033[0m")
    print("  ─────────────────────────────────")
    print(f"  \033[32m서버 시작\033[0m  →  http://{HOST}:{PORT}")
    print(f"  \033[90m외부 접근 차단 (127.0.0.1 전용)\033[0m")
    print(f"  \033[90mAPI: POST http://{HOST}:{PORT}/api/collect\033[0m")
    print("  종료: Ctrl+C")
    print("  ─────────────────────────────────")
    print()

    try:
        with socketserver.ThreadingTCPServer((HOST, PORT), Handler) as httpd:
            httpd.allow_reuse_address = True
            httpd.daemon_threads = True  # 서버 종료 시 수집 스레드도 정리
            webbrowser.open(f"http://{HOST}:{PORT}")
            httpd.serve_forever()

    except OSError as e:
        if e.errno in (98, 10048):  # Address already in use
            print(f"\n  \033[31m오류: 포트 {PORT}가 이미 사용 중입니다.\033[0m")
        else:
            print(f"\n  \033[31m오류: {e}\033[0m")
        sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n  서버 종료됨\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
