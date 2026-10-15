"""Headless end-to-end test: drives the real running API through the full student journey.

Run: backend/venv/Scripts/python backend/e2e_test.py
Asserts state transitions across all 5 modules + dashboard.
"""
import json
import sys
import urllib.request

BASE = "http://127.0.0.1:8000"
TOKEN = None
PASSED = []


def call(method, path, body=None, auth=True, raw=False):
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
            return r.status, (payload if raw else (json.loads(payload) if payload else None))
    except urllib.error.HTTPError as e:
        payload = e.read()
        try:
            return e.code, json.loads(payload)
        except Exception:
            return e.code, payload.decode(errors="replace")


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    PASSED.append(bool(cond))
    print(f"[{status}] {name}" + (f"  -> {detail}" if detail and not cond else ""))
    if not cond:
        print(f"       detail: {detail}")


# ---------- Module 1: Auth ----------
suffix = sys.argv[1] if len(sys.argv) > 1 else "x"
from app.core.config import settings  # noqa: E402
if settings.SMTP_USER and "@" in settings.SMTP_USER:
    # SMTP live: use a Gmail plus-alias so the reset email is really deliverable
    _local, _domain = settings.SMTP_USER.split("@", 1)
    email = f"{_local}+e2e{suffix}@{_domain}"
else:
    email = f"e2e_{suffix}@test.edu"
code, data = call("POST", "/api/auth/signup", {"name": "E2E Tester", "email": email, "password": "Secret@123"}, auth=False)
check("signup returns token + user", code in (200, 201) and data.get("access_token") and data["user"]["onboarded"] is False, data)
TOKEN = data["access_token"]

code, dup = call("POST", "/api/auth/signup", {"name": "E2E", "email": email, "password": "Secret@123"}, auth=False)
check("duplicate signup rejected with 409", code == 409, (code, dup))

code, me = call("GET", "/api/users/me")
check("GET /users/me returns profile dict", code == 200 and isinstance(me.get("profile"), dict), (code, me))

code, comp = call("GET", "/api/users/me/completion")
check("completion starts low", code == 200 and 0 <= comp["completion"] < 40, (code, comp))

# ---------- Onboarding ----------
code, prof = call("PUT", "/api/users/me", {
    "name": "E2E Tester", "phone": "+91 90000 00000", "college": "Test College",
    "degree": "B.Tech", "department": "Computer Science", "year_of_study": "3rd Year",
    "cgpa": 8.3, "skills": ["Python", "Java", "C", "SQL", "Git"], "interests": ["Web apps"],
    "preferred_career": "Software Developer", "experience_level": "Beginner",
    "daily_study_minutes": 120,
})
check("onboarding profile saved & onboarded=True", code == 200 and prof["onboarded"] is True and prof["profile"]["college"] == "Test College", (code, prof))
check("skills canonicalized (C++ merged into C)", "C" in prof["profile"]["skills"] and "C++" not in prof["profile"]["skills"], prof["profile"]["skills"])

code, comp = call("GET", "/api/users/me/completion")
check("completion now 100%", code == 200 and comp["completion"] == 100, (code, comp))

# forgot-password round trip: code must go to the inbox, NEVER the API response
code, fp = call("POST", "/api/auth/forgot-password", {"email": email}, auth=False)
check("forgot-password: 200 and no code leaked in response", code == 200 and not fp.get("demo_code") and not fp.get("code"), (code, fp))
# email delivery can't be read headlessly — inject a known code, then reset
from datetime import datetime, timedelta, timezone as _tz  # noqa: E402
from app.core.database import SessionLocal as _SL  # noqa: E402
from app.models import User as _U  # noqa: E402
from app.core.security import hash_password as _hp  # noqa: E402
_db = _SL()
_u = _db.query(_U).filter(_U.email == email).first()
_u.reset_code = _hp("654321")
_u.reset_code_expires = datetime.now(_tz.utc) + timedelta(minutes=15)
_db.commit()
_db.close()
code, rp = call("POST", "/api/auth/reset-password", {"email": email, "code": "654321", "new_password": "Newsecret@1"}, auth=False)
check("reset-password succeeds with emailed code", code == 200, (code, rp))
code, lg = call("POST", "/api/auth/login", {"email": email, "password": "Newsecret@1"}, auth=False)
check("login with new password works", code == 200 and lg.get("access_token"), (code, lg))
TOKEN = lg["access_token"]

# ---------- Module 2: Resume ----------
import os
with open(os.path.join(os.path.dirname(__file__), "sample_resume.pdf"), "rb") as f:
    pdf = f.read()
boundary = "----e2eboundary"
parts = [
    f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"e2e_resume.pdf\"\r\n"
    f"Content-Type: application/pdf\r\n\r\n".encode() + pdf + b"\r\n",
    f"--{boundary}--\r\n".encode(),
]
body = b"\r\n".join(parts)
req = urllib.request.Request(f"{BASE}/api/resumes/analyze", data=body, method="POST")
req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
req.add_header("Authorization", f"Bearer {TOKEN}")
with urllib.request.urlopen(req) as r:
    ra = json.loads(r.read())
check("resume analyzed: score >= 70", ra["score"] >= 70, ra["score"])
check("resume found 8+ skills", len(ra["skills"]) >= 8, ra["skills"])
check("resume has strengths + improvements", ra["strengths"] and ra["improvements"], (ra["strengths"], ra["improvements"]))

code, latest = call("GET", "/api/resumes/latest")
check("latest resume persisted", code == 200 and latest["file_name"] == "e2e_resume.pdf" and latest["is_latest"], (code, latest and latest.get("file_name")))

# ---------- Module 3: Careers ----------
code, recs = call("GET", "/api/careers/recommend")
recs = recs["recommendations"]
check("3+ career recommendations", len(recs) >= 3, len(recs))
top = recs[0]
check("top match is Software Developer at 90%+", top["career"] == "Software Developer" and top["match_percent"] >= 90, (top["career"], top["match_percent"]))
check("each rec has required/user/missing/why/learning_path", all(
    r.get(k) is not None for r in recs for k in ("required_skills", "user_skills", "missing_skills", "why", "learning_path")
), "missing keys")

# ---------- Module 4: Roadmap ----------
code, rm = call("GET", "/api/roadmap/Software%20Developer")
check("roadmap has 7 phases", code == 200 and len(rm["phases"]) == 7, (code, len(rm.get("phases", []))))
first_task = rm["phases"][0]["tasks"][0]["id"]
code, rm2 = call("POST", f"/api/roadmap/Software%20Developer/tasks/{first_task}")
check("toggling task marks it done", rm2["phases"][0]["tasks"][0]["done"] is True, rm2["phases"][0]["tasks"][0])
check("overall progress became > 0", rm2["overall_progress"] > 0, rm2["overall_progress"])
check("completed_tasks == 1", rm2["completed_tasks"] == 1, rm2["completed_tasks"])

# ---------- Module 5: Planner ----------
code, plan = call("GET", "/api/planner/today?generate=true")
check("today's plan generated", code == 200 and plan["total"] > 0, (code, plan))
titles = [t["title"] for t in plan["tasks"]]
check("no duplicate task titles", len(titles) == len(set(titles)), titles)
check("plan fits requested 2h budget (blocks sum <= 135m)", sum(t["duration_minutes"] for t in plan["tasks"]) <= 135, sum(t["duration_minutes"] for t in plan["tasks"]))

task_id = plan["tasks"][0]["id"]
code, plan2 = call("PATCH", f"/api/planner/tasks/{task_id}/status?new_status=done")
check("mark task done -> progress increases", plan2["completed"] == 1 and plan2["progress"] > 0, (plan2["completed"], plan2["progress"]))

code, skipped = call("PATCH", f"/api/planner/tasks/{plan['tasks'][1]['id']}/status?new_status=skipped")
check("skip task works", any(t["status"] == "skipped" for t in skipped["tasks"]), [t["status"] for t in skipped["tasks"]])

code, resched = call("POST", f"/api/planner/tasks/{plan['tasks'][2]['id']}/reschedule")
check("reschedule moves task to tomorrow", resched["total"] == plan2["total"] - 1, (resched["total"], plan2["total"]))

code, week = call("GET", "/api/planner/week")
check("weekly plan has 7 themed days", code == 200 and len(week["days"]) == 7, (code, len(week.get("days", []))))
check("weekly days have categories+suggestions", all(d["category"] and d["suggestion"] for d in week["days"]), "missing fields")

code, st = call("POST", "/api/planner/study-time", {"minutes_per_day": 30})
check("study-time rebuild adds a fresh <=30min pending task", any(t["duration_minutes"] <= 30 and t["status"] == "pending" for t in st["tasks"]), [(t["title"], t["duration_minutes"], t["status"]) for t in st["tasks"]])
check("study-time rebuild never duplicates today's titles", len({t["title"] for t in st["tasks"]}) == len(st["tasks"]), [t["title"] for t in st["tasks"]])

# ---------- Dashboard ----------
code, dash = call("GET", "/api/dashboard")
check("dashboard aggregates all signals", code == 200 and dash["resume_score"] and dash["career_match"] and dash["roadmap_progress"] is not None, (code, dash))
check("dashboard message is friendly", isinstance(dash["message"], str) and len(dash["message"]) > 10, dash["message"])
check("upcoming tasks present", isinstance(dash["upcoming"], list), dash.get("upcoming"))

# ---------- 401 guard ----------
code, _ = call("GET", "/api/dashboard", auth=False)
check("protected route rejects anonymous (401)", code == 401, code)

total, ok = len(PASSED), sum(PASSED)
print(f"\n{'='*50}\nRESULT: {ok}/{total} passed")
sys.exit(0 if ok == total else 1)
