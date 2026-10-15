# CareerBoost — Complete Project Explanation

## 1. What it is

**CareerBoost** is a full-stack web platform that helps college students and fresh graduates
prepare for placements: analyze their resume, discover fitting careers, follow a guided
roadmap, practice interviews (text + voice), and keep a personalized daily study plan.

The standout design decision: **everything is 100% free and runs offline.** No paid AI APIs.
The "AI" is a rule-based engine shipped in the codebase, behind an abstraction interface so
a real LLM (free-tier) can be plugged in later by changing one config value — no route changes.

- **Demo login:** `demo@career.ai` / `demo1234` (auto-seeded on first backend start)
- **Stack:** FastAPI (Python) backend + React/Vite/Tailwind frontend
- **Database:** MySQL-ready via SQLAlchemy, with automatic fallback to SQLite (`career_assistant.db`) so it always runs locally with zero config

## 2. Tech stack

**Backend:** Python, FastAPI, SQLAlchemy 2.x, PyMySQL, PyJWT, Passlib (bcrypt hashing),
Pydantic v2 + pydantic-settings, pypdf (PDF parsing), python-multipart (uploads),
defusedxml (safe XML), Vosk (offline speech-to-text, optional).

**Frontend:** React 18, Vite 6, Tailwind CSS 3, React Router v6, Recharts (charts),
Lucide React (icons). Vite dev server proxies `/api` → `http://localhost:8000`.

**Runners:** `START.bat` / `STOP.bat` / `CHECK-DB.bat` — double-click to launch backend
(port 8000) + frontend (port 5173) and open Chrome automatically.

## 3. Architecture

```
project/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app: lifespan, CORS, 11 routers, lightweight migrations
│   │   ├── models.py            # SQLAlchemy models — 9 tables
│   │   ├── core/                # config (.env), database engine, security (JWT), error handlers
│   │   ├── routes/              # 11 modular routers (auth, users, resumes, careers, roadmap,
│   │   │                        #  planner, dashboard, interview, speech, analytics, placement)
│   │   ├── services/            # ALL business logic:
│   │   │                        #  ai_service.py         — provider abstraction (mock | openai)
│   │   │                        #  interview_engine.py   — adaptive Q selection + scoring (650 lines)
│   │   │                        #  question_bank.py      — ~830 lines of questions by category
│   │   │                        #  resume_parser.py      — PDF text extraction + rule-based scoring
│   │   │                        #  career_data.py        — career definitions, skills, learning paths
│   │   │                        #  roadmap_data.py       — 7-phase roadmaps per career
│   │   │                        #  email_service.py      — SMTP password-reset emails
│   │   │                        #  transcription.py      — offline Vosk speech-to-text fallback
│   │   │                        #  speech_paragraphs.py  — practice paragraphs
│   │   └── schemas_interview.py # Pydantic schemas for modules 6–10
│   ├── e2e_test.py              # 35 end-to-end API checks
│   ├── scenario_test_11.py      # 90-check, 2-user full lifecycle scenario
│   ├── verify_roadmap_behavior.py   # 25 game-style roadmap behavior checks
│   ├── regression_pending_question.py # 10 regression checks
│   ├── check_db.py              # DB inspector CLI
│   ├── career_assistant.db      # SQLite database (all user data)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/               # 14 pages: Login, Signup, ForgotPassword, Onboarding,
│   │   │                        #  Dashboard, ResumeAnalysis, Careers, Roadmap, InterviewPrep,
│   │   │                        #  MockInterview, SpeechPractice, Analytics, Placement, Profile
│   │   ├── components/          # Reusable UI
│   │   ├── context/             # Auth context (JWT storage, session)
│   │   └── services/api.js      # Single API layer: JWT headers, error unwrapping, 401 handling
│   └── package.json
├── START.bat / STOP.bat / CHECK-DB.bat
├── README.md / HOW-TO-RUN.txt
```

**Key architectural rules:**
1. **Routes are thin, services are fat** — routes validate/authenticate; all logic lives in `services/`.
2. **AI abstraction** — routes never talk to a vendor. `get_ai_service()` returns the configured provider; `AI_PROVIDER=mock` is the built-in rule-based engine, `openai` plugs in a real LLM later via the same interface.
3. **Modular by design** — every new module = one new route file + one `include_router()` line.

## 4. The 10 modules

| # | Module | Endpoints | What it does |
|---|--------|-----------|--------------|
| 1 | Auth & Profile | `/api/auth/*`, `/api/users/*` | Signup, login, logout, forgot/reset password, profile with completion % |
| 2 | Resume Analysis | `/api/resumes/*` | Drag-and-drop PDF upload, rule-based scoring, strengths/improvements, section & keyword checks, history |
| 3 | Career Recommendations | `/api/careers/recommend` | Ranked career cards with match %, skill gaps, "why this fits you", learning paths |
| 4 | Career Roadmaps | `/api/roadmap/*` | 7-phase visual roadmap per career, per-task checklists, resources, mini projects, readiness % |
| 5 | Study Planner | `/api/planner/*` | Daily plan sized to available minutes, mark done/skip/reschedule, weekly themed dashboard, auto-adjust |
| — | Dashboard | `/api/dashboard` | Aggregates resume score, career match, roadmap progress, today's plan |
| 6–7 | Interview Prep & Mock Interview | `/api/interview/*` | Adaptive question selection, answer scoring, session reports |
| 8 | Speech Practice | `/api/speech/*` | Voice practice with pace/pause/filler/vocabulary analysis |
| 9 | Performance Analytics | `/api/analytics/*` | Real activity aggregation only (interviews, speech, roadmap, planner) |
| 10 | Placement Readiness | `/api/placement/*` | Readiness % + personalized multi-week task plan |

## 5. Database schema (9 tables)

- **users** — email, hashed_password, name, is_active, onboarded, reset_code, reset_code_expires
- **profiles** — phone, college, degree, department, year, cgpa, skills (JSON), preferred_career, experience_level, interests (JSON), daily_study_minutes
- **resumes** — parsed text, score, strengths/improvements (JSON), is_latest (versioned history)
- **roadmap_progress** — per-career task completion
- **plan_tasks** — daily planner tasks (status, reschedule)
- **interview_sessions** — session state, status, pending_question (JSON)
- **interview_answers** — question_text, topic, difficulty, answer_text, input_mode, scores (JSON), overall, feedback (JSON)
- **speech_analyses** — transcript, metrics (JSON), scores (JSON), communication_score, week_key
- **placement_tasks** — week_number, focus, title, category, status

**Cascade rule:** every child table cascades from `User` (`all, delete-orphan`) — deleting a
user removes all their data. This matters (see §9, bug #2).

## 6. How the "AI" works (rule-based, free forever)

### Resume scoring (`resume_parser.py`)
pypdf extracts text → rule-based checks: contact info, section presence (education, skills,
projects, experience), keyword density, action verbs, quantified achievements → weighted
score + strengths + improvements list.

### Career recommendation (`career_data.py` + `ai_service.py`)
Scores each career against the profile's skills/interests/preferred career → match %,
skill gaps (what you lack), reasoning text, learning path.

### Interview engine (`interview_engine.py`, 650 lines)
- **`pick_next_question()`** — adaptive, personalized, non-repetitive. Question pools are
  mapped per career (e.g. `Java Developer` → [JAVA, SOFTWARE] pools). **Primary-pool
  preference:** the role's own domain pool is served first; the secondary pool takes over
  only when the primary is exhausted. Track/difficulty/personalization (resume-based project
  questions) all factor in.
- **`evaluate_answer()`** — rule-based scoring: relevance, structure (linking words like
  "first", "for example", "because"), clarity, technical vocabulary (regex tech-term list),
  length → overall score + fresh natural feedback (strengths / improvements / revise advice).
- **`analyze_speech()`** — observable metrics: pace (words/min), pauses, filler words
  ("um", "uh", "basically"...), vocabulary richness, structure markers → communication score.
- **`final_evaluation()`** — session-level report with personalized advice.

An LLM provider can override any of these pieces through the same function signatures.

### Question bank (`question_bank.py`, ~830 lines)
Hundreds of questions in categorized pools (JAVA, SOFTWARE, CLOUD, DSA, SQL, HR, aptitude...),
plus parameterized project-based templates that inject the user's actual resume projects.

## 7. Voice pipeline (speech-to-text, free & offline)

1. **Primary:** browser `SpeechRecognition` API (Chrome/Edge) transcribes live while the student speaks.
2. **Fallback:** if no live transcript arrived (embedded browsers, no Google speech backend),
   the frontend uploads the recorded audio → backend converts webm/opus → 16 kHz mono WAV
   (ffmpeg) → **Vosk** offline recognizer (model: `vosk-model-small-en-us-0.15`, no cloud, no key).
3. **Graceful degradation:** if Vosk/model is missing, `/api/speech/transcribe-status` reports
   it and the UI keeps the typed-answer path. Nothing ever hard-fails.

## 8. Security design (JWT + OTP password reset)

- **Auth:** stateless JWT (PyJWT), 7-day expiry, bcrypt password hashing, sent as
  `Authorization: Bearer` from `services/api.js`. 401 anywhere → auto-logout handling.
- **Password-reset OTP** (the flow we tested end-to-end):
  1. `POST /api/auth/forgot-password` → generates a **crypto-random 6-digit code**
     (`secrets.randbelow(900000) + 100000`), stores it **bcrypt-hashed** (never plaintext),
     sets **15-minute expiry**, emails it via SMTP (Gmail app password / Brevo / Mailtrap).
  2. **No account enumeration:** the API returns the *same* generic message whether or not
     the email exists. The code is never in any API response.
  3. **SMTP failure → 503** with a plain message — never leaks the code.
  4. `POST /api/auth/reset-password` → validates in order: password strength → pending
     request exists → not expired (UTC compare) → bcrypt compare of code. Wrong guesses do
     **not** consume the code.
  5. On success: new hash written, **code + expiry NULLed → single-use**.
- **Properties:** hashed at rest, time-boxed, single-use, enumeration-safe, never exposed.
- **Known gap (honest):** no rate limiter on the reset endpoint — a wrong code can be retried
  until the 15-min expiry. Bounded by the 6-digit space + window, but rate limiting would be
  the next hardening step.

## 9. Testing (all suites green)

| Suite | Scope | Result |
|---|---|---|
| `e2e_test.py` | 35 API checks: auth, resume, careers, roadmap, planner, dashboard, 401 guard | **35/35** |
| `verify_roadmap_behavior.py` | Game-style level lifecycle | **25/25** |
| `regression_pending_question.py` | Pending-question regression | **10/10** |
| `scenario_test_11.py` | 90 checks, 2 users: analytics, placement, isolation | **90/90 ×3 consecutive runs** |
| `vite build` | Production frontend build | ✅ (advisory: 723 kB chunk) |
| Browser walk | All 10 pages + logout→login round-trip | ✅ 0 console errors, all API 200 |

### Two real bugs were found and fixed during testing:

**Bug 1 — prep questions didn't follow a career change.**
`Java Developer` maps to `[JAVA, SOFTWARE]` and both counted equally as "domain", so a
Java-role student drew generic software questions ~30% of the time (scenario test flaked
~1 in 10 runs). **Fix:** added `primary_ids_for()` to the question bank + primary-pool
preference in the interview engine — the role's own pool is served first, the secondary
pool only takes over when exhausted. Verified: 39/40 draws now Java (was 28/40).

**Bug 2 — deleted users' speech data leaked into new accounts.**
`SpeechAnalysis` was the only child table missing `User`'s cascade. SQLite reuses row ids
after deletion, so a brand-new signup inherited a deleted test user's 9 speech attempts.
**Fix:** added the cascade relationship + purged the 9 orphaned rows. Verified: 0 orphans
across all 7 user-owned tables after 3 full cleanup runs.

**Testing hazard learned the hard way:** killing the uvicorn *wrapper* PID left its child
holding port 8000 — early test runs silently ran stale code. Always verify which process
owns the port before trusting a test run.

## 10. How to run

```
Backend:   cd backend && venv\Scripts\python -m uvicorn app.main:app --port 8000
Frontend:  cd frontend && npm run dev        # http://localhost:5173, proxies /api → :8000
Or:        double-click START.bat            # launches both + opens Chrome
```

`.env` needs nothing to run (SQLite fallback + rule-based AI). SMTP vars are only needed
for real password-reset emails. `AI_PROVIDER=mock` is the default; set `openai` + key to
use a real LLM later.

## 11. Known limitations / future work

- Frontend JS chunk is 723 kB (>500 kB warning) — code-splitting candidate.
- `e2e_test.py` never deletes its test accounts (harmless, but rows accumulate).
- `regression_pending_question.py` imports `requests`, which works but isn't declared in `requirements.txt`.
- No rate limiting on password reset (see §8).
- React Router v7 future-flag warnings (advisory only).
- With SMTP configured, e2e runs really send the reset email (by design).
