"""Local status page for the V100. Bind to localhost and open it through an SSH tunnel.

Logs are written under /cache/yue2_panel/logs. Only the scripts listed below can be started.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "public" / "panel_state.json"
FLOW_PATH = ROOT / "public" / "panel_flow.json"
QUESTION_PATH = ROOT / "public" / "panel_questions.json"
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
START_HEAD = ""
RESTART = False
SERVER = None
QUIET_LOCK = threading.Lock()
QUIET = {"key": None, "line": None}


def git_text(args):
    completed = subprocess.run(
        ["git", *args], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, check=False)
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def listen_targets():
    pointer = Path("/cache/yue2_outputs/suno_prep/000/audio.path")
    original = Path(pointer.read_text(encoding="utf-8").strip()) if pointer.is_file() else pointer
    generated = Path("/cache/yue2_outputs/suno_free/suno_013117_free/audio.mp3")
    return (("original", "原曲", original), ("generated", "無譜生成", generated))


def artifact_rows():
    rows = []
    for audio_id, label, path in listen_targets():
        rows.append({
            "id": audio_id,
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


def annotate_flow(flow):
    stages = flow.get("stages") or []
    flow["done"] = sum(1 for stage in stages if stage.get("status") == "done")
    flow["total"] = len(stages)
    current = next((stage for stage in stages if stage.get("status") == "current"), None)
    flow["current_title"] = current.get("title") if current else ""
    flow["current_next"] = (current.get("next") or []) if current else []
    return flow


def flow_payload():
    try:
        data = json.loads(FLOW_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {"flows": []}
    flows = data.get("flows")
    if not flows and data.get("stages"):
        flows = [data]
    data["flows"] = [annotate_flow(flow) for flow in flows or []]
    data["current_next"] = []
    for flow in data["flows"]:
        if flow.get("current_next"):
            data["current_next"] = flow["current_next"]
            break
    return data


def question_payload():
    try:
        return json.loads(QUESTION_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"intro": "", "questions": []}


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
        "head_full": git_text(["rev-parse", "HEAD"]),
        "dirty_count": len(dirty),
        "artifacts": artifact_rows(),
        "narrative": narrative(),
        "flow": flow_payload(),
        "questions": question_payload(),
        "jobs": [{"id": key, **{name: value[name] for name in ("title", "detail")}} for key, value in JOBS.items()],
        "running": running,
        "logs": log_rows(),
    }


def read_log(name):
    target = LOG_DIR / Path(name).name
    if target.suffix != ".log" or not target.is_file():
        return None
    return target.read_text(encoding="utf-8", errors="replace")


def watch_git():
    global RESTART
    while True:
        time.sleep(3)
        with LOCK:
            busy = CURRENT["job"] is not None
        if busy or not START_HEAD:
            continue
        head = git_text(["rev-parse", "HEAD"])
        if head and head != START_HEAD:
            print("git moved, restarting panel", flush=True)
            RESTART = True
            if SERVER is not None:
                SERVER.shutdown()
            return


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
  main { max-width:1560px; margin:0 auto; padding:28px 36px 72px; }
  h1 { font-size:32px; margin:0 0 4px; }
  h2 { font-size:18px; margin:0 0 12px; }
  h3 { font-size:16px; margin:0; }
  p, li { margin:0; }
  .sub { color:var(--muted); margin-bottom:20px; }
  .grid { display:grid; grid-template-columns:repeat(3, minmax(0, 1fr)); gap:16px; }
  .players { display:grid; grid-template-columns:1fr 1fr; gap:16px; }
  .player audio { width:100%; margin:10px 0; height:42px; }
  @media (max-width: 900px) {
    .grid { grid-template-columns:1fr; }
  }
  @media (max-width: 700px) {
    .players { grid-template-columns:1fr; }
  }
  section { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:18px; margin-bottom:16px; }
  ul { padding-left:18px; display:grid; gap:8px; }
  code { font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size:13px; display:block; overflow-x:auto; white-space:nowrap; }
  button { appearance:none; border:0; background:var(--accent); color:white; border-radius:999px; padding:10px 16px; font:600 15px/1 sans-serif; cursor:pointer; }
  button.ghost { background:#efeae2; color:var(--ink); }
  pre { white-space:pre-wrap; word-break:break-word; max-height:520px; overflow:auto; background:#1c1915; color:#f7f4ee; border-radius:12px; padding:14px; font:13px/1.45 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
  .logpick { display:flex; flex-wrap:wrap; gap:8px; margin:8px 0 12px; }
  button:disabled { background:#b7b1a7; cursor:wait; }
  .job { display:flex; justify-content:space-between; gap:16px; align-items:center; padding:12px 0; border-top:1px solid var(--line); }
  .job p { color:var(--muted); margin-top:4px; }
  table { width:100%; border-collapse:collapse; }
  td { padding:8px 0; border-top:1px solid var(--line); vertical-align:top; }
  .ok { color:var(--accent); } .miss { color:#9a3412; }
  #note { min-height:1.4em; color:var(--muted); margin-top:8px; }
  .meter { color:var(--muted); margin-bottom:8px; }
  .stage { display:grid; grid-template-columns:88px 1fr; gap:12px; padding:14px 0; border-top:1px solid var(--line); }
  .badge { font:600 12px/1 sans-serif; border-radius:999px; padding:6px 0; text-align:center; height:fit-content; }
  .done { background:#e5f4ef; color:#0f6e56; }
  .current { background:#0f6e56; color:white; }
  .later { background:#f3efe8; color:#5c564c; }
  .blocked { background:#f8e8e2; color:#9a3412; }
  .q { padding:12px 0; border-top:1px solid var(--line); }
  .choice { display:flex; flex-wrap:wrap; gap:8px; margin-top:8px; }
  .choice label { display:flex; gap:6px; align-items:center; background:#f7f4ee; border-radius:999px; padding:6px 12px; }
  .stage p { color:var(--muted); margin-top:4px; }
  .stage.current-row { background:#f3faf7; margin:0 -18px; padding:14px 18px; }
</style>
</head>
<body>
<main>
  <h1>YuE2 V100</h1>
  <p class="sub" id="revision">讀取中</p>
  <section>
    <h2>對聽</h2>
    <p class="meter">直接播放伺服器上的檔案。只比較旋律和段落。</p>
    <div class="players" id="players"></div>
  </section>
  <section>
    <h2>選擇題</h2>
    <p class="meter" id="question-intro"></p>
    <div id="questions"></div>
    <button id="copy-answers" type="button">複製答案</button>
    <p id="answer-note" class="meter"></p>
  </section>
  <div id="flows"></div>
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
    <div class="logpick" id="logpick"></div>
    <button id="copy" type="button">複製完整日誌</button>
    <p id="copy-note" class="meter"></p>
    <pre id="logtext">還沒有日誌</pre>
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
let questionMark = "";
let playerMark = "";
function renderQuestions(payload) {
  const mark = JSON.stringify(payload || {});
  if (mark === questionMark) return;
  questionMark = mark;
  const questions = (payload && payload.questions) || [];
  document.getElementById("question-intro").textContent = (payload && payload.intro) || "";
  document.getElementById("questions").innerHTML = questions.map((question, index) =>
    `<div class="q" data-question="${esc(question.id)}" data-prompt="${esc(question.prompt)}">
      <strong>${index + 1}. ${esc(question.prompt)}</strong>
      <div class="choice">${(question.options || []).map(option =>
        `<label><input type="radio" name="${esc(question.id)}" value="${esc(option.label)}">${esc(option.label)}</label>`
      ).join("")}</div>
    </div>`
  ).join("");
}
function answerText() {
  const lines = ["聽感結論"];
  document.querySelectorAll("[data-question]").forEach(block => {
    const chosen = block.querySelector("input:checked");
    lines.push(block.dataset.prompt + " " + (chosen ? chosen.value : "未選"));
  });
  return lines.join("\n");
}
async function copyAnswers() {
  const text = answerText();
  const answerNote = document.getElementById("answer-note");
  try {
    await navigator.clipboard.writeText(text);
  } catch (error) {
    const area = document.createElement("textarea");
    area.value = text;
    document.body.appendChild(area);
    area.select();
    document.execCommand("copy");
    area.remove();
  }
  answerNote.textContent = "已複製，可以直接貼回來";
}
document.getElementById("copy-answers").onclick = copyAnswers;
function renderFlows(payload) {
  const labels = { done: "已完成", current: "目前", later: "之後", blocked: "受阻" };
  const flows = (payload && payload.flows) || [];
  document.getElementById("flows").innerHTML = flows.map(flow => {
    const meter = flow.total
      ? `已完成 ${flow.done} / ${flow.total}。目前：${flow.current_title || "未標明"}。`
      : "";
    const stages = (flow.stages || []).map((stage, index) =>
      `<div class="stage ${stage.status === "current" ? "current-row" : ""}">
        <div class="badge ${esc(stage.status)}">${labels[stage.status] || esc(stage.status)}</div>
        <div><strong>${index + 1}. ${esc(stage.title)}</strong><p>${esc(stage.detail || "")}</p></div>
      </div>`
    ).join("");
    return `<section><h2>${esc(flow.title)}</h2><p class="meter">${esc(meter)}</p>${stages}</section>`;
  }).join("");
}
function renderPlayers(artifacts) {
  const mark = JSON.stringify(artifacts || []);
  if (mark === playerMark) return;
  playerMark = mark;
  document.getElementById("players").innerHTML = (artifacts || []).map(row =>
    `<div class="player"><h3>${esc(row.label)} <span class="${row.exists ? "ok" : "miss"}">${row.exists ? row.bytes + " bytes" : "不存在"}</span></h3>
     ${row.exists ? `<audio controls preload="none" src="/audio/${esc(row.id)}"></audio>` : ""}
     <code>${esc(row.path)}</code></div>`
  ).join("");
}
let last = "";
let seenHead = "";
let selectedLog = "";
let shownLog = "";
async function showLog(name, bytes) {
  const mark = name + ":" + bytes;
  if (!name) {
    document.getElementById("logtext").textContent = "還沒有日誌";
    shownLog = "";
    return;
  }
  if (mark === shownLog) return;
  shownLog = mark;
  const response = await fetch("/api/log/" + encodeURIComponent(name));
  const payload = await response.json();
  document.getElementById("logtext").textContent = payload.text || "";
}
async function copyLog() {
  const text = document.getElementById("logtext").textContent;
  const copyNote = document.getElementById("copy-note");
  try {
    await navigator.clipboard.writeText(text);
    copyNote.textContent = "已複製 " + text.length + " 字";
  } catch (error) {
    const area = document.getElementById("logtext");
    const range = document.createRange();
    range.selectNodeContents(area);
    const selection = getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
    document.execCommand("copy");
    copyNote.textContent = "已複製 " + text.length + " 字";
  }
}
document.getElementById("copy").onclick = copyLog;
async function refresh() {
  let response;
  try {
    response = await fetch("/api/status");
  } catch (error) {
    return;
  }
  const data = await response.json();
  if (seenHead && data.head_full && data.head_full !== seenHead) {
    location.reload();
    return;
  }
  seenHead = data.head_full || "";
  const key = JSON.stringify(data);
  if (key === last) return;
  last = key;
  document.getElementById("revision").textContent = `${data.branch} @ ${data.head}，未提交 ${data.dirty_count} 個路徑`;
  renderPlayers(data.artifacts);
  renderQuestions(data.questions);
  document.getElementById("code").innerHTML = data.artifacts.map(row =>
    `<p><strong>${esc(row.label)}</strong> <span class="${row.exists ? "ok" : "miss"}">${row.exists ? row.bytes + " bytes" : "不存在"}</span><br><code>${esc(row.path)}</code></p>`
  ).join("");
  list("progress", data.narrative.progress);
  list("next", (data.flow && data.flow.current_next) || data.narrative.next);
  renderFlows(data.flow);
  const busy = Boolean(data.running);
  document.getElementById("jobs").innerHTML = data.jobs.map(job =>
    `<div class="job"><div><strong>${esc(job.title)}</strong><p>${esc(job.detail)}</p></div>
     <button data-job="${esc(job.id)}" ${busy ? "disabled" : ""}>執行</button></div>`
  ).join("");
  document.querySelectorAll("button[data-job]").forEach(button => button.onclick = () => runJob(button.dataset.job));
  note.textContent = busy ? `正在跑 ${data.running.id}` : "";
  if (data.running && data.running.log) selectedLog = data.running.log;
  else if (!selectedLog && data.logs.length) selectedLog = data.logs[0].name;
  document.getElementById("logpick").innerHTML = data.logs.map(row =>
    `<button type="button" class="ghost" data-log="${esc(row.name)}">${esc(row.mtime)}</button>`
  ).join("");
  document.querySelectorAll("button[data-log]").forEach(button => {
    button.onclick = () => {
      selectedLog = button.dataset.log;
      shownLog = "";
      const row = data.logs.find(item => item.name === selectedLog);
      showLog(selectedLog, row ? row.bytes : 0);
    };
  });
  const chosen = data.logs.find(row => row.name === selectedLog);
  showLog(selectedLog, chosen ? chosen.bytes : 0);
}
async function runJob(id) {
  note.textContent = "啟動中";
  const response = await fetch("/api/run/" + encodeURIComponent(id), { method: "POST" });
  const data = await response.json();
  note.textContent = response.ok ? "已開始，輸出會顯示在下方" : (data.error || "無法啟動");
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

    def send_audio(self, file_path):
        if not file_path.is_file():
            self.send_json(404, {"error": "audio not found"})
            return
        size = file_path.stat().st_size
        start, end = 0, size - 1
        status = 200
        range_header = self.headers.get("Range")
        if range_header and range_header.startswith("bytes="):
            bounds = range_header[6:].split(",", 1)[0].split("-", 1)
            if bounds[0]:
                start = int(bounds[0])
            if len(bounds) > 1 and bounds[1]:
                end = int(bounds[1])
            end = min(end, size - 1)
            if start < 0 or start > end or start >= size:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.end_headers()
                return
            status = 206
        length = end - start + 1
        try:
            self.send_response(status)
            self.send_header("Content-Type", "audio/mpeg")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(length))
            if status == 206:
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.end_headers()
            with file_path.open("rb") as handle:
                handle.seek(start)
                remaining = length
                while remaining > 0:
                    chunk = handle.read(min(65536, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            return

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
        if path.startswith("/audio/"):
            audio_id = path[len("/audio/"):]
            chosen = next((item for item in listen_targets() if item[0] == audio_id), None)
            if chosen is None:
                self.send_json(404, {"error": "unknown audio"})
                return
            self.send_audio(chosen[2])
            return
        if path.startswith("/api/log/"):
            text = read_log(path[len("/api/log/"):])
            if text is None:
                self.send_json(404, {"error": "log not found"})
                return
            self.send_json(200, {"text": text})
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
        message = f"{self.address_string()} {fmt % args}"
        stamp = datetime.now().strftime("%H:%M:%S")
        line = f"[panel] {stamp} {message}"
        with QUIET_LOCK:
            previous = QUIET["line"]
            same = QUIET["key"] == message
            QUIET["key"] = message
            QUIET["line"] = line
            if previous is None:
                print(line, end="", flush=True)
            elif same:
                pad = max(0, len(previous) - len(line))
                print("\r" + line + (" " * pad), end="", flush=True)
            else:
                print("\n" + line, end="", flush=True)


class PanelServer(ThreadingHTTPServer):
    allow_reuse_address = True


def main():
    global START_HEAD, SERVER
    START_HEAD = git_text(["rev-parse", "HEAD"])
    SERVER = PanelServer((HOST, PORT), Handler)
    threading.Thread(target=watch_git, daemon=True).start()
    print(f"panel http://{HOST}:{PORT}", flush=True)
    print(f"logs {LOG_DIR}", flush=True)
    try:
        SERVER.serve_forever()
    except KeyboardInterrupt:
        return
    SERVER.server_close()
    if RESTART:
        os.execv(sys.executable, [sys.executable, *sys.argv])


if __name__ == "__main__":
    main()
