"""Adaptive interview engine (modules 6-8).

Everything an interviewer does lives here:
  * pick_next_question()   — adaptive, personalized, non-repetitive selection
  * evaluate_answer()      — rule-based scoring + fresh natural feedback
  * analyze_speech()       — observable speech/content analysis (module 8)
  * final_evaluation()     — session-level report with personalized advice

Rule-based and free forever; an LLM provider can override any piece via
the same functions (see ai_service.py pattern).
"""
import random
import re
from collections import Counter
from typing import Dict, List, Optional

from app.services.question_bank import (
    CS_CORE,
    HR,
    PROJECT_TEMPLATES,
    QUESTION_BY_ID,
    domain_ids_for,
    pool_for_career,
    primary_ids_for,
)

FILLER_WORDS = [
    "um", "uh", "like,", "you know", "basically", "actually", "literally",
    "sort of", "kind of", "i mean", "yeah", "okay so", "so yeah",
]

STRUCTURE_MARKERS = [
    "first", "second", "third", "finally", "for example", "for instance",
    "in my project", "for example,", "such as", "because", "therefore",
    "as a result", "in summary", "to summarize", "step", "then",
]

TECH_TERM_RE = re.compile(r"\b(api|database|query|server|client|component|function|class|"
                          r"algorithm|complexity|array|object|index|token|request|response|"
                          r"framework|schema|cache|async|deploy|test|endpoint|model)\b", re.I)


# --------------------------------------------------------------------------
# question selection
# --------------------------------------------------------------------------
def _difficulty_rank(d: str) -> int:
    return {"Beginner": 0, "Intermediate": 1, "Advanced": 2}.get(d, 1)


def _rank_to_difficulty(rank: int) -> str:
    return ["Beginner", "Intermediate", "Advanced"][max(0, min(2, rank))]


def _seen_ids(answers: List[dict]) -> set:
    return {a.get("question_id") for a in answers if a.get("question_id")}


def _weak_topics(answers: List[dict]) -> List[str]:
    """Topics the user scored below 55 on — engine retests these later."""
    weak = []
    for a in answers:
        if a.get("overall", 0) < 55 and a.get("topic") and a["topic"] not in weak:
            weak.append(a["topic"])
    return weak


def pick_next_question(
    career: str,
    difficulty: str,
    session_type: str,
    answers: List[dict],
    profile: dict,
    question_number: int,
    total_planned: int,
) -> dict:
    """Select the next question. Returns the question dict plus a natural
    interviewer transition line. Adapts to level, history, weak topics,
    and (for role interviews) the user's actual resume projects."""
    seen = _seen_ids(answers)
    target_rank = _difficulty_rank(difficulty)

    # adaptive difficulty: 2 strong answers in a row -> harder; 2 weak -> easier
    recent = [a.get("overall", 0) for a in answers[-2:]]
    if len(recent) == 2 and all(s >= 75 for s in recent):
        target_rank += 1
    elif len(recent) == 2 and all(s < 45 for s in recent):
        target_rank = max(0, target_rank - 1)

    # ---- HR interview: HR pool only
    if session_type == "hr":
        candidates = [q for q in HR if q["id"] not in seen]
        if not candidates:
            candidates = list(HR)
        q = random.choice(candidates)
        return {**q, "transition": _transition(None, q, question_number)}

    # ---- build the technical candidate pool (career pools + skill-matched pools)
    pool = pool_for_career(career, profile.get("skills"))
    unseen = [q for q in pool if q["id"] not in seen] or list(pool)
    domain_ids = domain_ids_for(career, profile.get("skills"))
    primary_ids = primary_ids_for(career, profile.get("skills"))

    # ---- mixed/quick: weave in HR questions
    if session_type in ("mixed", "quick") and question_number >= 2:
        hr_seen = seen
        hr_pool = [q for q in HR if q["id"] not in hr_seen]
        if hr_pool and (question_number % 3 == 0):
            q = random.choice(hr_pool)
            return {**q, "transition": _transition(answers[-1] if answers else None, q, question_number)}

    # ---- 1. weak-topic retest (only later in the session)
    weak = _weak_topics(answers)
    if weak and question_number >= 3 and random.random() < 0.45:
        retests = [q for q in unseen if q["topic"] in weak
                   and _difficulty_rank(q["difficulty"]) <= target_rank]
        if retests:
            q = random.choice(retests)
            note = " Let's revisit this area — it came up earlier."
            return {**q, "transition": _transition(answers[-1] if answers else None, q, question_number) + note}

    # ---- 2. project questions from the resume (role/mixed interviews)
    projects = _resume_projects(profile)
    if projects and session_type in ("role", "mixed") and question_number >= 2 and random.random() < 0.5:
        proj = random.choice(projects)
        tpl = random.choice(PROJECT_TEMPLATES)
        qtext = tpl["template"].format(project=proj)
        return {
            "id": f"proj_{proj[:20]}_{tpl['template'][:10]}".replace(" ", "_"),
            "category": "Your Projects",
            "topic": f"Project: {proj[:30]}",
            "difficulty": difficulty,
            "question": qtext,
            "concepts": tpl["concepts"],
            "keywords": tpl["keywords"],
            "hint": "Use the STAR shape: what you built, how, the hard part, and the outcome.",
            "explanation": "Interviewers use project questions to test depth beyond theory. Structure your answer: context → your specific contribution → technical decisions and why → result/what you learned.",
            "transition": _transition(answers[-1] if answers else None, None, question_number),
        }

    # ---- 3. skill-specific question when the user claims a matching skill
    if question_number <= 2 and random.random() < 0.35:
        skills = [s.lower() for s in (profile.get("skills") or [])]
        skill_q = [q for q in unseen
                   if _difficulty_rank(q["difficulty"]) <= target_rank + 1
                   and any(re.search(rf"\b{re.escape(sk[:5])}", q["question"].lower()) for sk in skills if len(sk) >= 4)]
        if skill_q:
            q = random.choice(skill_q)
            return {**q, "transition": _transition(answers[-1] if answers else None, q, question_number)}

    # ---- 4. difficulty-filtered pick with spread across categories.
    # Role-first: strongly prefer questions from the user's career/skill domain
    # pools so a QA Engineer gets testing questions, a Java user gets Java, etc.
    near = [q for q in unseen if abs(_difficulty_rank(q["difficulty"]) - target_rank) <= 1]
    candidates = near or unseen
    used_cats = {a.get("category") for a in answers}
    fresh_cats = [q for q in candidates if q["category"] not in used_cats]
    candidates = fresh_cats or candidates
    domain_candidates = [q for q in candidates if q["id"] in domain_ids]
    # role-first: when the career's primary pool still has candidates, stay
    # inside it so a Java Developer gets Java questions (and a QA engineer
    # testing questions) instead of a generic secondary domain — the secondary
    # pool only takes over once the primary is exhausted.
    primary_candidates = [q for q in domain_candidates if q["id"] in primary_ids]
    if primary_candidates:
        domain_candidates = primary_candidates
    if domain_candidates and (random.random() < 0.8 or not unseen_dominated(candidates, domain_ids)):
        q = random.choice(domain_candidates)
    else:
        q = random.choice(candidates)
    return {**q, "transition": _transition(answers[-1] if answers else None, q, question_number)}


def unseen_dominated(candidates: List[dict], domain_ids: set) -> bool:
    """True when domain questions already make up most of the candidate set —
    in that case a plain pick keeps variety without starving the core."""
    domain_count = sum(1 for q in candidates if q["id"] in domain_ids)
    return len(candidates) == 0 or domain_count / len(candidates) >= 0.6


def _resume_projects(profile: dict) -> List[str]:
    """Pull project names out of the latest resume analysis (if any)."""
    resume = profile.get("latest_resume") or {}
    text = " ".join([
        *(resume.get("strengths") or []),
        resume.get("summary", ""),
        " ".join(resume.get("skills") or []),
    ]).lower()
    # cheap heuristic: look for common project words in summary lines
    names = []
    for m in re.finditer(r"(?:project|built|developed|created)\s+([a-z][\w +\-]{3,40})", text):
        name = m.group(1).strip(" .,|-")
        if name and len(name) > 3:
            names.append(name.title()[:40])
    return names[:3]


_TRANSitions = {
    "open": [
        "Let's begin.",
        "Here's your first question.",
        "Ready? Here we go.",
    ],
    "between": [
        "Okay, next question.",
        "Here's the next one.",
        "Moving ahead,",
        "Let's continue.",
    ],
    "after_good": [
        "Good answer — let's keep going.",
        "Nice, that covered the key points.",
        "Solid. Let's try something a little different.",
        "That works. Next question.",
    ],
    "after_weak": [
        "Thanks for the attempt — the next one is different.",
        "Let's move to another area.",
        "Okay, let's try a fresh topic.",
        "We'll come back to that. Next question:",
    ],
    "follow_up": [
        "Can you explain how you would handle this situation?",
        "Let's explore that further.",
        "Tell me more about how that works in practice.",
    ],
}


def _transition(prev_answer: Optional[dict], next_q: Optional[dict], number: int) -> str:
    """Short natural interviewer line, varied per turn."""
    if number <= 1:
        return random.choice(_TRANSitions["open"])
    if prev_answer:
        if prev_answer.get("overall", 0) >= 70:
            return random.choice(_TRANSitions["after_good"])
        if prev_answer.get("overall", 0) < 45:
            return random.choice(_TRANSitions["after_weak"])
    return random.choice(_TRANSitions["between"])


# --------------------------------------------------------------------------
# answer evaluation
# --------------------------------------------------------------------------
def evaluate_answer(question: dict, answer: str, input_mode: str = "text") -> dict:
    """Score one answer and generate fresh, specific feedback."""
    text = (answer or "").strip()
    low = text.lower()
    words = re.findall(r"[a-zA-Z']+", low)

    if len(words) < 3:
        return _too_short_result(question, input_mode)

    # ---- relevance: keyword coverage
    qkws = question.get("keywords", [])
    hits = [k for k in qkws if k.lower() in low]
    coverage = len(hits) / max(1, len(qkws))
    relevance = round(min(96, 30 + coverage * 90))

    # ---- depth: technical vocabulary + examples
    tech_hits = len(set(TECH_TERM_RE.findall(low)))
    has_example = any(m in low for m in ["example", "e.g", "for instance", "in my project", "suppose", "consider"])
    depth = min(96, 25 + tech_hits * 11 + (14 if has_example else 0) + min(20, len(words) // 12))

    # ---- structure: markers, length bands
    markers = sum(1 for m in STRUCTURE_MARKERS if m in low)
    length = len(words)
    if length < 25:
        len_score = 45
    elif length < 60:
        len_score = 70
    elif length <= 220:
        len_score = 92
    else:
        len_score = 75
    structure = min(96, int(len_score * 0.75 + min(24, markers * 9)))

    # ---- clarity: sentence length + filler ratio
    sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
    avg_sent = length / max(1, len(sentences))
    fillers = sum(low.count(f) for f in FILLER_WORDS)
    filler_ratio = fillers / max(1, len(sentences))
    clarity = 92
    if avg_sent > 32:
        clarity -= 18
    elif avg_sent > 24:
        clarity -= 8
    clarity -= min(20, int(filler_ratio * 30))
    clarity = max(30, min(96, clarity))

    overall = round(relevance * 0.4 + depth * 0.25 + structure * 0.2 + clarity * 0.15)

    # ---- category sanity: programming questions expect *something* technical
    if question.get("category") not in ("HR / Behavioral", "HR / Closing") and tech_hits == 0:
        overall = min(overall, 52)

    feedback = _build_feedback(question, {
        "relevance": relevance, "depth": depth, "structure": structure,
        "clarity": clarity, "overall": overall,
    }, {
        "covered": hits, "missing": [k for k in qkws if k.lower() not in low],
        "word_count": length, "has_example": has_example, "fillers": fillers,
    })

    return {
        "question_id": question.get("id", ""),
        "scores": {"relevance": relevance, "depth": depth, "structure": structure, "clarity": clarity},
        "overall": overall,
        "feedback": feedback,
    }


def _too_short_result(question: dict, input_mode: str) -> dict:
    return {
        "question_id": question.get("id", ""),
        "scores": {"relevance": 0, "depth": 0, "structure": 0, "clarity": 0},
        "overall": 0,
        "feedback": {
            "explanation": question.get("explanation", ""),
            "strengths": [],
            "improvements": ["Your answer was too short to evaluate — aim for 3-5 sentences covering the key idea, an example, and why it matters."],
            "revise": question.get("topic", ""),
            "verdict": "Try again with a fuller answer",
        },
    }


# ---- feedback composition: many small pieces so no two answers read alike ----
_PRAISE = {
    "relevance": [
        "You addressed the question directly",
        "Your answer stayed on point",
        "You covered the core of what was asked",
        "The response matched what interviewers look for here",
    ],
    "depth": [
        "you backed it up with technical detail",
        "the technical vocabulary was appropriate",
        "you showed understanding beyond definitions",
        "the explanation had real substance",
    ],
    "structure": [
        "the answer followed a clear sequence",
        "your points were well organised",
        "it was easy to follow from start to finish",
        "good step-by-step flow",
    ],
    "clarity": [
        "the language was crisp and readable",
        "sentences were well-paced and clear",
        "you communicated without waffle",
        "the phrasing was clean",
    ],
}

_ADVICE = {
    "relevance": [
        "Work in more of the expected terms — mention {missing} explicitly",
        "Tie your answer back to the question; {missing} were expected but didn't come up",
        "Cover the key ideas directly: {missing}",
    ],
    "depth": [
        "Add one concrete example — 'in my project, I…' makes it memorable",
        "Explain the *why* behind the concept, not just the definition",
        "Mention trade-offs or complexity to show deeper understanding",
    ],
    "structure": [
        "Use a simple frame: definition → example → when to use it",
        "Signpost with 'first… then… finally…' so the flow is obvious",
        "Start with a one-line summary, then expand",
    ],
    "clarity": [
        "Break long sentences into two — aim for 15-20 words each",
        "Swap filler words (basically, actually) for a short pause",
        "Read your answer aloud once; tighten anything you stumble on",
    ],
}

_REVISE_LEAD = [
    "Worth revising: {topic}",
    "Concept to revise: {topic}",
    "Add to your revision list: {topic}",
    "Before the next attempt, review {topic}",
]


def _build_feedback(question: dict, s: dict, ctx: dict) -> dict:
    overall = s["overall"]
    strengths: List[str] = []
    improvements: List[str] = []

    # pick the 2 strongest dimensions for praise, weakest 1-2 for advice
    dims = ["relevance", "depth", "structure", "clarity"]
    ranked = sorted(dims, key=lambda d: s[d], reverse=True)
    for d in ranked[:2]:
        if s[d] >= 60:
            phrase = random.choice(_PRAISE[d])
            strengths.append(phrase[0].upper() + phrase[1:] + ("" if phrase.startswith("You") else ".") if False else phrase)
    for d in ranked[-2:]:
        if s[d] < 65:
            advice = random.choice(_ADVICE[d])
            if "{missing}" in advice:
                miss = ", ".join(ctx["missing"][:3]) if ctx["missing"] else "the core terms"
                advice = advice.format(missing=miss)
            improvements.append(advice)

    if ctx["has_example"] and ctx["word_count"] > 40:
        strengths.append("You used a concrete example — interviewers remember those")
    if not strengths:
        strengths.append("You made an honest attempt — every practice round builds the habit")
    if not improvements:
        improvements.append("Polish the wording and add one more real-world example to make it stand out")

    missing_note = ""
    if ctx["missing"] and s["relevance"] < 70:
        missing_note = f" Key ideas to include: {', '.join(ctx['missing'][:4])}."

    verdict = ("Strong answer" if overall >= 75 else
               "Good answer" if overall >= 60 else
               "Partially correct" if overall >= 40 else
               "Needs more preparation")

    revise = random.choice(_REVISE_LEAD).format(topic=question.get("topic", "this topic")) if overall < 70 else ""

    return {
        "explanation": question.get("explanation", "") + missing_note,
        "strengths": strengths[:3],
        "improvements": improvements[:3],
        "revise": revise,
        "verdict": verdict,
    }


# --------------------------------------------------------------------------
# speech analysis (module 8) — observable characteristics only
# --------------------------------------------------------------------------
def analyze_speech(question: dict, transcript: str, duration_seconds: Optional[float] = None,
                   input_mode: str = "voice") -> dict:
    """Analyze an answer for observable speech/content characteristics.
    No claims about confidence or emotion — only measurable traits."""
    text = (transcript or "").strip()
    low = text.lower()
    words = re.findall(r"[a-zA-Z']+", low)

    if len(words) < 3:
        return {
            "metrics": {"word_count": len(words)},
            "scores": {"clarity": 0, "relevance": 0, "pace": 0, "structure": 0, "communication": 0},
            "communication_score": 0,
            "feedback": {
                "well": [],
                "improve": ["The answer was too short — speak for 45-90 seconds and cover the idea, one example, and the takeaway."],
                "practice": "Re-record the same question and aim for 3-5 full sentences.",
            },
        }

    # ---- fillers & repetition
    fillers_found = {}
    for f in FILLER_WORDS:
        n = low.count(f)
        if n:
            fillers_found[f.strip(",")] = n
    total_fillers = sum(fillers_found.values())

    word_counts = Counter(words)
    repeated = [(w, c) for w, c in word_counts.most_common(6) if c >= 5 and len(w) > 5]
    excessive_repetition = bool(repeated)

    # ---- pace (words per minute) when we have timing
    wpm = None
    pace_score = 75
    if duration_seconds and duration_seconds >= 10:
        wpm = round(len(words) / (duration_seconds / 60))
        if 110 <= wpm <= 160:
            pace_score = 92
        elif 90 <= wpm < 110 or 160 < wpm <= 185:
            pace_score = 78
        elif 70 <= wpm < 90:
            pace_score = 62  # too slow — lots of pauses
        elif wpm > 185:
            pace_score = 60  # rushed
        else:
            pace_score = 50

    # ---- pause estimate: long gaps between short bursts aren't observable from
    # text alone, so we use duration vs word count as the honest proxy
    pauses_flag = None
    if duration_seconds and duration_seconds >= 10:
        expected = len(words) / 130 * 60  # seconds at ~130 wpm
        if duration_seconds > expected * 1.8 and len(words) > 40:
            pauses_flag = True
            pace_score = min(pace_score, 58)

    # ---- content scores (reuse answer evaluation)
    ev = evaluate_answer(question, transcript, input_mode)
    s = ev["scores"]

    clarity = max(30, min(96, s["clarity"] + (6 if total_fillers == 0 else -min(15, total_fillers * 3))))
    structure = s["structure"]
    relevance = s["relevance"]
    communication = round(clarity * 0.3 + structure * 0.25 + relevance * 0.3 + pace_score * 0.15)

    vocab_richness = round(len(set(words)) / max(1, len(words)) * 100)

    # ---- dynamic feedback
    well: List[str] = []
    improve: List[str] = []

    if relevance >= 70:
        well.append(random.choice([
            "Your answer directly addresses the question",
            "The content stayed relevant throughout",
            "You answered what was actually asked — that matters",
        ]))
    else:
        improve.append(random.choice([
            "Open with a one-line direct answer to the question before elaborating",
            "Some of the answer drifted from the question — anchor each point back to it",
        ]))

    if structure >= 70:
        well.append(random.choice([
            "The answer follows a logical structure from start to finish",
            "Your points came in a clear sequence",
        ]))
    else:
        improve.append(random.choice([
            "Signpost the structure: 'There are three parts… first… second…'",
            "Group related ideas together instead of interleaving them",
        ]))

    if total_fillers == 0:
        well.append("No filler words detected — clean delivery")
    elif total_fillers <= 3:
        improve.append(f"You used a few filler words ({', '.join(list(fillers_found)[:3])}) — replace them with a short pause")
    else:
        improve.append(f"{total_fillers} filler words detected ({', '.join(list(fillers_found)[:4])}) — pause silently instead; a pause reads as confidence")

    if wpm:
        if 110 <= wpm <= 160:
            well.append(f"Good speaking pace ({wpm} words per minute)")
        elif wpm > 175:
            improve.append(f"Speaking fast ({wpm} wpm) — slow down slightly on the key points")
        elif wpm < 95:
            improve.append(f"Speaking slowly ({wpm} wpm) — the pauses are long; keep momentum with shorter sentences")
        if pauses_flag:
            improve.append("Long pauses detected mid-answer — practise transitioning between points")

    if excessive_repetition:
        improve.append(f"'{repeated[0][0]}' repeats {repeated[0][1]} times — vary your word choice")
    if vocab_richness < 45:
        improve.append("Try mixing in more precise vocabulary — describe mechanisms, not just outcomes")

    if not improve:
        improve.append("Fine-tune by adding one concrete example to the middle of the answer")

    practice = random.choice([
        f"Re-answer this same question in 60 seconds: one idea, one example, one takeaway.",
        "Record yourself introducing your favourite project in 45 seconds and listen for fillers.",
        "Practise the 'rule of three': structure every answer around exactly three points.",
        "Read the model explanation aloud twice, then re-answer without notes.",
    ])

    return {
        "metrics": {
            "word_count": len(words),
            "duration_seconds": round(duration_seconds) if duration_seconds else None,
            "wpm": wpm,
            "fillers": fillers_found,
            "total_fillers": total_fillers,
            "vocabulary_richness": vocab_richness,
            "long_pauses_detected": pauses_flag,
        },
        "scores": {
            "clarity": clarity, "relevance": relevance, "pace": pace_score,
            "structure": structure, "communication": communication,
        },
        "communication_score": communication,
        "feedback": {"well": well[:4], "improve": improve[:4], "practice": practice},
    }


# --------------------------------------------------------------------------
# final session evaluation (module 7 report + feeds modules 9 & 10)
# --------------------------------------------------------------------------
def final_evaluation(session_type: str, career: str, answers: List[dict]) -> dict:
    if not answers:
        return {"overall_score": 0, "summary": "No answers were recorded in this session.", "suggestions": []}

    def avg(key_scores: List[dict], field: str) -> int:
        vals = [sc.get(field, 0) for sc in key_scores if sc]
        return round(sum(vals) / len(vals)) if vals else 0

    all_scores = [a.get("scores") or {} for a in answers]
    overalls = [a.get("overall", 0) for a in answers]

    technical = avg(all_scores, "depth")
    relevance = avg(all_scores, "relevance")
    structure = avg(all_scores, "structure")
    clarity = avg(all_scores, "clarity")
    overall = round(sum(overalls) / len(overalls))

    # strong/weak topics across the session
    topic_scores: Dict[str, List[int]] = {}
    for a in answers:
        topic_scores.setdefault(a.get("topic", "General"), []).append(a.get("overall", 0))
    topic_avg = {t: round(sum(v) / len(v)) for t, v in topic_scores.items()}
    strong = [t for t, v in sorted(topic_avg.items(), key=lambda x: -x[1]) if v >= 65][:3]
    weak = [t for t, v in sorted(topic_avg.items(), key=lambda x: x[1]) if v < 60][:3]

    # ---- personalized summary (varied, not a fixed paragraph)
    name = session_type.replace("_", " ")
    openers = [
        f"Across this {name} you answered {len(answers)} questions with an average score of {overall}%.",
        f"You completed {len(answers)} questions in this {name}, averaging {overall}%.",
        f"This {name} covered {len(answers)} questions; your overall score is {overall}%.",
    ]
    summary = random.choice(openers)
    if strong:
        summary += f" Strongest areas: {', '.join(strong)}."
    if weak:
        summary += f" Focus next on {', '.join(weak)}."
    if relevance - technical >= 12:
        summary += " Your answers stay on topic well — adding more technical depth is the clearest next win."
    elif technical - relevance >= 12:
        summary += " You clearly know the material — the growth area is framing answers so the relevance is obvious."
    elif overall >= 75:
        summary += " You're at interview-ready level on these topics; keep the streak with harder questions."
    elif overall >= 55:
        summary += " You're building solid momentum — a few more focused sessions will move the needle."
    else:
        summary += " Early days — each session now will show visible improvement."

    suggestions: List[str] = []
    if weak:
        suggestions.append(f"Revise {weak[0]} — it scored lowest this session")
    if structure < 60:
        suggestions.append("Practise the frame: direct answer → example → why it matters")
    if clarity < 60:
        suggestions.append("Do one timed voice answer per day; listen back for fillers and long sentences")
    if technical < 60:
        suggestions.append("Deepen one core topic per week with the roadmap resources")
    if not suggestions:
        suggestions.append("Raise the difficulty to Advanced and try a Mixed interview next")
    suggestions.append("Schedule your next mock interview in 2-3 days to lock in the progress")

    return {
        "overall_score": overall,
        "breakdown": {
            "technical_knowledge": technical,
            "answer_relevance": relevance,
            "problem_solving": round((technical + relevance) / 2),
            "communication": clarity,
            "answer_structure": structure,
        },
        "summary": summary,
        "strong_topics": strong,
        "weak_topics": weak,
        "suggestions": suggestions,
    }
