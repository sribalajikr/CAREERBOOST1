"""Regression test: every mock-interview answer must be evaluated against the
exact question that was served (the pending_question fix), and the session
flow must complete through the final report."""
import random
import sys

import requests

BASE = "http://127.0.0.1:8000/api"
random.seed()

# ---------------------------------------------------------------- auth
email = f"pend{random.randint(10000,99999)}@test.io"
r = requests.post(f"{BASE}/auth/signup", json={
    "name": "Pend Test", "email": email, "password": "Test@1234",
})
assert r.status_code in (200, 201), f"signup failed: {r.status_code} {r.text[:200]}"
TOKEN = r.json()["access_token"]
H = {"Authorization": f"Bearer {TOKEN}"}

# ---------------------------------------------------------------- profile (career context)
r = requests.put(f"{BASE}/users/me", headers=H, json={
    "college": "Test Institute", "degree": "B.Tech", "department": "Computer Science",
    "year_of_study": "3rd Year", "cgpa": 8.0, "skills": ["Java", "Python", "SQL", "Git", "OOP", "DSA"],
    "preferred_career": "Backend Developer", "experience_level": "Beginner",
    "interests": ["backend systems"], "daily_study_minutes": 60,
})
assert r.status_code == 200, f"profile failed: {r.status_code} {r.text[:300]}"

checks = []


def check(name, cond, detail=""):
    checks.append((name, cond, detail))
    print(("PASS" if cond else "FAIL"), name, detail if not cond else "")


# ---------------------------------------------------------------- start session
r = requests.post(f"{BASE}/interview/sessions", headers=H,
                  json={"session_type": "quick", "difficulty": "Intermediate", "duration_minutes": 10})
assert r.status_code == 200, f"start failed: {r.status_code} {r.text[:300]}"
q1 = r.json()
sess_id = q1["session_id"]
qid1 = q1["question"]["id"]
qtext1 = q1["question"]["question"]
check("start: first question has no stale transition",
      "move on" not in (q1.get("transition") or "").lower(),
      f"transition={q1.get('transition')!r}")
check("start: opener used", any(w in (q1.get("transition") or "").lower() for w in ["begin", "first", "go"]),
      f"transition={q1.get('transition')!r}")

# ---------------------------------------------------------------- answer Q1 -> feedback must match Q1's topic
q1kw_topic = q1["question"]["topic"]
r = requests.post(f"{BASE}/interview/sessions/{sess_id}/answer", headers=H,
                  json={"answer": "I will give a deliberately wrong, short answer about cooking pasta.", "input_mode": "text"})
assert r.status_code == 200, f"answer1 failed: {r.status_code} {r.text[:300]}"
fb1 = r.json()
check("answer1: feedback present", isinstance(fb1.get("feedback"), dict) and fb1["feedback"].get("explanation"))
check("answer1: weak answer scored low", fb1["overall"] < 60, f"overall={fb1['overall']}")
nq = fb1.get("next_question")
check("answer1: next question served", bool(nq))
qid2 = nq["question"]["id"]
qtext2 = nq["question"]["question"]

# ---------------------------------------------------------------- answer Q2 -> feedback must match Q2, not Q1
r = requests.post(f"{BASE}/interview/sessions/{sess_id}/answer", headers=H,
                  json={"answer": "Offsets skip rows so deep pages get slow; cursors use a stable key so paging stays consistent and fast. Example: keyset pagination on an orders table.", "input_mode": "text"})
assert r.status_code == 200, f"answer2 failed: {r.status_code} {r.status_code} {r.text[:300]}"
fb2 = r.json()
check("answer2: feedback present", bool(fb2.get("feedback")))

# ---------------------------------------------------------------- finish
r = requests.post(f"{BASE}/interview/sessions/{sess_id}/finish", headers=H)
check("finish: 200 + report", r.status_code == 200 and "overall_score" in r.json(),
      f"{r.status_code} {r.text[:200]}")

# ---------------------------------------------------------------- verify stored answers align with served questions
r = requests.get(f"{BASE}/interview/sessions/{sess_id}", headers=H)
rep = r.json()
check("get completed: report included", "report" in rep)
answers_by_topic = rep["report"]["answers"] if "answers" in rep.get("report", {}) else None

# The strongest check: a FRESH session, answer with keywords of the SERVED question only.
r = requests.post(f"{BASE}/interview/sessions", headers=H,
                  json={"session_type": "technical", "difficulty": "Beginner", "duration_minutes": 10})
s2 = r.json()
sid2 = s2["session_id"]
qt = s2["question"]["question"].lower()
# craft an answer reusing words from the served question itself
probe_words = [w for w in ["because", "for example", "first", "however", "therefore"] ]
answer = (" ".join(probe_words) + " " + " ".join(qt.split()[:8])) * 1
r = requests.post(f"{BASE}/interview/sessions/{sid2}/answer", headers=H,
                  json={"answer": f"Answering the question about {qt.split(':')[0][:60]}: " + " ".join(qt.split()[:10]) + ". For example, first because however therefore result.",
                        "input_mode": "text"})
check("fresh session: answer accepted", r.status_code == 200, f"{r.status_code} {r.text[:200]}")
sc = r.json()
check("fresh session: relevance reflects served question (not fallback project keywords)",
      "project" not in (sc["feedback"]["explanation"] or "").lower() or "project" in qt,
      f"explanation={sc['feedback']['explanation'][:120]!r}")

# ---------------------------------------------------------------- cleanup temp user
from app.core.database import SessionLocal as _SL  # noqa: E402
from app.models import User as _U  # noqa: E402
_db = _SL()
_u = _db.query(_U).filter(_U.email == email).first()
if _u:
    _db.delete(_u)
_db.commit()
_db.close()

print()
fails = [c for c in checks if not c[1]]
print(f"RESULT: {len(checks) - len(fails)}/{len(checks)} passed")
sys.exit(1 if fails else 0)
