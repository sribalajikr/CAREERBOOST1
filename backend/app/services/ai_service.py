"""AI service abstraction.

The app never talks to a vendor directly — everything goes through
`get_ai_service()`. The default `mock` provider is a rule-based engine that
works with zero API keys. Adding a real free-tier LLM later only requires
implementing `AIService` and registering it here — no other code changes.
"""
import logging
import re
from typing import List

from app.core.config import settings
from app.services.career_data import (
    CAREERS,
    INTEREST_KEYWORDS,
    PREFERRED_ALIASES,
    SKILL_ALIASES,
    SKILL_EQUIVALENTS,
)
from app.services.resume_parser import extract_text_from_pdf
from app.services.roadmap_data import ROADMAPS

logger = logging.getLogger("uvicorn.app")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def canonical_skill(s: str) -> str:
    n = _norm(s)
    n = re.sub(r"[.\-_]", " ", n)
    return SKILL_ALIASES.get(n, s.strip().title() if s.strip() else s.strip())


def extract_skills_from_text(text: str) -> List[str]:
    """Detect known skills inside free text (resume body or user input)."""
    low = f" {_norm(text)} "
    found = []
    # check aliases first (longer keys first so "rest api" beats "api")
    for alias in sorted(SKILL_ALIASES.keys(), key=len, reverse=True):
        target = SKILL_ALIASES[alias]
        if re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", low):
            if target not in found:
                found.append(target)
    # then direct mentions of catalog skills
    for career in CAREERS.values():
        for skill in career["core"] + career["nice"]:
            if _norm(skill) and re.search(rf"(?<![a-z0-9]){re.escape(_norm(skill))}(?![a-z0-9])", low):
                if skill not in found:
                    found.append(skill)
    return found


# ---------------------------------------------------------------- contracts
class ResumeAnalysis(dict):
    """Just a typed dict — kept simple on purpose."""


class AIService:
    """Interface every AI provider must implement."""

    name = "abstract"

    def analyze_resume(self, file_name: str, pdf_bytes: bytes, profile: dict) -> dict:
        raise NotImplementedError

    def recommend_careers(self, profile: dict, resume_skills: List[str] | None = None) -> List[dict]:
        raise NotImplementedError


# ------------------------------------------------------------ rule engine
class RuleBasedAIService(AIService):
    """Deterministic, explainable engine. Works fully offline, free forever."""

    name = "mock (rule-based)"

    # -------------------------------------------------------- resume
    SECTION_PATTERNS = {
        "Education": [r"education", r"b\.?tech", r"b\.?e\b", r"bachelor", r"university", r"college", r"cgpa", r"10th", r"12th"],
        "Skills": [r"skills", r"technical skills", r"technologies", r"programming"],
        "Projects": [r"projects?", r"project experience", r"academic projects"],
        "Certifications": [r"certifications?", r"certificates?", r"licensed"],
        "Experience": [r"experience", r"internship", r"employment", r"work history"],
        "Contact": [r"email", r"phone", r"linkedin", r"github", r"\+?\d[\d\s\-()]{8,}"],
        "Achievements": [r"achievements?", r"awards?", r"honor", r"hackathon"],
        "Summary": [r"summary", r"objective", r"profile", r"about me"],
    }

    ATS_KEYWORDS = [
        "python", "java", "c++", "sql", "javascript", "react", "node", "html", "css",
        "api", "git", "github", "docker", "aws", "linux", "machine learning", "data",
        "rest", "testing", "agile", "algorithms", "dsa", "oop", "mongodb", "pandas",
    ]

    ACTION_VERBS = [
        "built", "developed", "designed", "created", "implemented", "led", "improved",
        "optimized", "automated", "launched", "managed", "reduced", "increased", "achieved",
    ]

    def analyze_resume(self, file_name: str, pdf_bytes: bytes, profile: dict) -> dict:
        text = extract_text_from_pdf(pdf_bytes)
        low = text.lower()
        words = re.findall(r"[a-zA-Z]{3,}", low)
        word_count = len(words)

        if word_count < 40:
            return self._unreadable_result(file_name, profile)

        # 1. section presence
        present, missing = [], []
        for section, patterns in self.SECTION_PATTERNS.items():
            if any(re.search(p, low) for p in patterns):
                present.append(section)
            else:
                missing.append(section)

        skills = extract_skills_from_text(text)

        # 2. scoring
        score = 0
        section_score = sum(
            14 for s in ["Contact", "Education", "Skills", "Projects"] if s in present
        )
        section_score += 8 if "Experience" in present else 0
        section_score += 6 if "Certifications" in present else 0
        section_score += 4 if "Achievements" in present else 0
        section_score += 4 if "Summary" in present else 0
        score += min(section_score, 50)

        kw_hits = [k for k in self.ATS_KEYWORDS if k in low]
        score += min(20, len(kw_hits) * 2)

        skills_count = len(skills)
        score += 10 if skills_count >= 8 else (7 if skills_count >= 5 else (4 if skills_count >= 2 else 0))

        if 250 <= word_count <= 900:
            score += 10
        elif 150 <= word_count <= 1200:
            score += 6

        bullets = len(re.findall(r"[•\n]\s*[-–•*]|\u2022", text))
        has_numbers = bool(re.search(r"\d+%", text) or re.search(r"\d+\+", text))
        if bullets >= 5:
            score += 5
        if has_numbers:
            score += 5
        if "linkedin" in low:
            score += 2
        if "github" in low:
            score += 3

        score = max(5, min(98, score))

        strengths, improvements = [], []

        if "Education" in present:
            strengths.append("Clear education section — recruiters can see your background easily")
        else:
            improvements.append("Add an Education section with your degree, college and CGPA")
        if "Projects" in present:
            strengths.append("Projects included — great! They prove you can build real things")
            if not has_numbers:
                improvements.append("Add measurable results to projects (e.g., 'improved speed by 30%')")
        else:
            improvements.append("Add 2–3 projects with what you built and the tech you used")
        if "Skills" in present:
            strengths.append("Technical skills are listed clearly")
        else:
            improvements.append("Create a Skills section grouping languages, tools and frameworks")
        if "Experience" in present:
            strengths.append("Experience/internship section adds credibility")
        else:
            improvements.append("Add internships, freelancing or open-source contributions")
        if "Certifications" in present:
            strengths.append("Certifications show initiative to keep learning")
        else:
            improvements.append("Add 1–2 relevant certifications (free ones like Kaggle, AWS, Google work)")
        if "Contact" not in present:
            improvements.append("Add email, phone and LinkedIn/GitHub links at the top")
        if skills_count < 5:
            improvements.append("List more relevant technical skills (aim for 8–12)")
        if not has_numbers:
            improvements.append("Quantify achievements — numbers make your impact obvious")
        if word_count > 900:
            improvements.append("Your resume looks long — try to fit it on one page")
        if word_count < 250:
            improvements.append("Your resume looks thin — add project details and descriptions")
        if bullets < 5:
            improvements.append("Use bullet points for projects and experience instead of paragraphs")
        if "Achievements" not in present:
            improvements.append("Add achievements like hackathons, rankings or awards")

        if not improvements:
            improvements.append("Polish wording with stronger action verbs (built, led, improved)")
        if not strengths:
            strengths.append("You have a starting point — every suggestion below will raise your score")

        job_readiness = self._job_readiness(score, present, skills_count)

        return {
            "provider": self.name,
            "file_name": file_name,
            "score": score,
            "grade_label": self._grade(score),
            "summary": self._summary(score, skills),
            "word_count": word_count,
            "skills": skills[:14],
            "strengths": strengths[:6],
            "improvements": improvements[:7],
            "sections": {s: (s in present) for s in self.SECTION_PATTERNS},
            "missing_sections": missing,
            "keyword_coverage": {
                "found": kw_hits[:12],
                "missing": [k for k in self.ATS_KEYWORDS if k not in kw_hits][:8],
                "coverage_percent": round(len(kw_hits) / len(self.ATS_KEYWORDS) * 100),
            },
            "job_readiness": job_readiness,
            "formatting": self._formatting_notes(text, low, present, bullets, word_count),
        }

    def _formatting_notes(self, text: str, low: str, present: list, bullets: int, word_count: int) -> list:
        """Derive formatting observations from the actual extracted resume structure.
        Every note is {level, message} where level is ok | warn | error."""
        notes = []

        # 1. Section organization (which standard sections exist)
        expected = ["Contact", "Education", "Skills", "Projects", "Experience"]
        missing_core = [s for s in expected if s not in present]
        positions = []
        for s in expected:
            if s in present:
                m = re.search(self.SECTION_PATTERNS[s][0], low)
                if m:
                    positions.append((s, m.start()))

        if not missing_core:
            notes.append({"level": "ok", "message":
                "Your resume has a clear section structure — contact details, education, skills, "
                "projects and experience are all present and easy for recruiters to scan."})
        else:
            notes.append({"level": "warn", "message":
                "Section organization can be improved — the " + " and ".join(missing_core) +
                " section" + ("s are" if len(missing_core) > 1 else " is") + " missing, which breaks the standard resume flow."})

        # 2. Contact information placement
        email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
        if email_match:
            rel = email_match.start() / max(1, len(text))
            if rel < 0.2:
                notes.append({"level": "ok", "message":
                    "Contact information (email) sits near the top of the first page — exactly where recruiters expect it."})
            else:
                notes.append({"level": "warn", "message":
                    "Your email appears deep inside the document. Move contact details to the top so they are seen first."})
        else:
            notes.append({"level": "error", "message": "No email address was detected — add one at the top of the resume."})

        # 3. Heading consistency (section names standing on their own lines)
        heading_lines = 0
        for s in present:
            for p in self.SECTION_PATTERNS[s]:
                if re.search(rf"^\s*{p}", text, re.MULTILINE):
                    heading_lines += 1
                    break
        if present:
            ratio = heading_lines / len(present)
            if ratio >= 0.7:
                notes.append({"level": "ok", "message":
                    "Section headings are consistent — most stand on their own line in a uniform style."})
            else:
                notes.append({"level": "warn", "message":
                    "Heading style is inconsistent — put each section title (e.g. EDUCATION, PROJECTS) on its own line "
                    "in the same case style so the structure is obvious."})

        # 4. Bullet-point consistency (mixed bullet glyphs look messy)
        glyphs = set(re.findall(r"^\s*([\u2022\-\u2013\u2219*\u25cf])\s", text, re.MULTILINE))
        if bullets >= 5:
            if len(glyphs) <= 1:
                notes.append({"level": "ok", "message":
                    f"Bullet formatting is consistent — {bullets} bullets all use the same marker style."})
            else:
                shown = ", ".join(sorted(glyphs))
                notes.append({"level": "warn", "message":
                    f"Mixed bullet styles detected ({shown}). Standardize on one bullet character for a cleaner look."})
        else:
            notes.append({"level": "warn", "message":
                "Very few bullet points were detected — use consistent bullets for responsibilities and achievements."})

        # 5. Date formatting consistency (4-digit years vs mixed styles)
        years4 = re.findall(r"(?:19|20)\d{2}", text)
        years2 = re.findall(r"'\d{2}\b", text)
        if years2 and years4:
            notes.append({"level": "warn", "message":
                "Date formats are mixed (some 2-digit, some 4-digit years). Use one consistent style like 'Jun 2024 - Aug 2025'."})
        elif years4:
            notes.append({"level": "ok", "message":
                "Dates are formatted consistently (4-digit years), which keeps your timeline easy to follow."})

        # 6. Length / page structure
        if 250 <= word_count <= 900:
            notes.append({"level": "ok", "message":
                f"Length looks right for one page ({word_count} words) — well balanced between detail and readability."})
        elif word_count > 900:
            notes.append({"level": "warn", "message":
                f"At {word_count} words this likely spills past one page — trim older or less relevant content."})
        else:
            notes.append({"level": "warn", "message":
                f"Only {word_count} words detected — the page will look sparse; expand project and experience descriptions."})

        # 7. Professional profile links
        has_linkedin, has_github = "linkedin" in low, "github" in low
        if has_linkedin or has_github:
            links = ", ".join(n for n, ok in [("LinkedIn", has_linkedin), ("GitHub", has_github)] if ok)
            notes.append({"level": "ok", "message":
                f"Professional profile links ({links}) are included — a good sign of a professionally structured resume."})
        else:
            notes.append({"level": "warn", "message":
                "No LinkedIn or GitHub link found — adding them makes the resume look more professional and verifiable."})

        return notes

    def _grade(self, score: int) -> str:
        if score >= 85:
            return "Excellent"
        if score >= 70:
            return "Strong"
        if score >= 55:
            return "Good start"
        if score >= 40:
            return "Needs work"
        return "Needs attention"

    def _summary(self, score: int, skills: List[str]) -> str:
        top = ", ".join(skills[:4]) if skills else "your key skills"
        if score >= 85:
            return f"Fantastic! This is a professional-quality resume. Keep {top} highlighted and tailor it per job."
        if score >= 70:
            return f"Your resume is getting stronger! A few focused tweaks around {top} will push it to the top tier."
        if score >= 55:
            return f"Solid foundation detected. Strengthen your projects and skills like {top} to stand out."
        return "Good start! Add the missing sections below and this score will climb quickly."

    def _job_readiness(self, score: int, present: List[str], skills_count: int) -> int:
        ready = 0
        ready += min(45, int(score * 0.5))
        ready += 20 if "Projects" in present and "Education" in present else 5
        ready += 15 if skills_count >= 6 else (8 if skills_count >= 3 else 2)
        ready += 10 if "Experience" in present else 0
        ready += 10 if "Certifications" in present else 0
        return max(5, min(98, ready))

    def _unreadable_result(self, file_name: str, profile: dict) -> dict:
        return {
            "provider": self.name,
            "file_name": file_name,
            "score": 0,
            "grade_label": "Could not read",
            "summary": "We couldn't extract text from this PDF. If it's a scanned copy, try a text-based PDF export from Word/Google Docs.",
            "word_count": 0,
            "skills": [],
            "strengths": [],
            "improvements": [
                "Export your resume as a text-based PDF (not a scanned image)",
                "Make sure the PDF isn't password protected",
            ],
            "sections": {},
            "missing_sections": list(self.SECTION_PATTERNS),
            "keyword_coverage": {"found": [], "missing": [], "coverage_percent": 0},
            "job_readiness": 0,
            "formatting": [],
        }

    # -------------------------------------------------------- careers
    def recommend_careers(self, profile: dict, resume_skills: List[str] | None = None) -> List[dict]:
        user_raw: List[str] = list(profile.get("skills") or []) + list(resume_skills or [])
        user_skills: List[str] = []
        for s in user_raw:
            c = canonical_skill(s)
            if c and c not in user_skills:
                user_skills.append(c)
        user_low = " ".join(_norm(s) for s in user_skills)

        interests = " ".join(_norm(i) for i in (profile.get("interests") or []))
        interests += " " + _norm(profile.get("preferred_career") or "")
        degree = _norm(profile.get("degree") or "") + " " + _norm(profile.get("department") or "")
        experience = _norm(profile.get("experience_level") or "beginner")
        cgpa = profile.get("cgpa") or 0

        scored = []
        for name, info in CAREERS.items():
            core, nice = info["core"], info["nice"]
            have_core = [s for s in core if self._user_has(user_skills, user_low, s)]
            have_nice = [s for s in nice if self._user_has(user_skills, user_low, s)]
            missing = [s for s in core if s not in have_core]

            core_ratio = len(have_core) / len(core)
            nice_ratio = len(have_nice) / max(1, len(nice))

            match = core_ratio * 62 + nice_ratio * 23

            # interest alignment
            hints = INTEREST_KEYWORDS.get(name, [])
            interest_hits = sum(1 for h in hints if h in interests)
            match += min(10, interest_hits * 5)

            # department signals
            dept_bonus = 0
            if any(d in degree for d in ["computer", "information technology", "software", "it "]):
                if name in ("Software Developer", "Full Stack Developer", "Backend Developer", "Frontend Developer", "DevOps Engineer"):
                    dept_bonus = 4
            if any(d in degree for d in ["data", "statistics", "mathematic", "ai", "machine learning"]):
                if name in ("Data Analyst", "Data Scientist", "AI/ML Engineer"):
                    dept_bonus = 6
            if any(d in degree for d in ["electron", "electrical", "mechanical", "civil"]):
                if name in ("Cloud Engineer", "DevOps Engineer", "IoT"):
                    dept_bonus = 2
            match += dept_bonus

            # preferred career gets a boost
            preferred = _norm(profile.get("preferred_career") or "")
            pref_canon = PREFERRED_ALIASES.get(preferred, "")
            if pref_canon == name or _norm(name) == preferred:
                match += 14

            if cgpa >= 8.5:
                match += 2

            match = max(8, min(96, round(match)))

            # level suggestion
            if core_ratio >= 0.8 and experience == "advanced":
                level = "Advanced"
            elif core_ratio >= 0.45 or experience == "intermediate":
                level = "Intermediate"
            else:
                level = "Beginner"

            why = []
            if have_core:
                why.append(f"You already know {', '.join(have_core[:4])}")
            if interest_hits:
                why.append("It matches your stated interests")
            if pref_canon == name:
                why.append("It aligns with your preferred career")
            if dept_bonus:
                why.append("It fits your degree background")
            if missing and len(missing) <= len(core):
                why.append(f"Only {len(missing)} key skills to add: {', '.join(missing[:3])}")
            if not why:
                why.append("A growing field with strong entry-level demand")

            scored.append({
                "career": name,
                "description": info["description"],
                "match_percent": match,
                "level": level,
                "required_skills": core,
                "user_skills": have_core + have_nice,
                "missing_skills": missing,
                "why": why[:4],
                "learning_path": info["learning_path"],
                "salary_hint": info["salary_hint"],
            })

        scored.sort(key=lambda x: x["match_percent"], reverse=True)
        return scored[:6]

    @staticmethod
    def _user_has(user_skills: List[str], user_low: str, skill: str) -> bool:
        if skill in user_skills:
            return True
        # a concrete skill satisfies its conceptual parent (Java -> Programming Fundamentals)
        for eq in SKILL_EQUIVALENTS.get(skill, []):
            if eq in user_skills:
                return True
        aliases = {skill, _norm(skill)}
        for a in SKILL_ALIASES:
            if SKILL_ALIASES[a] == skill:
                aliases.add(a)
        return any(a in user_low for a in aliases if a)


class OpenAICompatibleService(AIService):
    """Optional provider for a real free-tier LLM (OpenAI-compatible endpoint).

    Implementations call out through the same interface; if the call fails we
    transparently fall back to the rule-based engine so the app never breaks.
    """

    name = "openai-compatible"

    def __init__(self):
        try:
            from openai import OpenAI  # optional dependency
            self.client = OpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL,
            )
            self.model = settings.OPENAI_MODEL
        except Exception as exc:  # noqa: BLE001
            logger.warning("OpenAI provider unavailable (%s); using rule engine.", exc)
            raise

    def analyze_resume(self, file_name: str, pdf_bytes: bytes, profile: dict) -> dict:
        base = RuleBasedAIService().analyze_resume(file_name, pdf_bytes, profile)
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a friendly resume coach for college students. Reply with simple, encouraging language."},
                    {"role": "user", "content": f"Rewrite this summary in one friendly sentence and 3 improvement tips:\n{base['summary']}\n{base['improvements']}"},
                ],
                max_tokens=300,
            )
            text = resp.choices[0].message.content.strip()
            base["summary"] = text.split("\n")[0][:280]
            base["provider"] = self.name
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM call failed (%s); keeping rule-based result.", exc)
        return base

    def recommend_careers(self, profile: dict, resume_skills=None) -> List[dict]:
        # career matching stays deterministic; an LLM can polish descriptions later
        return RuleBasedAIService().recommend_careers(profile, resume_skills)


def get_ai_service() -> AIService:
    if settings.AI_PROVIDER == "openai" and settings.OPENAI_API_KEY:
        try:
            return OpenAICompatibleService()
        except Exception:  # noqa: BLE001
            pass
    return RuleBasedAIService()


def roadmap_careers() -> List[str]:
    return list(ROADMAPS.keys())
