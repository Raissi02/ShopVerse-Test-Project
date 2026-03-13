"""
runner_server.py
─────────────────────────────────────────────────────────────────────────────
ShopVerse Test Runner — Flask backend server

Exposes a simple HTTP API that the GUI calls to:
  • Run any pytest suite (unit / api / e2e / individual file)
  • Stream live output line-by-line via Server-Sent Events (SSE)
  • Check backend + frontend availability
  • Cancel a running test run

Install the one extra dependency:
    pip install flask

Run from the root of your test project (same folder as pytest.ini):
    python runner_server.py

Then open:
    http://localhost:9000
─────────────────────────────────────────────────────────────────────────────
"""

import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

import requests as req_lib
from flask import Flask, Response, jsonify, request, send_from_directory

# ── Config ────────────────────────────────────────────────────────────────────

PORT          = 9000
PROJECT_ROOT  = Path(__file__).parent          # folder containing pytest.ini
BACKEND_URL   = "http://localhost:5000/api/categories"
FRONTEND_URL  = "http://localhost:4200"
PYTHON_EXE    = sys.executable                 # same Python that runs this server

app = Flask(__name__, static_folder=str(PROJECT_ROOT))

# ── Global run state ──────────────────────────────────────────────────────────

_current_proc: subprocess.Popen | None = None
_run_lock = threading.Lock()

# ── Known test suites ─────────────────────────────────────────────────────────

SUITES = {
    # id         : (args passed to pytest after "pytest")
    "unit"       : ["tests_unit/", "-v", "--tb=short", "--no-header"],
    "api"        : ["tests_api/test_api_auth.py",
                    "tests_api/test_api_categories.py",
                    "tests_api/test_api_orders.py",
                    "tests_api/test_api_products.py",
                    "tests_api/test_api_users.py",
                    "-v", "--tb=short", "--no-header"],
    "system"     : ["tests_api/test_system_flows.py", "-v", "--tb=short", "--no-header"],
    "backend"    : ["tests_unit/", "tests_api/", "-v", "--tb=short", "--no-header"],
    "login"      : ["tests_e2e/test_login.py",        "-v", "--tb=short", "--no-header"],
    "register"   : ["tests_e2e/test_register.py",     "-v", "--tb=short", "--no-header"],
    "home"       : ["tests_e2e/test_home.py",         "-v", "--tb=short", "--no-header"],
    "nav"        : ["tests_e2e/test_navigation.py",   "-v", "--tb=short", "--no-header"],
    "cart"       : ["tests_e2e/test_cart.py",         "-v", "--tb=short", "--no-header"],
    "compat"     : ["tests_e2e/test_compatibility.py","-v", "--tb=short", "--no-header"],
    "a11y"       : ["tests_e2e/test_accessibility.py","-v", "--tb=short", "--no-header"],
    "e2e"        : ["tests_e2e/", "-v", "--tb=short", "--no-header"],
    "all"        : ["tests_unit/", "tests_api/", "tests_e2e/",
                    "-v", "--tb=short", "--no-header"],
}

# ── SSE helpers ───────────────────────────────────────────────────────────────

def _sse(event: str, data: dict) -> str:
    """Format a single SSE frame."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _classify_line(line: str) -> str:
    """Return a log level for a pytest output line."""
    s = line.strip()
    if re.match(r"PASSED", s):                  return "pass"
    if re.match(r"FAILED|ERROR", s):            return "fail"
    if re.match(r"WARNING|WARN", s):            return "warn"
    if re.match(r"=+\s*(PASSED|passed)", s):    return "pass"
    if re.match(r"=+\s*(FAILED|failed|error)",s,re.I): return "fail"
    if re.match(r"=+", s):                      return "sep"
    if re.match(r"RUNNING|collecting", s, re.I): return "info"
    if re.match(r"tests_unit|tests_api|tests_e2e|test_", s): return "info"
    return "dim"


def _parse_result_line(line: str) -> dict | None:
    """
    Parse a verbose pytest result line and return a structured dict.

    Handles both Unix and Windows output formats:

      Unix (standard):
        tests_unit/test_unit_auth_logic.py::TestClass::test_fn PASSED [  5%]

      Windows (pytest appends the absolute path with a ← arrow):
        tests_unit\\test_unit_auth_logic.py::TestClass::test_fn ← C:\\Users\\...\\test_fn.py PASSED [ 5%]
        tests_e2e/test_cart.py::TestCartPage::test_fn <- C:\\Users\\...\\test_cart.py PASSED [ 57%]

    The Windows arrow annotation (← U+2190 or <- ASCII) is stripped before
    the main regex runs so every format is handled uniformly.
    """
    s = line.strip()

    # ── Strip Windows path annotation ─────────────────────────────────────────
    # Pattern: optional space + (← or <-) + space + anything + lookahead for status word
    # Uses non-greedy .+? so it stops at the earliest status keyword.
    s = re.sub(
        r'\s+(?:\u2190|<-)\s+.+?(?=\s+(?:PASSED|FAILED|ERROR|SKIPPED)\b)',
        '',
        s,
    )

    # ── Match the cleaned line ─────────────────────────────────────────────────
    m = re.match(
        r"(?P<path>[\w/\\\.]+)::(?P<cls>[\w]+)::(?P<fn>test_[\w]+)"
        r"\s+(?P<status>PASSED|FAILED|ERROR|SKIPPED)"
        r"(?:\s+\[\s*(?P<pct>\d+)%\])?",
        s,
    )
    if not m:
        return None

    return {
        "path"  : m.group("path"),
        "cls"   : m.group("cls"),
        "fn"    : m.group("fn"),
        "status": m.group("status"),
        "pct"   : int(m.group("pct") or 0),
    }


def _parse_summary(line: str) -> dict | None:
    """
    Parse a pytest summary line like:
      5 failed, 55 passed, 1 warning in 3.42s
    or:
      60 passed in 0.31s
    """
    m = re.search(
        r"(?:(?P<failed>\d+) failed[,\s]*)?"
        r"(?:(?P<passed>\d+) passed[,\s]*)?"
        r"(?:(?P<error>\d+) error[s]?[,\s]*)?"
        r"(?:(?P<skipped>\d+) skipped[,\s]*)?"
        r"in\s+(?P<duration>[\d.]+)s",
        line
    )
    if not m:
        return None
    return {
        "passed"  : int(m.group("passed")   or 0),
        "failed"  : int(m.group("failed")   or 0),
        "errors"  : int(m.group("error")    or 0),
        "skipped" : int(m.group("skipped")  or 0),
        "duration": float(m.group("duration") or 0),
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@app.after_request
def _cors(resp):
    resp.headers["Access-Control-Allow-Origin"]  = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return resp


@app.route("/")
def index():
    """Serve the GUI HTML file."""
    return send_from_directory(str(PROJECT_ROOT), "runner_gui.html")


@app.route("/status")
def status():
    """Return server + service availability."""
    backend_ok  = False
    frontend_ok = False
    try:
        r = req_lib.get(BACKEND_URL, timeout=2)
        backend_ok = r.status_code < 500
    except Exception:
        pass
    try:
        r = req_lib.get(FRONTEND_URL, timeout=2)
        frontend_ok = r.status_code < 500
    except Exception:
        pass
    return jsonify({
        "server"  : True,
        "backend" : backend_ok,
        "frontend": frontend_ok,
        "running" : _current_proc is not None and _current_proc.poll() is None,
    })


@app.route("/run/<suite_id>")
def run_suite(suite_id: str):
    """
    Stream pytest output for the given suite as SSE.

    Query params:
      file  — override with a specific file path (relative to project root)
      extra — extra pytest flags e.g. -k "test_name"
    """
    global _current_proc

    if suite_id not in SUITES and suite_id != "file":
        return jsonify({"error": f"Unknown suite '{suite_id}'"}), 400

    # Build command
    if suite_id == "file":
        target = request.args.get("file", "")
        if not target:
            return jsonify({"error": "Missing 'file' param"}), 400
        args = [target, "-v", "--tb=short", "--no-header"]
    else:
        args = SUITES[suite_id]

    extra = request.args.get("extra", "")
    if extra:
        args = args + extra.split()

    cmd = [PYTHON_EXE, "-m", "pytest"] + args

    def generate():
        global _current_proc
        with _run_lock:
            if _current_proc and _current_proc.poll() is None:
                yield _sse("error", {"message": "A test run is already in progress."})
                return

            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            env["PYTHONPATH"]       = str(PROJECT_ROOT)

            try:
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(PROJECT_ROOT),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    env=env,
                )
                _current_proc = proc
            except FileNotFoundError as e:
                yield _sse("error", {"message": str(e)})
                return

        # Emit start event
        yield _sse("start", {
            "cmd"  : " ".join(cmd),
            "suite": suite_id,
            "time" : time.time(),
        })

        summary = None

        for raw_line in proc.stdout:
            line = raw_line.rstrip("\n")

            # Always emit the raw log line
            yield _sse("log", {
                "text" : line,
                "level": _classify_line(line),
            })

            # Emit structured result if we can parse it
            result = _parse_result_line(line)
            if result:
                yield _sse("result", result)

            # Detect summary line
            s = _parse_summary(line)
            if s:
                summary = s

        proc.wait()
        exit_code = proc.returncode

        yield _sse("done", {
            "exit_code": exit_code,
            "summary"  : summary or {},
            "time"     : time.time(),
        })

        with _run_lock:
            _current_proc = None

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control" : "no-cache",
            "X-Accel-Buffering": "no",   # disable nginx buffering
        }
    )


@app.route("/cancel", methods=["POST"])
def cancel():
    """Kill the currently running pytest process."""
    global _current_proc
    with _run_lock:
        if _current_proc and _current_proc.poll() is None:
            _current_proc.terminate()
            _current_proc = None
            return jsonify({"cancelled": True})
    return jsonify({"cancelled": False, "reason": "No run in progress"})


@app.route("/suites")
def list_suites():
    """Return all known suite IDs and their pytest args."""
    return jsonify({
        k: {"args": v, "cmd": "pytest " + " ".join(v)}
        for k, v in SUITES.items()
    })


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  ShopVerse Test Runner")
    print(f"  http://localhost:{PORT}")
    print(f"  Project root: {PROJECT_ROOT}")
    print(f"  Python: {PYTHON_EXE}")
    print("=" * 60)
    print()
    print("  Make sure you have started:")
    print("    dotnet run  (port 5000)  — for API + E2E tests")
    print("    ng serve    (port 4200)  — for E2E Selenium tests")
    print()
    app.run(host="0.0.0.0", port=PORT, threaded=True, debug=False)
