"""Drive the n8n_workflow_system Host Bridge job layer from Hermes.

The bridge already wraps Outlook/Excel COM, the Jira and GitLab clients, and the
workflow logic behind an HTTP contract (docs/BRIDGE_API.md). Hermes orchestrates
and summarises; it does not reimplement any of that.

    python bridge_job.py list
    python bridge_job.py run chipset_readiness --params '{"dryRun":true}'
    python bridge_job.py run jira_weekly_report --params '{"dryRun":true}' --notify

Credentials come from the environment (BRIDGE_URL, BRIDGE_TOKEN), which Hermes
loads from ~/.hermes/.env. Nothing is read from the repo at runtime.
"""
import argparse
import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = os.environ.get("BRIDGE_URL", "http://127.0.0.1:8765/api/v1").rstrip("/")
TOKEN = os.environ.get("BRIDGE_TOKEN", "")
HERMES = r"C:\Users\Chi_L\AppData\Local\hermes\bin\hermes.exe"

# Extensions Telegram renders inline; everything else goes as a plain document.
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


def _call(path, payload=None, timeout=60):
    url = f"{BASE}{path}"
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"X-Bridge-Token": TOKEN}
    if data:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers,
                                 method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read(500).decode(errors="replace")
        raise SystemExit(f"bridge {path} -> HTTP {e.code}: {detail}")
    except urllib.error.URLError as e:
        raise SystemExit(
            f"bridge unreachable at {BASE} ({e.reason}). The Host Bridge runs on the "
            f"Windows host, not in a container -- start it with host-bridge\run-bridge.cmd."
        )
    if not body.get("ok", True):
        raise SystemExit(f"bridge {path} -> {json.dumps(body.get('error'))}")
    return body.get("data", body)


def cmd_list(_args):
    data = _call("/jobs")
    jobs = data.get("jobs", data)
    if isinstance(jobs, dict):
        jobs = [{"name": k, **v} for k, v in jobs.items()]
    for j in jobs:
        name = j.get("name") or j.get("job")
        schema = j.get("paramsSchema") or {}
        props = schema.get("properties") or {}
        required = set(schema.get("required") or [])
        print(f"{name}")
        for k, v in props.items():
            tag = "required" if k in required else "optional"
            desc = (v.get("description") or "").split("\n")[0][:70]
            print(f"    {k:<22} {tag:<8} {desc}")


def _fetch_files(run_id, files, out_dir):
    """Pull each declared artifact back through the bridge.

    A job declaring a file does not mean the bridge will hand it over: the path
    must sit inside an allowed root, and anything over 20 MB is refused with the
    path so a human can go get it. Both are reported, not raised -- a missing
    chart should not lose the report it belongs to.
    """
    saved = []
    out_dir.mkdir(parents=True, exist_ok=True)
    for f in files:
        name = f.get("name")
        if not name:
            continue
        try:
            d = _call(f"/jobs/run/{run_id}/files/{urllib.parse.quote(name)}", timeout=120)
        except SystemExit as e:
            print(f"  [file] {name}: not retrievable -- {e}", file=sys.stderr)
            continue
        blob = base64.b64decode(d.get("contentBase64", ""))
        dest = out_dir / name
        dest.write_bytes(blob)
        saved.append(dest)
        print(f"  [file] {name} -> {dest} ({len(blob)} bytes)")
    return saved


def _notify(job, verdict, summary_lines, saved):
    """Tell Leo on Telegram. Images ride along as MEDIA: lines."""
    ok = verdict.get("ok")
    mark = {True: "✅", False: "❌", None: "ℹ️"}.get(ok, "ℹ️")
    body = [f"{mark} {job}"]
    if verdict.get("summary"):
        body.append(verdict["summary"])
    body.extend(summary_lines)
    for p in saved:
        # MEDIA: is how `hermes send` attaches a file; images render inline.
        body.append(f"MEDIA:{p}")
    text = "\n".join(body)
    try:
        subprocess.run([HERMES, "send", "-t", "telegram", "-q", text],
                       check=True, timeout=120)
        print("  [notify] sent to telegram")
    except Exception as e:  # noqa: BLE001 - a failed notice must not fail the run
        print(f"  [notify] FAILED: {e}", file=sys.stderr)


def cmd_run(args):
    params = json.loads(args.params) if args.params else {}
    data = _call("/jobs/run", {"job": args.job, "params": params,
                               "async": True, "timeoutSec": args.timeout})
    run_id = data.get("runId")
    print(f"runId={run_id} job={args.job}")

    deadline = time.time() + args.timeout
    state = {}
    while time.time() < deadline:
        state = _call(f"/jobs/run/{run_id}")
        if state.get("status") != "running":
            break
        time.sleep(5)
    else:
        raise SystemExit(f"job still running after {args.timeout}s; poll {run_id} yourself")

    status = state.get("status")
    result = state.get("result") or {}
    verdict = result.get("verdict") or {}
    print(f"status={status}")
    if state.get("error"):
        print("error:", json.dumps(state["error"], ensure_ascii=False)[:500])

    # Everything that is not a reserved key is the job's own payload.
    payload = {k: v for k, v in result.items() if k not in ("verdict", "files", "tables")}
    lines = []
    if payload:
        print("result:", json.dumps(payload, ensure_ascii=False)[:2000])
        lines.append(json.dumps(payload, ensure_ascii=False)[:600])

    saved = []
    if result.get("files"):
        saved = _fetch_files(run_id, result["files"], Path(args.out))

    if args.notify:
        _notify(args.job, verdict, lines, saved)

    for l in (state.get("log") or [])[-15:]:
        print("  log:", str(l)[:200])
    sys.exit(0 if status == "success" else 1)


def main():
    if not TOKEN:
        raise SystemExit("BRIDGE_TOKEN is not set in the environment (~/.hermes/.env)")
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list").set_defaults(func=cmd_list)
    r = sub.add_parser("run")
    r.add_argument("job")
    r.add_argument("--params", default="")
    r.add_argument("--timeout", type=int, default=900)
    r.add_argument("--out", default=str(Path.home() / ".hermes" / "bridge-artifacts"))
    r.add_argument("--notify", action="store_true",
                   help="Send the outcome (and any artifacts) to Telegram.")
    r.set_defaults(func=cmd_run)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
