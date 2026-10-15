"""Interview-style reading paragraphs for Speech Practice (module 8).

Every call to generate_paragraph() assembles a NEW paragraph from
professional, interview-flavoured sentence slots — never one hardcoded
paragraph. Combinatorics: 10 topics x 3-4 slots x 3-4 variants gives tens of
thousands of distinct paragraphs, and a per-user recent-history check keeps
the same text from coming back twice in a row (in-process memory + the
user's stored SpeechAnalysis rows).

Paragraphs are 80-150 words, moderately complex, and model exactly what a
candidate must do in an interview: explain reasoning, weigh trade-offs,
communicate clearly.
"""
import random
import re
from typing import Dict, List, Optional

# Each topic: 3-4 ordered sentence slots; a paragraph picks one variant per slot.
_SLOTS: List[List[List[str]]] = [
    # --- 1. Problem solving & debugging ------------------------------------
    [
        ["Effective problem solving requires more than spotting the immediate symptom, because the visible failure is rarely the real defect.",
         "When a system breaks under load, the first instinct to patch the symptom is exactly what separates a quick fix from a durable solution.",
         "In any production incident, the pressure to restore service quickly has to be balanced against the discipline of finding the underlying cause."],
        ["A candidate must isolate the problem methodically, reproduce it reliably, and test one hypothesis at a time instead of guessing at random changes.",
         "The professional approach is to gather evidence first — logs, metrics, and reproduction steps — and only then form and test a hypothesis.",
         "That means measuring before changing anything, narrowing the scope with every experiment, and resisting the temptation to ship an untested patch."],
        ["Communicating the reasoning clearly matters as much as the fix itself, because stakeholders need to understand what failed and why it will not fail again.",
         "Explaining the root cause in plain language, with evidence, turns a stressful incident into a demonstration of engineering judgement.",
         "A clear written summary of the cause, the fix, and the prevention plan is often worth more than the fix alone."],
        ["Finally, the chosen approach must balance performance, reliability, and maintainability — an elegant solution that nobody can maintain is not actually a solution.",
         "The last step is an honest trade-off review: does this fix hold up at scale, can the team maintain it, and what does it cost in complexity?",
         "Ultimately, good engineers commit to the approach that balances speed of recovery today against stability tomorrow, and they document the decision."],
    ],
    # --- 2. Ownership & mistakes -------------------------------------------
    [
        ["Taking ownership of a mistake begins with acknowledging it early, because hiding a problem almost always makes it more expensive to fix.",
         "In professional settings, the fastest way to lose trust is not to make an error but to let one be discovered by someone else.",
         "When something goes wrong on a project, the first responsible act is to raise it immediately, with facts rather than excuses."],
        ["A mature response focuses on impact and containment: who is affected, what can be reduced right now, and what must wait for a permanent fix.",
         "The next step is to assess the blast radius honestly — which users, systems, or deadlines are affected — and to contain the damage before investigating.",
         "That means communicating impact to the people who depend on the work, then fixing forward with a clear plan and realistic timelines."],
        ["Ownership also means studying the conditions that allowed the mistake, whether that was missing tests, unclear requirements, or a rushed review process.",
         "After the immediate fire is out, the deeper work is asking why the process permitted the error and changing that process, not blaming a person.",
         "The retrospective matters more than the apology, because it converts an individual slip into an organisational improvement."],
        ["Handled this way, a visible failure becomes evidence of reliability — teams trust people who surface problems, fix them, and make recurrence unlikely.",
         "Over time this habit builds a reputation for dependability: people who admit errors quickly are the ones given responsibility for critical systems.",
         "In an interview, describing a failure this way — impact, action, and lasting change — demonstrates exactly the accountability employers screen for."],
    ],
    # --- 3. Learning new technology ----------------------------------------
    [
        ["Learning a new technology under deadline pressure is less about raw speed than about having a deliberate strategy for building competence.",
         "Whenever a project demands a tool I have never used, I treat the first days as a structured exploration rather than a frantic search for answers.",
         "Confronting an unfamiliar framework or language is a normal part of professional work, and the approach taken in the first week decides the outcome."],
        ["I start from the official documentation and one small working example, because a running baseline teaches the vocabulary faster than any tutorial playlist.",
         "The first move is to get something minimal running end to end, which exposes the core concepts and produces a safe base to experiment against.",
         "My method is to skim the primary documentation for structure, then immediately build the smallest useful thing that touches every major concept."],
        ["From there, deliberate practice matters: rebuilding a familiar project in the new technology reveals gaps that passive reading never surfaces.",
         "Porting something I have already built forces me to translate old knowledge into new syntax, which quickly exposes the gaps that reading alone hides.",
         "The real learning happens when I try to solve a problem I already understand and compare how the new tool changes the solution."],
        ["Asking focused questions of experienced colleagues, and documenting what I learn, turns an individual sprint of learning into a durable team asset.",
         "Sharing notes, examples, and gotchas with the team multiplies the value of the effort and invites corrections before bad habits form.",
         "By combining documentation, small builds, review from seniors, and written summaries, unfamiliar technology becomes dependable within a realistic timeframe."],
    ],
    # --- 4. Teamwork & code review ------------------------------------------
    [
        ["Working effectively in a team means optimising for the team's output rather than personal credit, and code review is where that shows most clearly.",
         "Collaboration quality is easiest to observe in code reviews, where the goal is a better codebase rather than a defended ego.",
         "On any shared codebase, the review process is the main place where individual habits either strengthen or erode team standards."],
        ["A useful review comment explains the problem and its consequence, proposes an alternative, and distinguishes blocking issues from optional preferences.",
         "Good feedback is specific and kind: it names the line, explains the risk, suggests a fix, and separates must-change defects from matters of taste.",
         "The discipline is to critique the code, never the author, and to mark clearly which comments are requirements and which are suggestions."],
        ["Disagreements about design are resolved with criteria — performance data, maintainability, team conventions — rather than with seniority or volume.",
         "When two approaches both work, the decision should rest on evidence and agreed principles, so the outcome feels owned by the whole team.",
         "Healthy teams settle technical debates by writing down the trade-offs and choosing against explicit criteria that survive the next disagreement."],
        ["The result is a codebase the whole team understands, fewer defects reaching production, and juniors who grow because every review is a small lesson.",
         "Done consistently, this culture produces shared ownership of quality, faster onboarding, and steady growth for less experienced engineers.",
         "What compounds over months is not any single review but the shared understanding and rising baseline of quality that the process creates."],
    ],
    # --- 5. Technical decisions & trade-offs --------------------------------
    [
        ["Every meaningful technical decision is a trade-off, and the ability to explain those trade-offs is what interviewers are really probing.",
         "Choosing a technology or an architecture is rarely a matter of right and wrong; it is a matter of which constraints matter most right now.",
         "Good engineering decisions start from requirements and constraints, not from whatever tool is currently fashionable."],
        ["I evaluate options against explicit criteria — performance targets, team familiarity, ecosystem maturity, operational cost, and how reversible the choice is.",
         "My approach is to list the two or three realistic options, score them against the constraints that actually matter, and say out loud what each choice sacrifices.",
         "The discipline is to name the criteria before naming a winner, so the decision is a comparison of options rather than a defence of a preference."],
        ["A one-way decision deserves more deliberation than a reversible one; a choice that is cheap to undo should be made quickly and revisited with real data.",
         "It helps to classify decisions by reversibility: quick bets on easily changed things, careful analysis only where the choice will be expensive to reverse.",
         "Time spent deliberating should be proportional to the cost of being wrong — reversible choices deserve speed, irreversible ones deserve evidence."],
        ["Communicating the chosen trade-off, in writing, keeps future teammates from relitigating the decision without knowing why it was made.",
         "A short design note — context, options considered, decision, and expected consequences — saves the next engineer months of confusion.",
         "The final responsibility is documentation: recording what was chosen, what was rejected, and what evidence would justify revisiting the choice."],
    ],
    # --- 6. Deadlines & prioritisation --------------------------------------
    [
        ["Competing deadlines are inevitable, so professionals are judged less by the pressure they face than by the system they use to prioritise it.",
         "When several deliverables demand attention at once, an improvised response produces stress, while a written list produces a plan.",
         "Multiple urgent tasks are not a signal to work faster; they are a signal to decide deliberately what order matters most."],
        ["I list every commitment, estimate impact and effort, and rank by value to the user and to the team — not by which task is merely the loudest.",
         "The first step is an honest inventory of everything pending, each tagged with its true deadline, its impact, and the effort it realistically needs.",
         "Prioritisation starts by separating what is urgent from what is important, because those two lists are rarely the same list."],
        ["Scope is the adjustable variable: when time is short, I agree with stakeholders on a reduced but complete deliverable rather than a full feature done halfway.",
         "Rather than delivering everything late, it is usually better to negotiate scope early and ship a smaller slice that is genuinely done.",
         "A partially complete feature often satisfies nobody, so cutting scope to protect quality and deadlines is a strength, not an admission of failure."],
        ["Communicating status early — especially the bad news — gives stakeholders time to adjust, and it converts surprises into decisions.",
         "Regular, honest progress updates mean that even a slipping date is a planned adjustment instead of a last-minute crisis.",
         "In the end, reliability comes from this loop: transparent priorities, protected focus time, and early warnings whenever reality diverges from the plan."],
    ],
    # --- 7. Explaining to non-technical stakeholders ------------------------
    [
        ["Communicating technical work to non-technical stakeholders is a core professional skill, because decisions about budget and priority rest with them.",
         "Engineers who cannot explain their work to business audiences end up having their decisions made for them by people with less information.",
         "Technical depth loses its value if the people funding the work cannot understand what was done and why it mattered."],
        ["The effective pattern is to lead with the outcome — what the user gains or the risk removed — and only then describe the mechanism in plain language.",
         "I structure explanations as outcome first, mechanism second: state what changed for the business, then explain briefly how the technology achieved it.",
         "Analogies anchored in the audience's world work far better than jargon; the goal is shared understanding, not an accurate transfer of detail."],
        ["Precision matters where it changes the decision — costs, risks, and timelines deserve real numbers — while implementation detail belongs in an appendix.",
         "The discipline is to know which details are decision-relevant: money, risk, and dates get exact figures, while internal architecture stays one level up.",
         "Details earn their place only when they change what the listener will do; everything else is saved for the follow-up questions."],
        ["Checking understanding with a summary question, and inviting disagreement, turns a presentation into a conversation the audience actually owns.",
         "Ending with 'here is what I need from you, and here is what happens next' converts an explanation into forward motion.",
         "Practised consistently, this style builds the trust that lets an engineer influence decisions instead of merely reporting on them."],
    ],
    # --- 8. Quality & attention to detail -----------------------------------
    [
        ["Attention to detail is not perfectionism; it is the practice of noticing the small failures that quietly compound into large ones.",
         "In software, the defects that reach users are rarely exotic — they are small oversights that a systematic habit would have caught.",
         "Quality is less about heroic testing at the end and more about small, consistent checks built into every stage of the work."],
        ["It shows up in unglamorous places: reading the requirement twice, testing the edge case, questioning data that looks too convenient, writing error messages people can act on.",
         "The habit is concrete — verify assumptions before building on them, exercise the boundaries, and treat anything that 'works on my machine' as unproven.",
         "Practically, it means checking the input nobody will send, the empty state nobody will look at, and the failure path nobody plans to demo."],
        ["Systems thinking helps: automated checks, checklists, and peer review catch what individual vigilance eventually misses.",
         "Individual care is necessary but not sufficient, so I lean on tests, linters, and reviews to make quality independent of how tired anyone is.",
         "The professional safeguard is to design processes that assume human fallibility — automation and review catch what attention alone will not."],
        ["Users experience the details directly: a broken empty state or a wrong error message damages trust as surely as a crash does.",
         "Polish is not decoration; it is the visible evidence that someone cared about every path through the product, not just the happy one.",
         "Teams known for detail win a particular kind of trust — users assume, usually correctly, that the invisible parts were cared for too."],
    ],
    # --- 9. Feedback & growth -----------------------------------------------
    [
        ["Receiving feedback well is a professional skill in itself, because growth depends on information that is sometimes uncomfortable to hear.",
         "Most people claim to welcome feedback; far fewer have a repeatable way of extracting its value without taking it as a verdict on their worth.",
         "In any serious team, feedback is the main mechanism by which ability improves, which makes handling it gracefully a practical career asset."],
        ["The useful response is to separate the signal from the delivery: even bluntly worded comments usually contain an accurate observation worth acting on.",
         "I try to listen for the underlying observation rather than the tone, ask one clarifying question, and then write down the concrete change it implies.",
         "Defensiveness closes the channel instantly, so the practical habit is to thank the reviewer, ask for an example, and go away to verify it."],
        ["Acting on feedback visibly — and closing the loop with the person who gave it — turns an evaluation into an ongoing coaching relationship.",
         "Reporting back a month later with what changed shows the feedback was real work, not a polite conversation that evaporated.",
         "The follow-through matters more than the agreement: feedback that produces no visible change was, functionally, ignored."],
        ["Over time this habit compounds: people who metabolise feedback quickly improve faster than equally talented people who deflect it.",
         "Careers tend to diverge less on raw talent than on the speed of the learn-apply-recheck loop that feedback makes possible.",
         "Interviewers ask failure and feedback questions precisely to observe this loop, because it predicts performance better than any single skill."],
    ],
    # --- 10. Ambiguity & requirements ---------------------------------------
    [
        ["Real projects rarely arrive with complete requirements, so the ability to work productively with ambiguity is a core engineering skill.",
         "Ambiguity in requirements is not an obstacle to complain about; it is the normal starting condition of every meaningful project.",
         "Specifications are always incomplete in ways that matter, and waiting for perfect clarity is usually just delay in a more respectable costume."],
        ["The professional response is to make assumptions explicit early, state them in writing, and get them confirmed by whoever owns the decision.",
         "My habit is to write down the assumptions I am about to build on, rank them by how expensive it would be to be wrong, and confirm the risky ones first.",
         "Instead of either freezing in uncertainty or guessing silently, I surface my interpretation explicitly so it can be corrected before it hardens into code."],
        ["Prototypes and thin vertical slices are cheaper than documents for resolving ambiguity, because people react concretely to what they can see and click.",
         "A rough working slice answered more questions in an afternoon than three rounds of specification documents ever did.",
         "Showing a small, disposable implementation shifts the conversation from abstract debate to specific, decidable feedback."],
        ["As understanding improves, the plan is revised openly — changing course based on new information is diligence, not indecision.",
         "The discipline is to treat the early plan as provisional by design, updating it without embarrassment as reality supplies better information.",
         "Handled this way, ambiguity becomes manageable: explicit assumptions, fast feedback, and documented revisions replace guesswork with a traceable process."],
    ],
]

_TOPIC_LABELS = [
    "Problem Solving", "Ownership & Accountability", "Learning Agility", "Teamwork & Code Review",
    "Technical Decisions", "Prioritisation", "Stakeholder Communication", "Quality Mindset",
    "Growth & Feedback", "Handling Ambiguity",
]

_PARAGRAPH_BANK: Dict[str, dict] = {}          # id -> question-style dict for scoring
_recent_by_user: Dict[int, List[str]] = {}     # user_id -> last paragraph texts (in-process)
_MAX_RECENT = 12
_counter = 0

_WORD_RE = re.compile(r"[a-zA-Z']+")


def _word_count(text: str) -> int:
    return len(_WORD_RE.findall(text))


def generate_paragraph(user_id: int, exclude_texts: Optional[List[str]] = None) -> dict:
    """Assemble a fresh interview-style paragraph, avoiding this user's recent ones."""
    global _counter
    recent = set(_recent_by_user.get(user_id, [])) | set(exclude_texts or [])

    text = ""
    topic = ""
    best_text, best_topic, best_ok = "", "", False
    for _ in range(12):  # bounded retries; collisions are astronomically unlikely
        topic_idx = random.randrange(len(_SLOTS))
        slots = _SLOTS[topic_idx]
        parts = [random.choice(variants) for variants in slots]
        candidate = " ".join(parts)
        wc = _word_count(candidate)
        in_range = 80 <= wc <= 150
        if not best_text or (in_range and not best_ok):
            best_text, best_topic, best_ok = candidate, _TOPIC_LABELS[topic_idx], in_range
        text, topic = best_text, best_topic
        if text not in recent and in_range:
            break

    _counter += 1
    pid = f"para_{_counter}_{random.randint(100, 999)}"
    wc = _word_count(text)
    bank_entry = {
        "id": pid,
        "category": "Interview Communication",
        "topic": topic,
        "difficulty": "Intermediate",
        "question": text,
        "concepts": ["fluency", "pronunciation", "sentence flow", "professional vocabulary"],
        # keywords for reading-accuracy scoring: the paragraph's own significant words
        "keywords": _significant_words(text),
        "hint": None,
        "explanation": "Read the paragraph aloud at a steady pace, then compare your transcript with the original to check fluency and word accuracy.",
    }
    _PARAGRAPH_BANK[pid] = bank_entry
    # keep the bank bounded (long-running process)
    if len(_PARAGRAPH_BANK) > 500:
        for k in list(_PARAGRAPH_BANK.keys())[:200]:
            _PARAGRAPH_BANK.pop(k, None)

    user_recent = _recent_by_user.setdefault(user_id, [])
    user_recent.append(text)
    del user_recent[:-_MAX_RECENT]

    return {"id": pid, "text": text, "word_count": wc, "topic": topic}


def get_paragraph_question(paragraph_id: str) -> Optional[dict]:
    """The scoring-ready question dict for a paragraph id served earlier."""
    return _PARAGRAPH_BANK.get(paragraph_id)


def significant_words_from(text: str) -> List[str]:
    """Fallback keyword extraction for unknown/stale paragraph ids."""
    return _significant_words(text)


def _significant_words(text: str, limit: int = 14) -> List[str]:
    stop = set("""the a an and or but because so that this these those of in on at to for with by from
    is are was were be been being it its their there they you your we our not no if then than as into
    more most less what which who whom when where how why all any both each few other some such only
    own same too very can will just should now does do did done has have had having would could may
    might must one two three first second third every people person""".split())
    counts: Dict[str, int] = {}
    for w in _WORD_RE.findall(text.lower()):
        if len(w) > 3 and w not in stop:
            counts[w] = counts.get(w, 0) + 1
    ranked = sorted(counts.keys(), key=lambda w: -counts[w])
    return ranked[:limit]
