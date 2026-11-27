"""Local status page for the V100. Bind to localhost and open it through an SSH tunnel.

Logs are written under /cache/yue2_panel/logs. Only the scripts listed below can be started.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "public" / "panel_state.json"
LOG_DIR = Path("/cache/yue2_panel/logs") if Path("/cache").is_dir() else ROOT / "public" / "_panel_logs"
HOST = "127.0.0.1"
PORT = 8765

JOBS = {
    "export_listen": {
        "title": "匯出對聽路徑",
        "detail": "只讀原曲和生成 mp3 的路徑與大小，不載入模型。",
        "script": "panel_export_listen.py",
    },
}

LOCK = threading.Lock()
CURRENT = {"job": None, "log": None, "started": None, "exit": None}


def git_text(args):
    completed = subprocess.run(
        ["git", *args], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, check=False)
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def artifact_rows():
    rows = []
    pointer = Path("/cache/yue2_outputs/suno_prep/000/audio.path")
    original = Path(pointer.read_text(encoding="utf-8").strip()) if pointer.is_file() else pointer
    generated = Path("/cache/yue2_outputs/suno_free/suno_013117_free/audio.mp3")
    for label, path in (("原曲", original), ("無譜生成", generated)):
        rows.append({
            "label": label,
            "path": str(path),
            "exists": path.is_file(),
            "bytes": path.stat().st_size if path.is_file() else 0,
        })
    return rows


def narrative():
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"updated": "", "progress": [], "next": []}


def log_rows():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    files = [path for path in LOG_DIR.glob("*.log") if path.is_file()]
    files.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return [{
        "name": path.name,
        "bytes": path.stat().st_size,
        "mtime": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
    } for path in files[:20]]


def status_payload():
    with LOCK:
        running = None if CURRENT["job"] is None else {
            "id": CURRENT["job"],
            "log": CURRENT["log"],
            "started": CURRENT["started"],
            "exit": CURRENT["exit"],
        }
    dirty = [line for line in git_text(["status", "--porcelain"]).splitlines() if line.strip()]
    return {
        "branch": git_text(["rev-parse", "--abbrev-ref", "HEAD"]) or "unknown",
        "head": git_text(["rev-parse", "--short", "HEAD"]) or "unknown",
        "dirty_count": len(dirty),
        "artifacts": artifact_rows(),
        "narrative": narrative(),
        "jobs": [{"id": key, **{name: value[name] for name in ("title", "detail")}} for key, value in JOBS.items()],
        "running": running,
        "logs": log_rows(),
    }


def run_job(job_id, log_name):
    job = JOBS[job_id]
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / log_name
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    env["PYTHONUNBUFFERED"] = "1"
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    with log_path.open("w", encoding="utf-8") as handle:
        handle.write(f"job {job_id}\n")
        handle.flush()
        completed = subprocess.run(
            [sys.executable, str(ROOT / "public" / job["script"])],
            cwd=ROOT, env=env, stdout=handle, stderr=subprocess.STDOUT, check=False)
    with LOCK:
        CURRENT["exit"] = completed.returncode
        if CURRENT["log"] == log_name:
            CURRENT["job"] = None


def start_job(job_id):
    if job_id not in JOBS:
        return 404, {"error": "unknown job"}
    with LOCK:
        if CURRENT["job"] is not None:
            return 409, {"error": "a job is already running", "job": CURRENT["job"]}
        log_name = datetime.now().strftime("%Y%m%d-%H%M%S") + f"_{job_id}.log"
        CURRENT["job"] = job_id
        CURRENT["log"] = log_name
        CURRENT["started"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        CURRENT["exit"] = None
    threading.Thread(target=run_job, args=(job_id, log_name), daemon=True).start()
    return 202, {"started": job_id, "log": log_name}


PAGE = """<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>YuE2 V100</title>
<style>
  :root { color-scheme: light; --ink:#1c1915; --muted:#5c564c; --line:#e4ddd2; --paper:#f7f4ee; --card:#fffdf9; --accent:#0f6e56; }
  * { box-sizing: border-box; }
  body { margin:0; font:16px/1.5 "Iowan Old Style", Palatino, "Songti SC", serif; color:var(--ink); background:var(--paper); }
  main { max-width:980px; margin:0 auto; padding:32px 20px 64px; }
  h1 { font-size:32px; margin:0 0 4px; }
  h2 { font-size:18px; margin:0 0 12px; }
  p, li { margin:0; }
  .sub { color:var(--muted); margin-bottom:24px; }
  .grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(260px, 1fr)); gap:16px; }
  section { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:18px; margin-bottom:16px; }
  ul { padding-left:18px; display:grid; gap:8px; }
  code { font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size:13px; }
  button, a.button { appearance:none; border:0; background:var(--accent); color:white; border-radius:999px; padding:10px 16px; font:600 15px/1 sans-serif; cursor:pointer; text-decoration:none; display:inline-block; }
  button:disabled { background:#b7b1a7; cursor:wait; }
  .job { display:flex; justify-content:space-between; gap:16px; align-items:center; padding:12px 0; border-top:1px solid var(--line); }
  .job p { color:var(--muted); margin-top:4px; }
  table { width:100%; border-collapse:collapse; }
  td { padding:8px 0; border-top:1px solid var(--line); vertical-align:top; }
  .ok { color:var(--accent); } .miss { color:#9a3412; }
  #note { min-height:1.4em; color:var(--muted); margin-top:8px; }
</style>
</head>
<body>
<main>
  <h1>YuE2 V100</h1>
  <p class="sub" id="revision">讀取中</p>
  <div class="grid">
    <section><h2>代碼狀態</h2><div id="code"></div></section>
    <section><h2>目前進度</h2><ul id="progress"></ul></section>
    <section><h2>下一步</h2><ul id="next"></ul></section>
  </div>
  <section>
    <h2>可執行步驟</h2>
    <div id="jobs"></div>
    <p id="note"></p>
  </section>
  <section>
    <h2>日誌</h2>
    <table id="logs"></table>
  </section>
</main>
<script>
const note = document.getElementById("note");
function esc(value) {
  return String(value).replace(/[&<>"]/g, ch => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;" }[ch]));
}
function list(id, items) {
  document.getElementById(id).innerHTML = (items || []).map(item => `<li>${esc(item)}</li>`).join("");
}
let last = "";
async function refresh() {
  const response = await fetch("/api/status");
  const data = await response.json();
  const key = JSON.stringify(data);
  if (key === last) return;
  last = key;
  document.getElementById("revision").textContent = `${data.branch} @ ${data.head}，未提交 ${data.dirty_count} 個路徑`;
  document.getElementById("code").innerHTML = data.artifacts.map(row =>
    `<p><strong>${esc(row.label)}</strong> <span class="${row.exists ? "ok" : "miss"}">${row.exists ? row.bytes + " bytes" : "不存在"}</span><br><code>${esc(row.path)}</code></p>`
  ).join("");
  list("progress", data.narrative.progress);
  list("next", data.narrative.next);
  const busy = Boolean(data.running);
  document.getElementById("jobs").innerHTML = data.jobs.map(job =>
    `<div class="job"><div><strong>${esc(job.title)}</strong><p>${esc(job.detail)}</p></div>
     <button data-job="${esc(job.id)}" ${busy ? "disabled" : ""}>執行</button></div>`
  ).join("");
  document.querySelectorAll("button[data-job]").forEach(button => button.onclick = () => runJob(button.dataset.job));
  note.textContent = busy ? `正在跑 ${data.running.id}，日誌 ${data.running.log}` : "";
  document.getElementById("logs").innerHTML = data.logs.length ? data.logs.map(row =>
    `<tr><td><code>${esc(row.name)}</code><br>${esc(row.mtime)}，${row.bytes} bytes</td>
     <td><a class="button" href="/download/${encodeURIComponent(row.name)}">下載</a></td></tr>`
  ).join("") : "<tr><td>還沒有日誌</td></tr>";
}
async function runJob(id) {
  note.textContent = "啟動中";
  const response = await fetch("/api/run/" + encodeURIComponent(id), { method: "POST" });
  const data = await response.json();
  note.textContent = response.ok ? `已開始，完成後下載 ${data.log}` : (data.error || "無法啟動");
  refresh();
}
refresh();
setInterval(refresh, 2000);
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def send_json(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = unquote(urlparse(self.path).path)
        if path in ("/", "/index.html"):
            body = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/api/status":
            self.send_json(200, status_payload())
            return
        if path.startswith("/download/"):
            name = Path(path[len("/download/"):]).name
            target = LOG_DIR / name
            if not name.endswith(".log") or not target.is_file():
                self.send_json(404, {"error": "log not found"})
                return
            body = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="{name}"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_json(404, {"error": "not found"})

    def do_POST(self):
        path = unquote(urlparse(self.path).path)
        prefix = "/api/run/"
        if not path.startswith(prefix):
            self.send_json(404, {"error": "not found"})
            return
        code, payload = start_job(path[len(prefix):])
        self.send_json(code, payload)

    def log_message(self, fmt, *args):
        print("[panel]", self.address_string(), fmt % args, flush=True)


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"panel http://{HOST}:{PORT}", flush=True)
    print(f"logs {LOG_DIR}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
