"""Headless behavior check for the game-style Planner/Roadmap API.

Drives the REAL running backend and asserts the stateful lifecycle:
  reset -> toggle a task -> re-read (persistence) -> untoggle -> re-read.
Uses the demo account and leaves its Progress at 0 so nothing is dirtied.

Run: backend/venv/Scripts/python backend/verify_roadmap_behavior.py
"""
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8000"
TOKEN = None
PASSED = []


def call(method, path, body=None, auth=True):
    global TOKEN
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(f"{BASE}{path}", data=data, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    if auth and TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    try:
        with urllib.request.urlopen(req) as r:
            payload = r.read()
            return r.status, (json.loads(payload) if payload else None)
    except urllib.error.HTTPError as e:
        payload = e.read()
        try:
            return e.code, json.loads(payload)
        except Exception:
            return e.code, payload.decode(errors="replace")


def check(name, cond, detail=""):
    PASSED.append(bool(cond))
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f"  -> {detail}" if detail and not cond else ""))


CAREER = urllib.parse.quote("Software Developer", safe="")

# --- login as demo ---
code, data = call("POST", "/api/auth/login", {"email": "demo@career.ai", "password": "demo1234"}, auth=False)
check("demo login", code == 200 and data.get("access_token"), (code, data))
TOKEN = data["access_token"]

# --- clean slate ---
call("DELETE", f"/api/roadmap/{CAREER}")

# --- shape of the level track ---
code, lv = call("GET", f"/api/roadmap/{CAREER}/levels")
check("levels endpoint 200", code == 200, (code, lv))
levels = lv["levels"]
check("11 levels", len(levels) == 11, len(levels))
check("44 total tasks", lv["total_tasks"] == 44, lv["total_tasks"])
check("fresh: 0 tasks done", lv["completed_tasks"] == 0, lv["completed_tasks"])
check("fresh: L01 current", levels[0]["state"] == "current", levels[0]["state"])
check("fresh: L02 next (unlocked)", levels[1]["state"] == "unlocked", levels[1]["state"])
check("fresh: L03 locked", levels[2]["state"] == "locked", levels[2]["state"])
check("fresh: overall 0%", lv["overall_progress"] == 0, lv["overall_progress"])

# --- toggle one task in L01 ---
task0 = levels[0]["tasks"][0]["id"]
code, _ = call("POST", f"/api/roadmap/{CAREER}/tasks/{task0}")
check("toggle task returns 200", code == 200, code)

# --- re-read: did it persist and move the meter? ---
_, after = call("GET", f"/api/roadmap/{CAREER}/levels")
check("re-read: 1 task done", after["completed_tasks"] == 1, after["completed_tasks"])
check("re-read: task marked done", after["levels"][0]["tasks"][0]["done"] is True, after["levels"][0]["tasks"][0])
check("re-read: L01 progress 25%", after["levels"][0]["progress"] == 25, after["levels"][0]["progress"])
check("re-read: overall 2% (1/44)", after["overall_progress"] == 2, after["overall_progress"])
check("re-read: L01 still current", after["levels"][0]["state"] == "current", after["levels"][0]["state"])

# --- untoggle: does it revert? ---
call("POST", f"/api/roadmap/{CAREER}/tasks/{task0}")
_, back = call("GET", f"/api/roadmap/{CAREER}/levels")
check("untoggle: back to 0 tasks", back["completed_tasks"] == 0, back["completed_tasks"])
check("untoggle: L01 progress 0%", back["levels"][0]["progress"] == 0, back["levels"][0]["progress"])

# --- invalid task id rejected ---
code, _ = call("POST", f"/api/roadmap/{CAREER}/tasks/bogus-999")
check("unknown task rejected 404", code == 404, code)

# --- finish L01 fully -> must unlock L02 ---
for t in back["levels"][0]["tasks"]:
    call("POST", f"/api/roadmap/{CAREER}/tasks/{t['id']}")
_, done = call("GET", f"/api/roadmap/{CAREER}/levels")
check("L01 completed after all 4", done["levels"][0]["state"] == "completed", done["levels"][0]["state"])
check("L02 now current", done["levels"][1]["state"] == "current", done["levels"][1]["state"])
check("L03 now unlocked", done["levels"][2]["state"] == "unlocked", done["levels"][2]["state"])
check("completed_levels == 1", done["completed_levels"] == 1, done["completed_levels"])

# --- reset restores clean state AND persists ---
call("DELETE", f"/api/roadmap/{CAREER}")
_, clean = call("GET", f"/api/roadmap/{CAREER}/levels")
check("reset: 0 tasks", clean["completed_tasks"] == 0, clean["completed_tasks"])
check("reset: L01 current again", clean["levels"][0]["state"] == "current", clean["levels"][0]["state"])
check("reset: L03 locked again", clean["levels"][2]["state"] == "locked", clean["levels"][2]["state"])

print("\n" + "=" * 50)
print(f"RESULT: {sum(PASSED)}/{len(PASSED)} passed")
sys.exit(0 if all(PASSED) else 1)
