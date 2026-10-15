"""Scenario tests for the 11-point module update (item 11).

Drives the real running API as two separate users and verifies:
  1-4  analytics / graphs / practice summary / placement percentages match activity
  5    plan has N tasks; completing 2 -> 2/N with the right percentage
  6    refresh persistence (server-stored completion)
  7    logout/login persistence
  8    user isolation (B sees none of A)
  9  QA role -> QA-specific prep questions + QA-specific placement plan
 10  Java role -> Java-specific placement plan + Java-specific prep questions

Run: backend/venv/Scripts/python backend/scenario_test_11.py <suffix>
"""
import json
import re
import sys
import urllib.request

BASE = "http://127.0.0.1:8000"
TOKEN = None
PASSED = []


def call(method, path, body=None, auth=True, raw_body=None, content_type=None):
    global TOKEN
    data = raw_body if raw_body is not None else (None if body is None else json.dumps(body).encode())
    req = urllib.request.Request(f"{BASE}{path}", data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", content_type or "application/json")
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
    status = "PASS" if cond else "FAIL"
    PASSED.append(bool(cond))
    print(f"[{status}] {name}" + ("" if cond else f"  -> {detail}"))
    if not cond:
        print(f"       detail: {detail}")


suffix = sys.argv[1] if len(sys.argv) > 1 else "s1"
from app.core.config import settings  # noqa: E402

if settings.SMTP_USER and "@" in settings.SMTP_USER:
    _local, _domain = settings.SMTP_USER.split("@", 1)
    email_a = f"{_local}+e2eScenA{suffix}@{_domain}"
    email_b = f"{_local}+e2eScenB{suffix}@{_domain}"
else:
    email_a = f"e2e_scen_a{suffix}@test.edu"
    email_b = f"e2e_scen_b{suffix}@test.edu"

# auth.py lowercases every email on signup; build them lowercase so the
# end-of-run cleanup matches what is actually stored in MySQL.
email_a = email_a.lower()
email_b = email_b.lower()

ANSWER = ("In my approach I first clarify the requirements and constraints, then work through a small example "
          "before choosing a solution. In my project I used an approach with a hash map so lookup stays O(1), "
          "and I tested the edge cases such as empty input and duplicates. I would measure performance, "
          "communicate the trade-offs with the team, and document the decision so it is easy to maintain later.")

# ------------------------------------------------------------------ setup User A
code, data = call("POST", "/api/auth/signup",
                  {"name": "Scenario A", "email": email_a, "password": "Secret@123"}, auth=False)
check("A signup", code in (200, 201) and data.get("access_token"), (code, data))
TOKEN = data["access_token"]

code, prof = call("PUT", "/api/users/me", {
    "name": "Scenario A", "phone": "+91 90000 00001", "college": "Scenario College",
    "degree": "B.Tech", "department": "Computer Science", "year_of_study": "4th Year",
    "cgpa": 8.1, "skills": ["Selenium", "SQL", "Testing"],
    "preferred_career": "QA / Automation Engineer", "experience_level": "Beginner",
    "daily_study_minutes": 90,
})
check("A onboarded with QA role", code == 200 and prof.get("onboarded") is True
      and prof["profile"]["preferred_career"] == "QA / Automation Engineer", (code, prof))

# resume upload (exercises resumeAnalysis module)
import os  # noqa: E402
with open(os.path.join(os.path.dirname(__file__), "sample_resume.pdf"), "rb") as f:
    pdf = f.read()
boundary = "----scenboundary"
body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"scen_resume.pdf\"\r\n"
        "Content-Type: application/pdf\r\n\r\n").encode() + pdf + f"\r\n--{boundary}--\r\n".encode()
code, res = call("POST", "/api/resumes/analyze", raw_body=body,
                 content_type=f"multipart/form-data; boundary={boundary}")
check("A resume analyzed", code in (200, 201) and res.get("score", 0) > 0, (code, str(res)[:200]))
resume_score = res.get("score", 0)

# ------------------------------------------------------------------ TEST 9 (part 1): QA role -> QA prep questions
qa_categories_seen = []
qa_ids = []
for _ in range(6):
    code, q = call("GET", "/api/interview/prep/next")
    check("prep/next serves a question", code == 200 and q.get("question"), (code, q))
    qa_ids.append(q.get("id", ""))
    qa_categories_seen.append(q.get("category", ""))
    code, a = call("POST", f"/api/interview/prep/answer?question_id={q['id']}", {"answer": ANSWER})
    check("prep answer accepted", code == 200 and "overall" in a, (code, a))

qa_domain = sum(1 for i in qa_ids if i.startswith("qa"))
check("QA role: >=4/6 prep questions are QA/testing questions", qa_domain >= 4,
      f"ids={qa_ids} categories={qa_categories_seen}")
check("QA role: zero generic developer-pool questions (no sw*/fe* ids)",
      not any(i.startswith(("sw", "fe")) for i in qa_ids), f"ids={qa_ids}")

# ------------------------------------------------------------------ item 2: fresh paragraph every request
paras = []
for _ in range(3):
    code, p = call("GET", "/api/speech/paragraph")
    check("paragraph endpoint 200", code == 200 and p.get("text"), (code, p))
    paras.append(p)
    wc = len(re.findall(r"[a-zA-Z']+", p["text"]))
    check("paragraph is 80-150 words", 80 <= p["word_count"] <= 150 and wc == p["word_count"],
          f"wc={p['word_count']} recomputed={wc}")
    check("paragraph is professional (no story content)",
          "once upon" not in p["text"].lower() and p["text"].count("?") == 0, p["text"][:80])
    code, an = call("POST", "/api/speech/analyze", {
        "question_text": p["text"], "question_id": p["id"], "transcript": ANSWER,
        "duration_seconds": 45, "input_mode": "text",
    })
    check("speech analysis 200 with score", code == 200 and an.get("communication_score", 0) > 0, (code, an))

check("3 requests -> 3 distinct paragraphs", len({p["text"] for p in paras}) == 3,
      [p["text"][:40] for p in paras])

# refresh also yields a fresh paragraph (server remembers the last ones)
code, p_again = call("GET", "/api/speech/paragraph")
check("4th paragraph still fresh", p_again["text"] not in {p["text"] for p in paras}, p_again["text"][:40])

# ------------------------------------------------------------------ mock interview: QA questions, no repeats, finish
code, q1 = call("POST", "/api/interview/sessions",
                {"session_type": "technical", "difficulty": "Intermediate", "duration_minutes": 5})
check("mock session starts", code == 200 and q1.get("session_id"), (code, q1))
check("5-minute session plans 3 questions", q1.get("planned_total") == 3, q1)
session_id = q1["session_id"]
served_ids = [q1["question"]["id"]]
mock_categories = [q1["question"]["category"]]
next_q = q1
answers_sent = 0
while next_q is not None and answers_sent < 10:
    code, res = call("POST", f"/api/interview/sessions/{session_id}/answer",
                     {"answer": ANSWER, "input_mode": "text"})
    answers_sent += 1
    check("mock answer accepted", code == 200 and "overall" in res, (code, str(res)[:200]))
    next_q = res.get("next_question")
    if next_q:
        served_ids.append(next_q["question"]["id"])
        mock_categories.append(next_q["question"]["category"])

check("mock served planned_total questions", len(served_ids) == 3, served_ids)
check("NO repeated questions within the mock session", len(set(served_ids)) == len(served_ids), served_ids)
mock_domain = sum(1 for i in served_ids if i.startswith("qa"))
check("mock interview questions are QA/role-based", mock_domain >= 2, f"ids={served_ids} cats={mock_categories}")

code, report = call("POST", f"/api/interview/sessions/{session_id}/finish")
check("mock finished with report", code == 200 and report.get("overall_score", 0) > 0, (code, report))
mock_score = report["overall_score"]

# ------------------------------------------------------------------ TEST 1 + 2: analytics reflect activity
code, an1 = call("GET", "/api/analytics")
code2, an2 = call("GET", "/api/analytics")
check("analytics has_data", code == 200 and an1["has_data"] is True, (code, an1))
check("analytics deterministic (two reads identical)", an1 == an2, "")
check("questions_answered matches 6 prep + 3 mock answers", an1["questions_answered"] == 9, an1["questions_answered"])
check("exactly 1 completed mock", an1["sessions_completed"] == 1, an1["sessions_completed"])
check("trend score equals the real report score",
      len(an1["trend"]) == 1 and an1["trend"][0]["score"] == mock_score,
      (an1["trend"], mock_score))
check("weekly values within 0-100", all(0 <= w["avg"] <= 100 for w in an1["weekly"]), an1["weekly"])
check("no random percentages: avg_overall is a real derived integer",
      isinstance(an1["avg_overall"], int) and 0 <= an1["avg_overall"] <= 100, an1["avg_overall"])

# ------------------------------------------------------------------ TEST 3: practice summary counts
code, sh = call("GET", "/api/speech/history")
check("speech history has the 3 attempts", code == 200 and len(sh["attempts"]) == 3, sh)
check("speech history avg matches analytics speech_avg", sh["avg_communication"] == an1["speech_avg"],
      (sh["avg_communication"], an1["speech_avg"]))

# ------------------------------------------------------------------ TEST 9 (part 2): QA-specific plan
code, plan = call("POST", "/api/placement/plan/generate")
check("plan generated", code == 200 and plan["plan"]["total"] > 0, (code, plan))
plan_a = plan["plan"]
titles = [t["title"] for w in plan_a["weeks"] for t in w["tasks"]]
cats = [t["category"] for w in plan_a["weeks"] for t in w["tasks"]]
check("plan task count N is real (16 tasks, 4 weeks x 4)", plan_a["total"] == 16 and len(titles) == 16, plan_a["total"])
check("every task has unique taskId + category + completed flag",
      len({t["taskId"] for w in plan_a["weeks"] for t in w["tasks"]}) == 16
      and all(t["category"] for w in plan_a["weeks"] for t in w["tasks"])
      and all(t["completed"] is False for w in plan_a["weeks"] for t in w["tasks"]), cats)
check("plan is QA-specific (>=8 tasks mention testing/QA)",
      sum(1 for t in titles if re.search(r"\btest|qa\b|selenium|bug|regression|defect", t, re.I)) >= 8, titles)
check("plan mentions Selenium and test cases",
      any("selenium" in t.lower() for t in titles) and any("test case" in t.lower() for t in titles), titles)
check("plan has Testing category tasks", "Testing" in cats, cats)

# ------------------------------------------------------------------ TEST 4: placement percentages consistency
code, pl = call("GET", "/api/placement")
check("placement has_data", code == 200 and pl["has_data"] is True, (code, pl))
check("placement areas within 0-100", all(0 <= a["percent"] <= 100 for a in pl["areas"]), pl["areas"])

# ------------------------------------------------------------------ /api/progress single source of truth
code, prog = call("GET", "/api/analytics/progress")
check("progress endpoint 200 + has_data", code == 200 and prog["has_data"] is True, (code, prog))
m = prog["modules"]
check("resumeAnalysis module == resume score", m["resumeAnalysis"] == resume_score, (m["resumeAnalysis"], resume_score))
check("placementReadiness == Placement page overall", m["placementReadiness"] == pl["overall"],
      (m["placementReadiness"], pl["overall"]))
check("interviewPreparation > 0 (activity exists)", m["interviewPreparation"] > 0, m)
check("speechPractice > 0 (activity exists)", m["speechPractice"] > 0, m)
check("mockInterview > 0 (activity exists)", m["mockInterview"] > 0, m)
check("progress activity speech_attempts == analytics speech_attempts",
      prog["activity"]["speech_attempts"] == an1["speech_attempts"], prog["activity"])
check("progress activity plan_total == plan total", prog["activity"]["plan_total"] == plan_a["total"], prog["activity"])
check("progress deterministic (second read identical)", call("GET", "/api/analytics/progress")[1] == prog, "")

# ------------------------------------------------------------------ TEST 5: complete 2 tasks -> 2/N
task_ids = [t["id"] for w in plan_a["weeks"] for t in w["tasks"]]
for tid in task_ids[:2]:
    code, updated = call("PATCH", f"/api/placement/plan/tasks/{tid}", {"status": "done"})
    check(f"task {tid} toggled done", code == 200, (code, updated))
n = plan_a["total"]
expected_pct = round(2 / n * 100)
check("2/N tasks after completing 2", updated["completed"] == 2 and updated["total"] == n,
      (updated["completed"], updated["total"]))
check("plan progress == round(2/N*100)", updated["progress"] == expected_pct,
      (updated["progress"], expected_pct))

# ------------------------------------------------------------------ TEST 6: refresh persistence
code, plan_after = call("GET", "/api/placement/plan")
check("refresh: completed tasks persisted server-side",
      plan_after["completed"] == 2 and plan_after["progress"] == expected_pct, plan_after)
done_flags = [t["completed"] for w in plan_after["weeks"] for t in w["tasks"]]
check("refresh: exactly 2 tasks marked completed", sum(done_flags) == 2, done_flags)

# progress module placementReadiness must still match the Placement page after completion
code, pl2 = call("GET", "/api/placement")
code, prog2 = call("GET", "/api/analytics/progress")
check("progress stays consistent with placement after completion",
      prog2["modules"]["placementReadiness"] == pl2["overall"], (prog2["modules"], pl2["overall"]))

# ------------------------------------------------------------------ TEST 7: logout + login again
code, lg = call("POST", "/api/auth/login", {"email": email_a, "password": "Secret@123"}, auth=False)
check("re-login works", code == 200 and lg.get("access_token"), (code, lg))
TOKEN = lg["access_token"]
code, plan_login = call("GET", "/api/placement/plan")
code, an_login = call("GET", "/api/analytics")
check("after re-login: plan progress unchanged",
      plan_login["completed"] == 2 and plan_login["progress"] == expected_pct, plan_login)
check("after re-login: analytics unchanged",
      an_login["questions_answered"] == an1["questions_answered"] and an_login["speech_attempts"] == an1["speech_attempts"],
      an_login)

# ------------------------------------------------------------------ TEST 10: Java role -> Java plan + Java questions
full_profile = {
    "name": "Scenario A", "phone": "+91 90000 00001", "college": "Scenario College",
    "degree": "B.Tech", "department": "Computer Science", "year_of_study": "4th Year",
    "cgpa": 8.1, "skills": ["Java", "Spring Boot", "SQL"],
    "preferred_career": "Java Developer", "experience_level": "Beginner",
    "daily_study_minutes": 90,
}
code, prof2 = call("PUT", "/api/users/me", full_profile)
career_set = code == 200 and (prof2.get("profile") or {}).get("preferred_career") == "Java Developer"
if not career_set:
    full_profile["preferred_career"] = "Backend Developer"
    code, prof2 = call("PUT", "/api/users/me", full_profile)
    check("profile updated for Java test (alias path)", code == 200, (code, prof2))
else:
    check("profile role set to Java Developer", True)

code, plan_java = call("POST", "/api/placement/plan/generate")
java_titles = [t["title"] for w in plan_java["plan"]["weeks"] for t in w["tasks"]]
check("Java plan generated (different from QA plan)", plan_java["plan"]["total"] > 0
      and set(java_titles) != set(titles), java_titles[:4])
check("plan is Java-specific (Java + OOP + exceptions + spring/REST)",
      any("java" in t.lower() for t in java_titles)
      and any("exception" in t.lower() for t in java_titles)
      and any("thread" in t.lower() for t in java_titles)
      and any("spring" in t.lower() for t in java_titles), java_titles)

# profile change must flow into prep questions (career sync fix)
code, jq = call("GET", "/api/interview/prep/next")
code, jq2 = call("GET", "/api/interview/prep/next")
java_qs = [x["id"] for x in (jq, jq2)]
check("prep questions follow the NEW role (Java)", any(i.startswith("jv") for i in java_qs), java_qs)

# ------------------------------------------------------------------ TEST 8: user B isolation
TOKEN = None
code, bs = call("POST", "/api/auth/signup",
                {"name": "Scenario B", "email": email_b, "password": "Secret@123"}, auth=False)
check("B signup", code in (200, 201) and bs.get("access_token"), (code, bs))
TOKEN = bs["access_token"]

code, b_an = call("GET", "/api/analytics")
check("B analytics empty (has_data False)", code == 200 and b_an["has_data"] is False, b_an)
check("B sees zero questions/sessions/speech", b_an["questions_answered"] == 0 and b_an["attempts"] == 0
      and b_an["speech_attempts"] == 0, b_an)
code, b_prog = call("GET", "/api/analytics/progress")
check("B progress: has_data False and ALL modules 0%",
      b_prog["has_data"] is False and all(v == 0 for v in b_prog["modules"].values()), b_prog)
check("B progress has zero activity", all(v == 0 for v in b_prog["activity"].values()), b_prog["activity"])
code, b_plan = call("GET", "/api/placement/plan")
check("B plan empty: 0/0 tasks · 0%", b_plan["total"] == 0 and b_plan["completed"] == 0
      and b_plan["progress"] == 0, b_plan)
code, b_pl = call("GET", "/api/placement")
check("B placement has no data", code == 200 and b_pl["has_data"] is False, b_pl)
code, b_sh = call("GET", "/api/speech/history")
check("B speech history empty + no avg", b_sh["attempts"] == [] and b_sh["avg_communication"] == 0, b_sh)
code, b_para = call("GET", "/api/speech/paragraph")
check("B gets own fresh paragraph (not A's)", code == 200 and b_para["text"] not in {p["text"] for p in paras},
      b_para["text"][:60])

# A's data still intact after B visited (note: TEST 10 regenerated A's plan,
# which intentionally resets its completion state — plan must still be A's own)
TOKEN = lg["access_token"]
code, a_again = call("GET", "/api/analytics")
code, a_plan_again = call("GET", "/api/placement/plan")
check("A's data unaffected by B",
      a_again["questions_answered"] == 9 and a_plan_again["total"] == 16,
      (a_again["questions_answered"], a_plan_again["total"]))

# ------------------------------------------------------------------ cleanup temp users
from app.core.database import SessionLocal as _SL  # noqa: E402
from app.models import User as _U  # noqa: E402
_db = _SL()
for em in (email_a, email_b):
    u = _db.query(_U).filter(_U.email == em).first()
    if u:
        _db.delete(u)
_db.commit()
_db.close()
print("cleanup: scenario users deleted")

total = len(PASSED)
print(f"\n==================================================\nRESULT: {sum(PASSED)}/{total} passed")
sys.exit(0 if all(PASSED) else 1)
