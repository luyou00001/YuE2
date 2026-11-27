"""Local status page for the V100. Bind to localhost and open it through an SSH tunnel.

Logs are written under /cache/yue2_panel/logs. Only the scripts listed below can be started.
"""
from __future__ import annotations

import html
import json
import os
import re
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
    "transcribe7": {
        "title": "再轉 7 首",
        "detail": "只轉接下來 7 首並打成前綴，用來確認批量轉譜。不更新權重。",
        "script": "suno_batch7.py",
    },
    "abc_loss8": {
        "title": "計算 8 首樂譜損失",
        "detail": "載入一次 YuE2-3B，計算 000 到 007 的樂譜損失。不更新權重。",
        "script": "suno_abc_loss8.py",
    },
    "free004": {
        "title": "無譜生成第 004 首",
        "detail": "004 的樂譜損失最高，為 0.6875。只用它的歌詞和 style 生成，不餵 ABC。",
        "script": "suno_free_004.py",
    },
    "fit32_probe": {
        "title": "32GB 顯存探針",
        "detail": "只對最後一層做一次反向，印出峰值顯存。不更新權重，不寫進基模。",
        "script": "train_fit32_probe.py",
    },
    "fit32_update": {
        "title": "32GB 小更新",
        "detail": "對 000 到 007 各做一步，只更新最後一層。新權重存到 /cache/yue2_ckpts/fit32-suno8。",
        "script": "train_fit32.py",
    },
    "free004_fit32": {
        "title": "用新權重無譜生成 004",
        "detail": "用 fit32-suno8 的權重，只給第 004 首的歌詞和 style。輸出 suno_004_fit32。",
        "script": "suno_free_004_fit32.py",
    },
    "export_listen": {
        "title": "匯出對聽路徑",
        "detail": "只讀原曲和生成 mp3 的路徑與大小，不載入模型。",
        "script": "panel_export_listen.py",
    },
}

LOCK = threading.Lock()
CURRENT = {"job": None, "log": None, "started": None, "exit": None, "finished_id": None}
START_HEAD = ""
RESTART = False
SERVER = None
QUIET_LOCK = threading.Lock()
QUIET = {"key": None, "line": None}


def git_text(args):
    try:
        completed = subprocess.run(
            ["git", *args], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, check=False, timeout=2)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def listen_targets():
    pointer = Path("/cache/yue2_outputs/suno_prep/004/audio.path")
    original = Path(pointer.read_text(encoding="utf-8").strip()) if pointer.is_file() else pointer
    base = Path("/cache/yue2_outputs/suno_free/suno_004_free/audio.mp3")
    updated = Path("/cache/yue2_outputs/suno_free/suno_004_fit32/audio.mp3")
    return (
        ("original", "004 原曲", original),
        ("base", "004 基模", base),
        ("fit32", "004 新權重", updated),
    )


def artifact_rows():
    rows = []
    try:
        targets = listen_targets()
    except OSError:
        targets = ()
    for audio_id, label, path in targets:
        try:
            exists = path.is_file()
            size = path.stat().st_size if exists else 0
        except OSError:
            exists, size = False, 0
        rows.append({
            "id": audio_id,
            "label": label,
            "path": str(path),
            "exists": exists,
            "bytes": size,
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
    try:
        with LOCK:
            running = None if CURRENT["job"] is None else {
                "id": CURRENT["job"],
                "log": CURRENT["log"],
                "started": CURRENT["started"],
                "exit": CURRENT["exit"],
            }
            finished_id = CURRENT.get("finished_id")
            finished_exit = CURRENT["exit"]
            finished_log = CURRENT["log"]
        dirty = [line for line in git_text(["status", "--porcelain"]).splitlines() if line.strip()]
        task_html, visible_jobs = pipeline_view()
        sync_head, sync_steps = sync_parts()
        tree_html, tree_mark, tree_count = code_tree()
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
            "task_html": task_html,
            "gpu_html": render_gpus(gpu_rows()),
            "jobs_html": render_jobs(visible_jobs),
            "sync_head": sync_head,
            "sync_steps": sync_steps,
            "tree_html": tree_html,
            "tree_mark": tree_mark,
            "tree_count": tree_count,
            "run_detail": run_detail(),
            "finished_job": None if running else finished_id,
            "finished_exit": None if running else finished_exit,
            "finished_log": finished_log or "",
            "show_copy_log": copy_log_visible(),
        }
    except Exception as exc:
        return {
            "branch": "error",
            "head": type(exc).__name__,
            "head_full": "",
            "dirty_count": 0,
            "artifacts": [],
            "narrative": {"progress": [str(exc)], "next": []},
            "flow": {"flows": [], "current_next": []},
            "questions": {"intro": "", "questions": []},
            "jobs": [],
            "running": None,
            "logs": [],
            "task_html": "",
            "gpu_html": "",
            "jobs_html": "",
            "sync_head": "",
            "sync_steps": "",
            "tree_html": "",
            "tree_mark": "",
            "tree_count": "",
            "run_detail": "",
            "finished_job": None,
            "finished_exit": None,
            "finished_log": "",
            "show_copy_log": False,
            "live": "",
            "error": f"{type(exc).__name__}: {exc}",
        }


def brief_progress(line):
    text = line.strip()
    if text.startswith("[YuE2] "):
        text = text[7:]
    if "elapsed " in text:
        stage, _, rest = text.partition(": ")
        elapsed = rest.split("elapsed ", 1)[1].split()[0]
        return f"{stage}  {elapsed}"
    return text


def run_detail():
    with LOCK:
        job = CURRENT["job"]
        log_name = CURRENT["log"]
    if not job:
        return ""
    latest = ""
    for line in (read_log(log_name) or "").splitlines():
        line = line.strip()
        if not line or line.startswith("job "):
            continue
        latest = brief_progress(line)
    if not latest:
        return f"正在跑 {job}"
    return f"正在跑 {job}　{latest}"


def read_log(name):
    if not name:
        return None
    target = LOG_DIR / Path(name).name
    if target.suffix != ".log" or not target.is_file():
        return None
    return target.read_text(encoding="utf-8", errors="replace")


def gpu_rows():
    try:
        completed = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,name,memory.used,memory.total,utilization.gpu",
             "--format=csv,noheader,nounits"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=2, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return []
    if completed.returncode != 0:
        return []
    rows = []
    for line in completed.stdout.splitlines():
        parts = [item.strip() for item in line.split(",")]
        if len(parts) < 5:
            continue
        rows.append({
            "index": parts[0], "name": parts[1],
            "memory_used": parts[2], "memory_total": parts[3], "util": parts[4],
        })
    return rows


def task_summary():
    with LOCK:
        job = CURRENT["job"]
        log_name = CURRENT["log"]
        started = CURRENT["started"]
        exit_code = CURRENT["exit"]
    logs = log_rows()
    if not log_name and logs:
        log_name = logs[0]["name"]
    text = read_log(log_name) or ""
    lines = text.splitlines()
    ready = [line for line in lines if line.startswith("ready=")]
    stage = next((line for line in reversed(lines) if line.startswith("stage ")), "")
    done_line = next((line for line in reversed(lines) if line.startswith("batch7_done=")), "")
    if job:
        head = f"狀態：進行中 {job}"
        if started:
            head += f"，開始於 {started}"
    elif done_line:
        head = f"狀態：已完成 {done_line}。請立刻按「複製完整日誌」。"
    elif exit_code not in (None, 0):
        head = f"狀態：失敗 exit={exit_code}。請複製下方日誌。"
    elif log_name:
        head = "狀態：閒置。最近一次日誌在下方。"
    else:
        head = "狀態：閒置"
    parts = [head]
    if ready:
        parts.append(f"已打包 {len(ready)} 首，最後 {ready[-1]}")
    if stage and job:
        parts.append(f"最新步驟 {stage}")
    if log_name:
        parts.append(f"日誌 {log_name}")
    return "\n".join(parts)


def live_text():
    lines = [task_summary(), ""]
    gpus = gpu_rows()
    if not gpus:
        lines.append("GPU：沒有讀到 nvidia-smi")
    for gpu in gpus:
        lines.append(
            f"GPU {gpu['index']} {gpu['name']}  顯存 {gpu['memory_used']}/{gpu['memory_total']} MiB  利用率 {gpu['util']}%"
        )
    return "\n".join(lines)


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
        CURRENT["finished_id"] = job_id
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
  main { max-width:none; width:100%; margin:0; padding:0 20px 12px; }
  .topbar { position:sticky; top:0; z-index:40; background:var(--paper); margin:0 -20px 12px; padding:10px 20px; border-bottom:1px solid var(--line); }
  .topbar h1 { margin:0; display:flex; align-items:baseline; gap:14px; font-size:28px; }
  .topbar .sub { margin:0; font-size:14px; font-weight:400; }
  .layout { display:grid; grid-template-columns:minmax(0, 1fr) minmax(420px, 600px); gap:16px; align-items:start; width:100%; }
  .main-col, .side { min-width:0; }
  .side { position:sticky; top:var(--side-top, 64px); height:calc(100vh - var(--side-top, 64px) - 12px); max-height:calc(100vh - var(--side-top, 64px) - 12px); display:flex; flex-direction:column; gap:12px; overflow:hidden; padding-right:2px; }
  .pager, .copy-row { display:flex; align-items:center; gap:8px; margin-bottom:8px; flex-wrap:nowrap; }
  select.timepick { appearance:none; border:0; background:#efeae2; color:var(--ink); border-radius:999px; padding:8px 14px; font:600 14px/1 sans-serif; max-width:280px; }
  .step-split { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:12px; margin-top:10px; }
  .step-split > div { background:#f7f4ee; border-radius:12px; padding:12px; min-width:0; }
  .step-split .meter { margin:0 0 8px; font-weight:700; color:var(--ink); }
  .step-list { list-style:none; margin:0; padding:0; display:grid; gap:6px; }
  .step-list li { background:#fffdf9; border-radius:8px; padding:7px 10px; }
  .run-live { margin-top:8px; color:var(--muted); }
  #copy-note { margin:0; }
  @media (max-width: 900px) {
    .layout { grid-template-columns:1fr; }
    .side { position:static; height:auto; max-height:none; overflow:visible; }
  }
  h1 { font-size:32px; margin:0 0 4px; }
  h2 { font-size:18px; margin:0 0 12px; }
  h3 { font-size:16px; margin:0; }
  p, li { margin:0; }
  .sub { color:var(--muted); margin-bottom:20px; }
  .grid { display:grid; grid-template-columns:repeat(3, minmax(0, 1fr)); gap:16px; }
  .players { display:grid; grid-template-columns:repeat(3, minmax(0, 1fr)); gap:16px; }
  .player audio { width:100%; margin:10px 0; height:42px; }
  @media (max-width: 900px) {
    .grid { grid-template-columns:1fr; }
  }
  @media (max-width: 700px) {
    .players { grid-template-columns:1fr; }
  }
  details.block { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:4px 18px 14px; margin-bottom:16px; }
  details.block > summary { cursor:pointer; font-weight:700; font-size:18px; padding:14px 0 8px; }
  details.stage-fold { padding:10px 0; border-top:1px solid var(--line); }
  details.stage-fold > summary { cursor:pointer; display:flex; gap:12px; align-items:center; font-weight:700; }
  details.stage-fold .badge { min-width:72px; }
  ul { padding-left:18px; display:grid; gap:8px; }
  code { font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size:13px; display:block; overflow-x:auto; white-space:nowrap; }
  button { appearance:none; border:0; background:var(--accent); color:white; border-radius:999px; padding:10px 16px; font:600 15px/1 sans-serif; cursor:pointer; }
  button.ghost { background:#efeae2; color:var(--ink); }
  pre { white-space:pre-wrap; word-break:break-word; max-height:520px; overflow:auto; background:#1c1915; color:#f7f4ee; border-radius:12px; padding:14px; font:13px/1.45 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
  .reply.md { max-height:70vh; overflow:auto; background:#fffdf9; color:var(--ink); border:1px solid var(--line); border-radius:12px; padding:8px 16px 16px; }
  .reply.md strong { font-weight:700; }
  .reply.md h2 { font-size:20px; margin:16px 0 8px; }
  .reply.md h3 { font-size:17px; margin:12px 0 6px; }
  .reply.md p { margin:0 0 10px; }
  .reply.md ul { margin:0 0 12px; }
  .reply.md code { display:inline; white-space:normal; font-size:.92em; background:#f3efe8; padding:0 4px; border-radius:4px; }
  .reply.md pre { margin:0 0 12px; }
  .reply.md pre code { display:block; white-space:pre-wrap; background:transparent; color:inherit; padding:0; }
  .logpick { display:flex; flex-wrap:wrap; gap:8px; margin:8px 0 12px; }
  button:disabled { background:#b7b1a7; cursor:wait; }
  .job { display:flex; justify-content:space-between; gap:16px; align-items:center; padding:12px 0; border-top:1px solid var(--line); }
  .job p { color:var(--muted); margin-top:4px; }
  table { width:100%; border-collapse:collapse; }
  td { padding:8px 0; border-top:1px solid var(--line); vertical-align:top; }
  .ok { color:var(--accent); } .miss { color:#9a3412; }
  #note { min-height:0; margin:0; color:var(--muted); }
  #note:not(:empty) { margin-top:8px; }
  #task-board { margin-bottom:0; }
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
  .gpus { display:grid; grid-template-columns:repeat(4, minmax(0, 1fr)); gap:10px; }
  .gpu { background:#f7f4ee; border-radius:12px; padding:10px; display:grid; gap:6px; min-width:0; }
  .gpu strong { font-size:14px; }
  .gpu span, .gpu small { color:var(--muted); font-size:12px; line-height:1.35; }
  .gpu span { display:block; max-height:2.7em; overflow:hidden; }
  .bar { height:8px; background:#e4ddd2; border-radius:99px; overflow:hidden; }
  .bar > div { height:100%; background:#0f6e56; }
  .bar.mem > div { background:#1d4e89; }
  .side > details.block { flex:1 1 0; height:0; min-height:0; margin:0; display:flex; flex-direction:column; overflow:hidden; }
  .side > details.block > summary { flex:none; }
  .side > details.block::details-content { flex:1 1 auto; min-height:0; display:flex; flex-direction:column; overflow:hidden; }
  #task-board, .side .gpus { flex:1 1 auto; min-height:0; overflow:auto; }
  #task-board { display:flex; flex-direction:column; gap:12px; padding:2px 6px 8px 0; margin:0 0 8px; }
  .task-card { border:1px solid; border-radius:14px; padding:0; margin:0; display:block; }
  .task-card > summary { cursor:pointer; padding:12px 14px; }
  .task-card > p { margin:0; padding:0 14px 14px; color:var(--muted); }
  .task-card > button { margin:0 14px 14px; }
  .task-label { font:700 12px/1 sans-serif; letter-spacing:.04em; margin-right:6px; }
  .task-ready { background:#e7f6ef; border-color:#0f6e56; }
  .task-running { background:#e8f1fb; border-color:#1d4e89; }
  .task-done { background:#f3efe8; border-color:#cfc6ba; }
  .task-next { background:#fff6e0; border-color:#b7791f; }
  .task-later { background:#f7f4ee; border-color:#e4ddd2; }
  .task-group { display:grid; gap:10px; margin-top:12px; }
  .task-group h3 { margin:0; font-size:14px; }
  .sync-split { display:grid; grid-template-columns:minmax(0, 1fr) minmax(0, 1fr); gap:16px; align-items:stretch; }
  .sync-col, .tree-pane { display:flex; flex-direction:column; gap:8px; min-width:0; min-height:0; }
  .sync-col .meter, #tree-count { margin:0; }
  #tree-count { display:flex; align-items:center; gap:8px; min-width:0; overflow:hidden; }
  .sync-steps { list-style:none; margin:0; padding:0; display:grid; gap:4px; }
  .sync-step { display:flex; gap:8px; align-items:baseline; padding:4px 8px; border-radius:8px; background:#f7f4ee; }
  .sync-step .mark { font:700 12px/1 sans-serif; min-width:48px; }
  .sync-step.done { background:#e7f6ef; }
  .sync-step.current { background:#e8f1fb; }
  .sync-step.wait { color:var(--muted); }
  .tree-pane { position:relative; }
  .tree-label { flex:none; }
  .chip-row { min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .chip { display:inline-block; margin-right:6px; padding:2px 6px; border-radius:6px; font:700 11px/1.4 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
  .tree-scroll { position:absolute; left:0; right:0; top:28px; bottom:0; overflow:auto; border:1px solid var(--line); border-radius:12px; background:#fffdf9; }
  .tree, .tree ul { list-style:none; margin:0; padding:0; }
  .tree { margin:2px 0 2px 8px; padding-left:10px; border-left:1px solid #d4cbbf; position:relative; font:12px/1 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
  .tree ul { margin-left:6px; padding-left:10px; border-left:1px solid #d4cbbf; position:relative; }
  .tree li { position:relative; }
  .tree > li::before, .tree ul > li::before { content:""; position:absolute; left:-10px; top:7px; width:10px; border-top:1px solid #d4cbbf; }
  .tree::before, .tree ul::before { content:""; position:absolute; left:-1px; top:0; width:2px; height:7px; background:#fffdf9; }
  .tree > li:last-child::after, .tree ul > li:last-child::after { content:""; position:absolute; left:-11px; top:8px; bottom:0; width:3px; background:#fffdf9; }
  .tree summary { display:flex; align-items:center; gap:4px; min-height:16px; padding:0 6px 0 0; border-radius:4px; cursor:pointer; list-style:none; }
  .tree summary::-webkit-details-marker { display:none; }
  .tree .chev { width:5px; height:5px; border-right:1.5px solid #8a8175; border-bottom:1.5px solid #8a8175; transform:rotate(-45deg); flex:none; }
  .tree details[open] > summary .chev { transform:rotate(45deg); margin-top:-1px; }
  .tree .file { display:flex; align-items:center; gap:4px; min-height:16px; padding:0 6px 0 0; border-radius:4px; color:#6d675e; }
  .tree .name { min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .tree .meta { margin-left:auto; color:#8a8175; font:11px/1 sans-serif; }
  .tree .file.hit { background:#fff6e0; color:var(--ink); }
  .tree details.hit > summary { background:#f7f4ee; }
  .tree .tag { font:700 10px/1 sans-serif; border-radius:4px; padding:3px 4px; min-width:14px; text-align:center; }
  .tree .tag-A { background:#e5f4ef; color:#0f6e56; }
  .tree .tag-M { background:#fff1d6; color:#9a6700; }
  .tree .tag-D { background:#f8e8e2; color:#9a3412; }
  .tree .tag-R { background:#e8f1fb; color:#1d4e89; }
  .chip.tag-A { background:#e5f4ef; color:#0f6e56; }
  .chip.tag-M { background:#fff1d6; color:#9a6700; }
  .chip.tag-D { background:#f8e8e2; color:#9a3412; }
  .chip.tag-R { background:#e8f1fb; color:#1d4e89; }
  #git-notice[hidden] { display:none; }
  button[hidden] { display:none; }
  #git-notice { position:fixed; inset:0; z-index:80; display:flex; align-items:center; justify-content:center; padding:20px; background:rgba(28,25,21,.35); }
  .notice-card { width:min(420px, 100%); background:#fffdf9; border-radius:16px; padding:22px 24px; box-shadow:0 12px 40px rgba(28,25,21,.18); }
  .notice-card h2 { margin:0 0 8px; }
  .notice-card p { margin:0 0 16px; }
  @media (max-width: 900px) {
    .sync-split { grid-template-columns:1fr; }
    .tree-scroll { position:relative; top:auto; height:280px; }
  }
  .stage.current-row { background:#f3faf7; margin:0 -18px; padding:14px 18px; }
</style>
</head>
<body data-head="__HEADFULL__">
<main>
  <div class="topbar">
    <h1>YuE2 V100 <span class="sub" id="revision">__REVISION__</span></h1>
  </div>
  <div class="layout">
  <div class="main-col">
  <details class="block" open data-fold="sync">
    <summary>Git 同步</summary>
    <div class="sync-split">
      <div class="sync-col">
        <p class="meter" id="sync-head">__SYNCHEAD__</p>
        <ol class="sync-steps" id="sync-steps">__SYNCSTEPS__</ol>
      </div>
      <div class="tree-pane">
        <p class="meter" id="tree-count">__FILECOUNT__</p>
        <div class="tree-scroll" id="code-tree" data-mark="__FILEMARK__">__FILETREE__</div>
      </div>
    </div>
  </details>
  <details class="block" open data-fold="reply">
    <summary>本輪回答</summary>
    <div class="pager">
      <button id="reply-prev" class="ghost" type="button">上一則</button>
      <select id="reply-pick" class="timepick"></select>
      <button id="reply-next" class="ghost" type="button">下一則</button>
    </div>
    <div class="reply md" id="reply">__REPLY__</div>
  </details>
  __OPTIONAL__
  <div id="flows">__FLOWS__</div>
  <details class="block" open data-fold="logs">
    <summary>日誌</summary>
    <div class="pager">
      <button id="log-prev" class="ghost" type="button">上一則</button>
      <select id="log-pick" class="timepick"></select>
      <button id="log-next" class="ghost" type="button">下一則</button>
      <button id="copy" type="button">複製完整日誌</button>
      <span id="copy-note" class="meter"></span>
    </div>
    <pre id="logtext">還沒有日誌</pre>
  </details>
  </div>
  <aside class="side">
  <details class="block" open data-fold="task">
    <summary>任務</summary>
    <div id="task-board">__TASKS__</div>
    <button id="copy-task-log" type="button" __COPYLOG__>複製目前日誌</button>
    <p id="note"></p>
  </details>
  <details class="block" open data-fold="gpu">
    <summary>GPU</summary>
    <div class="gpus" id="gpus">__GPUS__</div>
  </details>
  </aside>
  </div>
</main>
<div id="done-notice" hidden>
  <div class="notice-card">
    <h2 id="done-title">任務已完成</h2>
    <p id="done-text"></p>
    <button id="copy-done" type="button">複製目前日誌</button>
    <button id="close-done" class="ghost" type="button">關閉</button>
  </div>
</div>
<div id="git-notice" hidden>
  <div class="notice-card">
    <h2>Git 已更新</h2>
    <p>伺服器上的代碼已經換到新版本。重整後才會看到新介面。</p>
    <button id="reload-page" type="button">重整畫面</button>
  </div>
</div>
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
  const root = document.getElementById("questions");
  if (!root) return;
  const mark = JSON.stringify(payload || {});
  if (mark === questionMark) return;
  questionMark = mark;
  const questions = (payload && payload.questions) || [];
  const intro = document.getElementById("question-intro");
  if (intro) intro.textContent = (payload && payload.intro) || "";
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
  return lines.join("\\n");
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
  if (answerNote) answerNote.textContent = "已複製，可以直接貼回來";
}
const copyAnswersButton = document.getElementById("copy-answers");
if (copyAnswersButton) copyAnswersButton.onclick = copyAnswers;
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
  const root = document.getElementById("players");
  if (!root) return;
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
let seenHead = document.body.getAttribute("data-head") || "";
let selectedLog = "";
let shownLog = "";
let taskSig = "";
let sawJob = false;
let logRows = [];
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
const copyTaskLog = document.getElementById("copy-task-log");
if (copyTaskLog) copyTaskLog.onclick = copyLog;
const replies = __REPLIES__;
let replyIndex = replies.length ? replies.length - 1 : 0;
function showReply() {
  const box = document.getElementById("reply");
  const pick = document.getElementById("reply-pick");
  if (!box || !replies.length) return;
  const item = replies[replyIndex];
  box.innerHTML = item.html || "";
  if (pick) pick.value = String(replyIndex);
}
function fillReplyPick() {
  const pick = document.getElementById("reply-pick");
  if (!pick) return;
  pick.innerHTML = replies.map((item, index) =>
    `<option value="${index}">${esc(item.time || ("第 " + (index + 1) + " 則"))}</option>`
  ).join("");
  pick.onchange = function () {
    replyIndex = Number(pick.value);
    showReply();
  };
}
const replyPrev = document.getElementById("reply-prev");
const replyNext = document.getElementById("reply-next");
if (replyPrev) replyPrev.onclick = function () { if (replyIndex > 0) { replyIndex -= 1; showReply(); } };
if (replyNext) replyNext.onclick = function () { if (replyIndex < replies.length - 1) { replyIndex += 1; showReply(); } };
fillReplyPick();
showReply();
document.getElementById("task-board").addEventListener("click", event => {
  const button = event.target.closest("button[data-job]");
  if (button && !button.disabled) runJob(button.dataset.job);
});
async function refresh() {
  let response;
  try {
    response = await fetch("/api/status");
  } catch (error) {
    document.getElementById("revision").textContent = "連不上控制台，請確認這個程序還在跑";
    return;
  }
  let data;
  try {
    data = await response.json();
  } catch (error) {
    document.getElementById("revision").textContent = "狀態不是有效資料，HTTP " + response.status;
    return;
  }
  if (data.error) {
    document.getElementById("revision").textContent = data.error;
    return;
  }
  if (data.head_full && seenHead && data.head_full !== seenHead) {
    seenHead = data.head_full;
    const gitNotice = document.getElementById("git-notice");
    if (gitNotice) gitNotice.hidden = false;
  } else if (data.head_full) {
    seenHead = data.head_full;
  }
  const key = JSON.stringify(data);
  if (key === last) return;
  last = key;
  applyStatus(data);
}
function applyStatus(data) {
  try {
  document.getElementById("revision").textContent = `${data.branch} @ ${data.head}，未提交 ${data.dirty_count} 個路徑`;
  pinSide();
  const busy = Boolean(data.running);
  if (data.running) sawJob = true;
  else if (sawJob) {
    sawJob = false;
    const doneBox = document.getElementById("done-notice");
    const doneTitle = document.getElementById("done-title");
    const doneText = document.getElementById("done-text");
    const ok = data.finished_exit === 0;
    if (doneTitle) doneTitle.textContent = ok ? "任務已完成" : "任務已結束";
    if (doneText) doneText.textContent = (data.finished_job || "") + (ok ? "" : "  exit=" + data.finished_exit);
    if (data.finished_log) selectedLog = data.finished_log;
    if (doneBox) doneBox.hidden = false;
  }
  if (note) note.textContent = "";
  const live = document.getElementById("run-live");
  if (live) live.textContent = data.run_detail || "";
  const board = document.getElementById("task-board");
  if (board && data.task_html && data.task_html !== taskSig) {
    taskSig = data.task_html;
    board.innerHTML = data.task_html;
    board.scrollTop = board.scrollHeight;
  }
  document.querySelectorAll("button[data-job]").forEach(button => { button.disabled = busy; });
  const gpus = document.getElementById("gpus");
  if (gpus && data.gpu_html) gpus.innerHTML = data.gpu_html;
  const syncHead = document.getElementById("sync-head");
  if (syncHead && data.sync_head) syncHead.textContent = data.sync_head;
  const syncSteps = document.getElementById("sync-steps");
  if (syncSteps && data.sync_steps) syncSteps.innerHTML = data.sync_steps;
  const copyTaskLogButton = document.getElementById("copy-task-log");
  if (copyTaskLogButton) copyTaskLogButton.hidden = !data.show_copy_log;
  const tree = document.getElementById("code-tree");
  if (tree && data.tree_html && tree.dataset.mark !== (data.tree_mark || "")) {
    tree.innerHTML = data.tree_html;
    tree.dataset.mark = data.tree_mark || "";
  }
  const treeCount = document.getElementById("tree-count");
  if (treeCount && data.tree_count) treeCount.innerHTML = data.tree_count;
  if (data.running && data.running.log) selectedLog = data.running.log;
  else if (!selectedLog && data.logs.length) selectedLog = data.logs[0].name;
  const logPick = document.getElementById("log-pick");
  if (logPick) {
    const sig = data.logs.map(row => row.name).join("|");
    if (sig !== logPick.dataset.sig) {
      logPick.dataset.sig = sig;
      logPick.innerHTML = data.logs.map(row =>
        `<option value="${esc(row.name)}">${esc(row.mtime)}</option>`
      ).join("");
    }
    if (selectedLog) logPick.value = selectedLog;
    logPick.onchange = function () {
      selectedLog = logPick.value;
      shownLog = "";
      const row = data.logs.find(item => item.name === selectedLog);
      showLog(selectedLog, row ? row.bytes : 0);
    };
  }
  logRows = data.logs;
  const logPrev = document.getElementById("log-prev");
  const logNext = document.getElementById("log-next");
  if (logPrev) logPrev.onclick = function () {
    const index = logRows.findIndex(row => row.name === selectedLog);
    if (index > 0) {
      selectedLog = logRows[index - 1].name;
      shownLog = "";
      if (logPick) logPick.value = selectedLog;
      showLog(selectedLog, logRows[index - 1].bytes);
    }
  };
  if (logNext) logNext.onclick = function () {
    const index = logRows.findIndex(row => row.name === selectedLog);
    if (index >= 0 && index < logRows.length - 1) {
      selectedLog = logRows[index + 1].name;
      shownLog = "";
      if (logPick) logPick.value = selectedLog;
      showLog(selectedLog, logRows[index + 1].bytes);
    }
  };
  const chosen = data.logs.find(row => row.name === selectedLog);
  showLog(selectedLog, chosen ? chosen.bytes : 0);
  } catch (error) {
    document.getElementById("revision").textContent = "頁面填資料失敗：" + error;
  }
}
async function runJob(id) {
  const live = document.getElementById("run-live");
  if (live) live.textContent = "啟動中";
  const response = await fetch("/api/run/" + encodeURIComponent(id), { method: "POST" });
  const data = await response.json();
  if (live) live.textContent = response.ok ? "已開始" : (data.error || "無法啟動");
  refresh();
}
function pinSide() {
  const bar = document.querySelector(".topbar");
  if (!bar) return;
  const gap = Math.ceil(bar.offsetHeight + parseFloat(getComputedStyle(bar).marginBottom));
  document.documentElement.style.setProperty("--side-top", gap + "px");
}
const reloadPage = document.getElementById("reload-page");
if (reloadPage) reloadPage.onclick = function () { location.reload(); };
const copyDone = document.getElementById("copy-done");
if (copyDone) copyDone.onclick = async function () {
  const row = logRows.find(item => item.name === selectedLog);
  if (row) {
    shownLog = "";
    await showLog(selectedLog, row.bytes);
  }
  copyLog();
};
const closeDone = document.getElementById("close-done");
if (closeDone) closeDone.onclick = function () {
  const box = document.getElementById("done-notice");
  if (box) box.hidden = true;
};
pinSide();
window.addEventListener("resize", pinSide);
const taskBoard = document.getElementById("task-board");
if (taskBoard) taskBoard.scrollTop = taskBoard.scrollHeight;
refresh();
setInterval(refresh, 2000);
</script>
</body>
</html>
"""


def reply_text():
    path = ROOT / "agent_instructions.md"
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return "尚無回答。"


def optional_blocks(data):
    narrative_data = data.get("narrative") or {}
    blocks = []
    if narrative_data.get("show_listen"):
        blocks.append(
            '<details class="block" open data-fold="listen"><summary>對聽</summary>'
            '<p class="meter">三份都在伺服器上：原曲、基模無譜生成、新權重無譜生成。</p>'
            f'<div class="players" id="players">{render_players(data.get("artifacts") or [])}</div>'
            "</details>"
        )
    if narrative_data.get("show_questions"):
        questions = data.get("questions") or {}
        blocks.append(
            '<details class="block" open data-fold="questions"><summary>選擇題</summary>'
            f'<p class="meter" id="question-intro">{html.escape(questions.get("intro") or "")}</p>'
            f'<div id="questions">{render_questions(questions)}</div>'
            '<button id="copy-answers" type="button">複製答案</button>'
            '<p id="answer-note" class="meter"></p></details>'
        )
    return "".join(blocks)


SYNC_STEPS = (
    ("ssh", "(1/5) Testing SSH connectivity"),
    ("pull", "(2/5) Pulling latest from origin"),
    ("dirty", "(3/5) Checking uncommitted local changes"),
    ("repo", "(4/5) Ensuring server repo exists"),
    ("remote", "(5/5) Setting git remote"),
    ("push", "Pushing to server"),
    ("verify", "Verifying server side"),
    ("done", "Done"),
)
TREE_CACHE = {"head": None, "html": "", "count": ""}


def sync_record():
    path = Path("/cache/yue2_panel/sync_status.json")
    if not path.is_file():
        return {}
    try:
        info = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return info if isinstance(info, dict) else {}


def sync_parts():
    info = sync_record()
    state = str(info.get("state") or "unknown")
    step = str(info.get("step") or "")
    sha = str(info.get("sha") or "")
    when = str(info.get("time") or "")
    labels = {"syncing": "正在同步", "synced": "已同步", "unknown": "尚無同步記錄"}
    head = f"{labels.get(state, state)}    {when or '無'}    {sha}".strip()
    order = [key for key, _title in SYNC_STEPS]
    if state == "synced" or step == "done":
        cursor = len(order)
    elif step in order:
        cursor = order.index(step)
    else:
        cursor = -1
    rows = []
    for index, (_key, title) in enumerate(SYNC_STEPS):
        if index < cursor:
            mark, klass = "完成", "done"
        elif index == cursor:
            mark, klass = "進行中", "current"
        else:
            mark, klass = "等待", "wait"
        rows.append(
            f'<li class="sync-step {klass}"><span class="mark">{mark}</span>'
            f"<span>{html.escape(title)}</span></li>"
        )
    return head, "".join(rows)


def change_map():
    info = sync_record()
    state = str(info.get("state") or "unknown")
    raw = info.get("files") if isinstance(info.get("files"), list) else None
    lines = [str(item) for item in raw if str(item).strip()] if raw else []
    if not lines and state != "syncing":
        shown = git_text(["show", "--name-status", "--pretty=format:", "-1"])
        lines = [line for line in shown.splitlines() if line.strip()]
    marks = {}
    for line in lines:
        parts = [part.strip() for part in line.split("\t") if part.strip()]
        if len(parts) < 2:
            continue
        letter = parts[0][0]
        if letter == "R" and len(parts) >= 3:
            marks[parts[2]] = "R"
            marks.setdefault(parts[1], "D")
        elif letter in {"A", "M", "D", "R", "C"}:
            marks[parts[-1]] = letter
        else:
            marks[parts[-1]] = "M"
    return marks


def render_file_tree(listing, marks):
    files = [line.strip() for line in listing.splitlines() if line.strip()]
    root = {}

    def ensure(path, letter):
        node = root
        parts = path.split("/")
        for part in parts[:-1]:
            child = node.get(part)
            if not isinstance(child, dict):
                child = {}
                node[part] = child
            node = child
        node[parts[-1]] = letter

    seen = set(files)
    for path in files:
        ensure(path, marks.get(path, ""))
    for path, letter in marks.items():
        if path not in seen:
            ensure(path, letter)
    if not root:
        return "<p class='meter'>沒有讀到代碼樹</p>", "沒有讀到代碼樹"

    def tally(node):
        counts = {}
        for value in node.values():
            if isinstance(value, dict):
                for key, count in tally(value).items():
                    counts[key] = counts.get(key, 0) + count
            elif value:
                counts[value] = counts.get(value, 0) + 1
        return counts

    def file_count(node):
        total = 0
        for value in node.values():
            total += file_count(value) if isinstance(value, dict) else 1
        return total

    def tags(counts):
        return "".join(
            f'<span class="tag tag-{html.escape(letter)}">{html.escape(letter)} {counts[letter]}</span>'
            for letter in ("A", "M", "D", "R", "C")
            if counts.get(letter)
        )

    def walk(node, root=False):
        def sort_key(name):
            value = node[name]
            changed = bool(tally(value)) if isinstance(value, dict) else bool(value)
            return (not isinstance(value, dict), not changed, name.lower())

        chunks = []
        for name in sorted(node, key=sort_key):
            value = node[name]
            safe = html.escape(name)
            if isinstance(value, dict):
                counts = tally(value)
                hit = " hit" if counts else ""
                opened = " open" if counts else ""
                chunks.append(
                    "<li><details class=\"dir{hit}\"{opened}>"
                    "<summary><i class=\"chev\"></i><span class=\"name\">{name}/</span>{tags}"
                    "<span class=\"meta\">{count}</span></summary>{children}</details></li>".format(
                        hit=hit,
                        opened=opened,
                        name=safe,
                        tags=tags(counts),
                        count=file_count(value),
                        children=walk(value),
                    )
                )
            else:
                hit = " hit" if value else ""
                tag = f'<span class="tag tag-{html.escape(value)}">{html.escape(value)}</span>' if value else ""
                chunks.append(
                    f'<li><div class="file{hit}">{tag}<span class="name">{safe}</span></div></li>'
                )
        klass = ' class="tree"' if root else ""
        return f"<ul{klass}>{''.join(chunks)}</ul>"

    changed = sum(tally(root).values())
    chips = "".join(
        f'<span class="chip tag-{html.escape(letter)}">{html.escape(f"{letter} {Path(path).name}")}</span>'
        for path, letter in sorted(marks.items())
    )
    caption = (
        f'<span class="tree-label">代碼樹 {file_count(root)} 個文件，本次變更：</span>'
        f'<span class="chip-row">{chips}</span>'
    )
    return walk(root, True), caption


def code_tree():
    marks = change_map()
    head = git_text(["rev-parse", "HEAD"]) or ""
    signature = head + "|" + ",".join(f"{path}:{marks[path]}" for path in sorted(marks))
    if TREE_CACHE["head"] == signature and TREE_CACHE["html"]:
        return TREE_CACHE["html"], signature, TREE_CACHE["count"]
    html_tree, count = render_file_tree(git_text(["ls-files"]), marks)
    TREE_CACHE["head"] = signature
    TREE_CACHE["html"] = html_tree
    TREE_CACHE["count"] = count
    return html_tree, signature, count


def render_markdown(text):
    def inline(value):
        escaped = html.escape(value)
        parts = []
        position = 0
        for match in re.finditer(r"`([^`]+)`|\*\*(.+?)\*\*", escaped):
            parts.append(escaped[position:match.start()])
            if match.group(1) is not None:
                parts.append(f"<code>{match.group(1)}</code>")
            else:
                parts.append(f"<strong>{match.group(2)}</strong>")
            position = match.end()
        parts.append(escaped[position:])
        return "".join(parts)

    lines = text.splitlines()
    blocks = []
    paragraph = []
    index = 0

    def flush_paragraph():
        if paragraph:
            blocks.append("<p>" + inline(" ".join(paragraph)) + "</p>")
            paragraph.clear()

    while index < len(lines):
        line = lines[index]
        if line.startswith("```"):
            flush_paragraph()
            index += 1
            code_lines = []
            while index < len(lines) and not lines[index].startswith("```"):
                code_lines.append(lines[index])
                index += 1
            if index < len(lines):
                index += 1
            blocks.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
            continue
        if line.startswith("### "):
            flush_paragraph()
            blocks.append("<h3>" + inline(line[4:]) + "</h3>")
        elif line.startswith("## "):
            flush_paragraph()
            blocks.append("<h2>" + inline(line[3:]) + "</h2>")
        elif line.startswith("# "):
            flush_paragraph()
            blocks.append("<h1>" + inline(line[2:]) + "</h1>")
        elif line.startswith("- "):
            flush_paragraph()
            items = []
            while index < len(lines) and lines[index].startswith("- "):
                items.append("<li>" + inline(lines[index][2:]) + "</li>")
                index += 1
            blocks.append("<ul>" + "".join(items) + "</ul>")
            continue
        elif line.strip():
            paragraph.append(line.strip())
        else:
            flush_paragraph()
        index += 1
    flush_paragraph()
    return "".join(blocks)


def reply_history():
    path = ROOT / "public" / "panel_replies.jsonl"
    items = []
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if item.get("text"):
                text = item["text"]
                items.append({
                    "time": item.get("time") or "",
                    "text": text,
                    "html": render_markdown(text),
                })
    if not items:
        text = reply_text()
        items.append({"time": "", "text": text, "html": render_markdown(text)})
    return items


def page_html():
    data = status_payload()
    if data.get("error"):
        revision = data["error"]
    else:
        revision = f'{data["branch"]} @ {data["head"]}，未提交 {data["dirty_count"]} 個路徑'
    pieces = {
        "__REVISION__": html.escape(revision),
        "__PLAYERS__": render_players(data.get("artifacts") or []),
        "__QUESTION_INTRO__": html.escape((data.get("questions") or {}).get("intro") or ""),
        "__QUESTIONS__": render_questions(data.get("questions") or {}),
        "__FLOWS__": render_flows(
            data.get("flow") or {},
            (data.get("narrative") or {}).get("progress") or [],
        ),
        "__HEADFULL__": html.escape(data.get("head_full") or ""),
        "__JOBS__": render_jobs(pipeline_view()[1]),
        "__JOBS_ATTR__": "open" if pipeline_view()[1] else "hidden",
        "__REPLY__": render_markdown(reply_text()),
        "__REPLIES__": json.dumps(reply_history(), ensure_ascii=False).replace("<", "\\u003c"),
        "__SYNCHEAD__": html.escape(data.get("sync_head") or ""),
        "__SYNCSTEPS__": data.get("sync_steps") or "",
        "__FILETREE__": data.get("tree_html") or "",
        "__FILEMARK__": html.escape(data.get("tree_mark") or ""),
        "__FILECOUNT__": html.escape(data.get("tree_count") or ""),
        "__COPYLOG__": "" if data.get("show_copy_log") else "hidden",
        "__TASKS__": pipeline_view()[0],
        "__GPUS__": render_gpus(gpu_rows()),
        "__OPTIONAL__": optional_blocks(data),
    }
    page = PAGE
    for key, value in pieces.items():
        page = page.replace(key, value)
    return page


def render_items(items):
    return "".join(f"<li>{html.escape(str(item))}</li>" for item in items)


def loss8_is_done():
    summary = Path("/cache/yue2_outputs/suno_loss8/summary.txt")
    try:
        if summary.is_file() and summary.read_text(encoding="utf-8").count("abc_loss=") >= 8:
            return True
    except OSError:
        return False
    logs = log_rows()
    if not logs:
        return False
    return "abc_loss8_done=8" in (read_log(logs[0]["name"]) or "")


def batch7_is_done():
    packed = Path("/cache/yue2_outputs/suno_packed")
    if all((packed / f"{index:03d}" / "prefix.npy").is_file() for index in range(1, 8)):
        return True
    logs = log_rows()
    if not logs:
        return False
    return "batch7_done=7" in (read_log(logs[0]["name"]) or "")


def batch7_progress():
    logs = log_rows()
    if not logs:
        return ""
    lines = (read_log(logs[0]["name"]) or "").splitlines()
    ready = [line for line in lines if line.startswith("ready=")]
    stage = next((line for line in reversed(lines) if line.startswith("stage ")), "")
    parts = []
    if ready:
        parts.append(f"已打包 {len(ready)} / 7，最後 {ready[-1]}")
    if stage:
        parts.append(stage)
    return "；".join(parts)


def task_card(state, label, title, detail, button=None):
    action = ""
    if button:
        action = f'<button data-job="{html.escape(button["id"])}" type="button">執行</button>'
    open_attr = "" if state == "done" else " open"
    return (
        f'<details class="task-card task-{state}"{open_attr}>'
        f'<summary><span class="task-label">{html.escape(label)}</span> {html.escape(title)}</summary>'
        f'<p>{html.escape(detail)}</p>{action}</details>'
    )


def task_group(state, label, cards):
    return (
        f'<div class="task-group task-{state}"><h3>{html.escape(label)}</h3>{"".join(cards)}</div>'
    )


PIPELINE = ["transcribe7", "abc_loss8", "free004"]


def task_done(task_id):
    if task_id == "transcribe7":
        return batch7_is_done()
    if task_id == "abc_loss8":
        return loss8_is_done()
    if task_id == "free004":
        return Path("/cache/yue2_outputs/suno_free/suno_004_free/audio.mp3").is_file()
    return False


def job_record(task_id):
    job = dict(JOBS[task_id])
    job["id"] = task_id
    return job


def done_detail(task_id):
    if task_id == "transcribe7":
        return "batch7_done=7，001 到 007 已打包。"
    if task_id == "abc_loss8":
        return "8 首平均 abc_loss=0.4971。000 最低 0.3594，004 最高 0.6875。沒有更新權重。"
    if task_id == "free004":
        return "已生成 217.1 秒，耗時 501.5 秒。樂譜和語義都沒有截斷。"
    return JOBS[task_id]["detail"]


def running_detail(task_id):
    if task_id == "transcribe7":
        return batch7_progress()
    logs = log_rows()
    if not logs:
        return ""
    lines = [line for line in (read_log(logs[0]["name"]) or "").splitlines() if " abc_loss=" in line]
    return lines[-1] if lines else ""


def pipeline_view():
    with LOCK:
        running = CURRENT["job"]
    cards = []
    visible = []
    started = False
    for number, task_id in enumerate(PIPELINE, 1):
        task = JOBS[task_id]
        title = f"{number}. {task['title']}"
        if running == task_id:
            detail = running_detail(task_id) or task["detail"]
            cards.append(task_card("running", "正在進行", title, detail))
            started = True
        elif task_done(task_id):
            cards.append(task_card("done", "已完成", title, done_detail(task_id)))
        elif not visible and not running:
            record = job_record(task_id)
            state = "next" if number > 1 else "ready"
            label = "可以開始下一步" if number > 1 else "可以開始"
            cards.append(task_card(state, label, title, task["detail"], record))
            visible.append(record)
            started = True
        else:
            cards.append(task_card("later", "之後", title, task["detail"]))
    listen_title = f"{len(PIPELINE) + 1}. 對聽第 004 首"
    if listen_recorded():
        cards.append(task_card(
            "done", "已完成", listen_title,
            "整體很像。旋律只有部分段落接近。段落對得上。伴奏接近原曲。人聲自然。",
        ))
        probe_title = f"{len(PIPELINE) + 2}. 32GB 顯存探針"
        probe_detail = JOBS["fit32_probe"]["detail"]
        if running == "fit32_probe":
            cards.append(task_card("running", "正在進行", probe_title, probe_detail))
        elif probe_is_done():
            cards.append(task_card("done", "已完成", probe_title, "峰值 9.54 GiB，abc_loss=0.3594。沒有更新權重。"))
            update_title = f"{len(PIPELINE) + 3}. 32GB 小更新"
            update_detail = JOBS["fit32_update"]["detail"]
            if running == "fit32_update":
                cards.append(task_card("running", "正在進行", update_title, update_detail))
            elif update_is_done():
                cards.append(task_card("done", "已完成", update_title, "8 首各一步已完成。峰值 9.85 GiB。新權重在 fit32-suno8。"))
                listen_new = f"{len(PIPELINE) + 4}. 用新權重生成 004"
                listen_detail = JOBS["free004_fit32"]["detail"]
                if running == "free004_fit32":
                    cards.append(task_card("running", "正在進行", listen_new, listen_detail))
                elif Path("/cache/yue2_outputs/suno_free/suno_004_fit32/audio.mp3").is_file():
                    cards.append(task_card("done", "已完成", listen_new, "已生成 224.0 秒，耗時 517.2 秒。樂譜和語義都沒有截斷。"))
                    cards.append(task_card(
                        "next", "請對聽", f"{len(PIPELINE) + 5}. 三份對聽",
                        "播放原曲、基模生成和新權重生成。選完選擇題後按複製答案。",
                    ))
                else:
                    record = job_record("free004_fit32")
                    cards.append(task_card("next", "下一步", listen_new, listen_detail, record))
                    visible.append(record)
            else:
                record = job_record("fit32_update")
                cards.append(task_card("next", "下一步", update_title, update_detail, record))
                visible.append(record)
        else:
            record = job_record("fit32_probe")
            cards.append(task_card("next", "下一步", probe_title, probe_detail, record))
            visible.append(record)
    elif listen_is_current():
        cards.append(task_card("next", "請對聽", listen_title, "播放原曲和這次生成。選完選擇題後按複製答案。"))
    else:
        cards.append(task_card("later", "之後", listen_title, "播放原曲和這次生成。選完選擇題後按複製答案。"))
    return "".join(cards), visible


def update_is_done():
    for row in log_rows():
        text = read_log(row["name"]) or ""
        if "saved=/cache/yue2_ckpts/fit32-suno8" in text and "base_unchanged=" in text:
            return True
    return False


def probe_is_done():
    for row in log_rows():
        text = read_log(row["name"]) or ""
        if "peak_gib=" in text and "no weights were updated" in text:
            return True
    return False


def listen_recorded():
    return bool(narrative().get("listen_done"))


def listen_is_current():
    with LOCK:
        if CURRENT["job"] is not None:
            return False
    return all(task_done(task_id) for task_id in PIPELINE) and not listen_recorded()


def copy_log_visible():
    with LOCK:
        running = CURRENT["job"]
        exit_code = CURRENT["exit"]
    return running is not None or exit_code is not None


def render_gpus(rows):
    if not rows:
        return "<p>沒有讀到 nvidia-smi</p>"
    cards = []
    for gpu in rows:
        try:
            util = max(0, min(100, int(float(gpu["util"]))))
            mem_pct = max(0, min(100, int(100 * float(gpu["memory_used"]) / max(float(gpu["memory_total"]), 1))))
            mem_text = f'{float(gpu["memory_used"]) / 1024:.1f}/{float(gpu["memory_total"]) / 1024:.0f} GB'
        except (TypeError, ValueError):
            util, mem_pct = 0, 0
            mem_text = f'{gpu["memory_used"]}/{gpu["memory_total"]} MiB'
        cards.append(
            f'<div class="gpu"><strong>GPU {html.escape(gpu["index"])}</strong>'
            f'<span>{html.escape(gpu["name"])}</span>'
            f'<div class="bar"><div style="width:{util}%"></div></div><small>利用率 {util}%</small>'
            f'<div class="bar mem"><div style="width:{mem_pct}%"></div></div>'
            f'<small>顯存 {html.escape(mem_text)}</small></div>'
        )
    return "".join(cards)


def render_code(artifacts):
    parts = []
    for row in artifacts:
        state = f'{row["bytes"]} bytes' if row.get("exists") else "不存在"
        klass = "ok" if row.get("exists") else "miss"
        parts.append(
            f'<p><strong>{html.escape(row["label"])}</strong> '
            f'<span class="{klass}">{html.escape(state)}</span><br>'
            f'<code>{html.escape(row["path"])}</code></p>'
        )
    return "".join(parts)


def render_players(artifacts):
    parts = []
    for row in artifacts:
        audio = ""
        if row.get("exists"):
            audio = f'<audio controls preload="none" src="/audio/{html.escape(row["id"])}"></audio>'
        state = f'{row["bytes"]} bytes' if row.get("exists") else "不存在"
        klass = "ok" if row.get("exists") else "miss"
        parts.append(
            f'<div class="player"><h3>{html.escape(row["label"])} '
            f'<span class="{klass}">{html.escape(state)}</span></h3>{audio}'
            f'<code>{html.escape(row["path"])}</code></div>'
        )
    return "".join(parts)


def render_questions(payload):
    blocks = []
    for index, question in enumerate(payload.get("questions") or [], 1):
        options = "".join(
            '<label><input type="radio" name="{name}" value="{label}">{label}</label>'.format(
                name=html.escape(question["id"]),
                label=html.escape(option["label"]),
            )
            for option in question.get("options") or []
        )
        blocks.append(
            f'<div class="q" data-question="{html.escape(question["id"])}" '
            f'data-prompt="{html.escape(question["prompt"])}">'
            f'<strong>{index}. {html.escape(question["prompt"])}</strong>'
            f'<div class="choice">{options}</div></div>'
        )
    return "".join(blocks)


def render_flows(payload, progress=None):
    labels = {"done": "已完成", "current": "目前", "later": "之後", "blocked": "受阻"}
    sections = []
    for flow in payload.get("flows") or []:
        stages = flow.get("stages") or []
        meter = ""
        if flow.get("total"):
            meter = f'已完成 {flow["done"]} / {flow["total"]}。目前：{flow.get("current_title") or "未標明"}。'
        open_flow = " open" if any(stage.get("status") == "current" for stage in stages) else ""
        stage_html = []
        for index, stage in enumerate(stages, 1):
            status = stage.get("status") or ""
            open_stage = " open" if status == "current" else ""
            extra = ""
            if status == "current":
                extra = (
                    '<div class="step-split"><div><p class="meter">目前進度</p>'
                    + '<ul class="step-list">' + render_items(progress or []) + "</ul>"
                    + '<p id="run-live" class="run-live"></p></div><div><p class="meter">下一步</p>'
                    + '<ul class="step-list">' + render_items(stage.get("next") or []) + "</ul>"
                    + "</div></div>"
                )
            stage_html.append(
                f'<details class="stage-fold"{open_stage}><summary>'
                f'<span class="badge {html.escape(status)}">{html.escape(labels.get(status, status))}</span>'
                f'{index}. {html.escape(stage.get("title") or "")}</summary>'
                f'<p>{html.escape(stage.get("detail") or "")}</p>{extra}</details>'
            )
        sections.append(
            f'<details class="block"{open_flow}><summary>{html.escape(flow.get("title") or "")}</summary>'
            f'<p class="meter">{html.escape(meter)}</p>{"".join(stage_html)}</details>'
        )
    return "".join(sections)


def render_jobs(jobs):
    return "".join(
        f'<div class="job"><div><strong>{html.escape(job["title"])}</strong>'
        f'<p>{html.escape(job["detail"])}</p></div>'
        f'<button data-job="{html.escape(job["id"])}" type="button">執行</button></div>'
        for job in jobs
    )


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
            body = page_html().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
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
