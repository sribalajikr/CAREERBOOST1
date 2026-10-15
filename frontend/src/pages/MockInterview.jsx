import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowRight, CheckCircle2, Clock, History, Play, RotateCcw, Trophy } from "lucide-react";
import { Link } from "react-router-dom";
import { api, getErrorMessage } from "../services/api.js";
import { useToast } from "../context/ToastContext.jsx";
import { EmptyState, LoadingSpinner, ProgressBar, SectionHeader } from "../components/ui.jsx";

const TYPES = [
  { id: "quick", label: "Quick Interview", desc: "5 questions, all-round warm-up" },
  { id: "technical", label: "Technical Interview", desc: "Domain + skills focused" },
  { id: "hr", label: "HR Interview", desc: "Projects, teamwork, motivation" },
  { id: "mixed", label: "Mixed Interview", desc: "Technical + HR blend" },
  { id: "role", label: "Role-specific", desc: "Deep dive into your target role" },
];
const LEVELS = ["Beginner", "Intermediate", "Advanced"];
const DURATIONS = [5, 10, 15, 25, 40];

const fmtTimer = (s) =>
  `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

function ScoreBar({ label, value }) {
  return (
    <div>
      <div className="flex items-center justify-between text-xs font-semibold">
        <span className="capitalize text-slate-500">{label.replace(/_/g, " ")}</span>
        <span className="text-slate-800">{value}%</span>
      </div>
      <ProgressBar value={value} size="sm" tone={value >= 70 ? "emerald" : value >= 50 ? "brand" : "rose"} />
    </div>
  );
}

export default function MockInterview() {
  const toast = useToast();
  const [view, setView] = useState("setup"); // setup | live | feedback | report
  const [history, setHistory] = useState([]);
  const [form, setForm] = useState({ session_type: "quick", difficulty: "Intermediate", duration_minutes: 15 });
  const [starting, setStarting] = useState(false);

  const [session, setSession] = useState(null);      // {session_id, question_number, planned_total, question, transition}
  const [answer, setAnswer] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [lastFeedback, setLastFeedback] = useState(null);
  const [report, setReport] = useState(null);
  const [finishing, setFinishing] = useState(false);
  const [timeLeft, setTimeLeft] = useState(form.duration_minutes * 60); // countdown, exact selected duration
  const timeUpRef = useRef(false);

  const loadHistory = useCallback(async () => {
    try { setHistory(await api.sessionHistory()); } catch { /* non-fatal */ }
  }, []);
  useEffect(() => { loadHistory(); }, [loadHistory]);

  const start = async () => {
    setStarting(true);
    try {
      const q = await api.startSession(form);
      setSession(q);
      setAnswer("");
      setLastFeedback(null);
      setReport(null);
      // timer starts at EXACTLY the selected duration and resets per interview
      timeUpRef.current = false;
      setTimeLeft(form.duration_minutes * 60);
      setView("live");
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (e) {
      toast.error(getErrorMessage(e));
    } finally {
      setStarting(false);
    }
  };

  // every question starts with a completely fresh, empty answer area
  useEffect(() => {
    setAnswer("");
  }, [session?.session_id, session?.question_number]);

  const submitAnswer = async () => {
    if (!answer.trim()) {
      toast.info("Type (or dictate) your answer first.");
      return;
    }
    setSubmitting(true);
    try {
      const res = await api.answerSession(session.session_id, { answer, input_mode: "text" });
      setLastFeedback(res);
      setView("feedback");
    } catch (e) {
      toast.error(getErrorMessage(e));
    } finally {
      setSubmitting(false);
    }
  };

  const nextQuestion = () => {
    if (lastFeedback?.next_question) {
      setSession(lastFeedback.next_question);
      setAnswer("");
      setLastFeedback(null);
      setView("live");
      window.scrollTo({ top: 0, behavior: "smooth" });
    } else {
      finish();
    }
  };

  const finish = async () => {
    setFinishing(true);
    try {
      const rep = await api.finishSession(session.session_id);
      setReport(rep);
      setView("report");
      loadHistory();
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (e) {
      toast.error(getErrorMessage(e));
    } finally {
      setFinishing(false);
    }
  };

  // countdown — runs only during the live interview, never between interviews
  useEffect(() => {
    if (view !== "live") return undefined;
    const t = setInterval(() => setTimeLeft((s) => Math.max(0, s - 1)), 1000);
    return () => clearInterval(t);
  }, [view]);

  // time's up -> end through the existing completion flow
  useEffect(() => {
    if (view !== "live" || timeLeft !== 0 || timeUpRef.current) return;
    timeUpRef.current = true;
    if ((session?.question_number ?? 1) > 1) {
      toast.info("Time's up — here's your final report.");
      finish();
    } else {
      toast.info("Time's up! Pick a duration and start a new interview.");
      setView("setup");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view, timeLeft]);

  // ---------------- setup ----------------
  if (view === "setup") {
    const typeLabel = TYPES.find((t) => t.id === form.session_type)?.label;
    return (
      <div className="space-y-6">
        <SectionHeader
          title="AI Mock Interview"
          subtitle="A realistic interview that adapts every question to your profile, answers and goals."
        />
        <div className="rounded-3xl border border-slate-100 bg-white p-6 shadow-soft sm:p-8">
          <p className="text-xs font-bold uppercase tracking-wider text-slate-400">1 · Interview type</p>
          <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {TYPES.map((t) => (
              <button
                key={t.id}
                onClick={() => setForm((f) => ({ ...f, session_type: t.id }))}
                className={`rounded-2xl border-2 p-4 text-left transition ${
                  form.session_type === t.id
                    ? "border-brand-500 bg-brand-50 shadow-lift"
                    : "border-slate-100 hover:border-brand-200"
                }`}
              >
                <p className="text-sm font-bold text-slate-800">{t.label}</p>
                <p className="mt-0.5 text-xs text-slate-500">{t.desc}</p>
              </button>
            ))}
          </div>

          <p className="mt-6 text-xs font-bold uppercase tracking-wider text-slate-400">2 · Difficulty</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {LEVELS.map((l) => (
              <button
                key={l}
                onClick={() => setForm((f) => ({ ...f, difficulty: l }))}
                className={`rounded-xl px-4 py-2 text-sm font-semibold transition ${
                  form.difficulty === l ? "bg-brand-600 text-white shadow-lift" : "bg-slate-100 text-slate-600 hover:bg-brand-50"
                }`}
              >
                {l}
              </button>
            ))}
          </div>

          <p className="mt-6 text-xs font-bold uppercase tracking-wider text-slate-400">3 · Duration</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {DURATIONS.map((d) => (
              <button
                key={d}
                onClick={() => setForm((f) => ({ ...f, duration_minutes: d }))}
                className={`flex items-center gap-1.5 rounded-xl px-4 py-2 text-sm font-semibold transition ${
                  form.duration_minutes === d ? "bg-brand-600 text-white shadow-lift" : "bg-slate-100 text-slate-600 hover:bg-brand-50"
                }`}
              >
                <Clock size={14} /> {d} min
              </button>
            ))}
          </div>

          <button
            onClick={start}
            disabled={starting}
            className="mt-8 flex w-full items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-brand-600 to-brand-700 px-6 py-3.5 text-base font-bold text-white shadow-lift transition hover:brightness-110 disabled:opacity-60 sm:w-auto"
          >
            {starting ? <LoadingSpinner size={18} /> : <Play size={18} />}
            Start {typeLabel}
          </button>
        </div>

        {history.length > 0 && (
          <div className="rounded-3xl border border-slate-100 bg-white p-6 shadow-soft">
            <p className="flex items-center gap-2 text-sm font-bold text-slate-700"><History size={16} /> Past interviews</p>
            <div className="mt-3 space-y-2">
              {history.slice(0, 5).map((h) => (
                <div key={h.session_id} className="flex items-center justify-between rounded-xl bg-slate-50 px-4 py-2.5 text-sm">
                  <span className="font-semibold capitalize text-slate-600">{h.session_type} · {h.difficulty}</span>
                  <span className={`font-bold ${h.overall_score >= 70 ? "text-emerald-600" : h.overall_score >= 50 ? "text-amber-600" : "text-rose-500"}`}>
                    {h.overall_score}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  // ---------------- live / feedback ----------------
  if (view === "live" || view === "feedback") {
    const q = view === "feedback" ? lastFeedback?.next_question ?? session : session;
    const progress = session ? Math.round(((session.question_number - 1) / session.planned_total) * 100) : 0;
    return (
      <div className="mx-auto max-w-3xl space-y-5">
        {/* interview header */}
        <div className="rounded-2xl bg-gradient-to-r from-slate-800 to-slate-900 p-4 text-white shadow-lift sm:p-5">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs font-semibold text-slate-300">
            <span className="rounded-full bg-white/10 px-3 py-1 capitalize">{form.session_type} interview</span>
            <span className="capitalize">{form.difficulty}</span>
            <span>Question {session?.question_number} of {session?.planned_total}</span>
            <span
              className={`ml-auto flex items-center gap-1.5 rounded-full px-3 py-1 font-mono text-sm font-bold ${
                timeLeft <= 60 ? "bg-rose-500/20 text-rose-300" : "bg-white/10 text-white"
              }`}
              title="Time remaining"
            >
              <Clock size={14} /> {fmtTimer(timeLeft)}
            </span>
            <span>{progress}% done</span>
          </div>
          <div className="mt-3">
            <ProgressBar value={progress} size="sm" tone="brand" />
          </div>
        </div>

        {view === "feedback" && lastFeedback && (
          <div className="rounded-3xl border border-emerald-100 bg-white p-6 shadow-soft animate-fade-in sm:p-7">
            <p className="text-xs font-bold uppercase tracking-wider text-emerald-600">Coach feedback</p>
            <div className="mt-2 grid grid-cols-2 gap-3 sm:grid-cols-4">
              {Object.entries(lastFeedback.scores).map(([k, v]) => (
                <div key={k} className="rounded-xl bg-slate-50 p-3 text-center">
                  <p className="text-lg font-extrabold text-slate-800">{v}%</p>
                  <p className="text-[11px] font-semibold capitalize text-slate-400">{k}</p>
                </div>
              ))}
            </div>
            <p className="mt-4 text-sm font-bold text-slate-800">{lastFeedback.feedback.verdict} · {lastFeedback.overall}% overall</p>
            <p className="mt-2 text-sm leading-relaxed text-slate-600">{lastFeedback.feedback.explanation}</p>
            {lastFeedback.feedback.improvements.length > 0 && (
              <ul className="mt-3 space-y-1.5">
                {lastFeedback.feedback.improvements.map((s, i) => (
                  <li key={i} className="flex gap-2 text-sm text-slate-600"><span className="text-amber-500">→</span>{s}</li>
                ))}
              </ul>
            )}
          </div>
        )}

        {/* question */}
        <div className="rounded-3xl border border-slate-100 bg-white p-6 shadow-soft sm:p-8">
          {q?.transition && view === "live" && (
            <p className="mb-3 text-sm font-medium italic text-brand-600">"{q.transition}"</p>
          )}
          <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
            {q?.question.category} · {q?.question.topic}
          </p>
          <h2 className="mt-2 text-lg font-bold leading-snug text-slate-800 sm:text-xl">{q?.question.question}</h2>

          <textarea
            key={`${session?.session_id}-${q?.question?.id ?? "q"}`}
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            rows={6}
            disabled={view === "feedback"}
            placeholder="Take your time — structure your answer like you're speaking to the interviewer…"
            className="mt-5 w-full resize-y rounded-2xl border border-slate-200 p-4 text-sm text-slate-700 outline-none transition focus:border-brand-400 focus:ring-4 focus:ring-brand-100 disabled:bg-slate-50"
          />

          <div className="mt-4 flex flex-wrap items-center gap-3">
            {view === "live" ? (
              <>
                <button
                  onClick={submitAnswer}
                  disabled={submitting}
                  className="flex items-center gap-2 rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-bold text-white shadow-lift transition hover:bg-brand-700 disabled:opacity-60"
                >
                  {submitting ? <LoadingSpinner size={16} /> : <CheckCircle2 size={16} />} Submit Answer
                </button>
                <button
                  onClick={finish}
                  disabled={finishing}
                  className="ml-auto text-sm font-semibold text-slate-400 transition hover:text-rose-500"
                >
                  {finishing ? "Wrapping up…" : "End interview & see report"}
                </button>
              </>
            ) : (
              <button
                onClick={nextQuestion}
                className="flex items-center gap-2 rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-bold text-white shadow-lift transition hover:bg-brand-700"
              >
                {lastFeedback?.next_question ? "Next Question" : "See Final Report"} <ArrowRight size={16} />
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  // ---------------- report ----------------
  if (view === "report" && report) {
    return (
      <div className="mx-auto max-w-3xl space-y-6">
        <div className="rounded-3xl border border-slate-100 bg-white p-6 text-center shadow-soft sm:p-8">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-500">
            <Trophy size={30} />
          </div>
          <h2 className="mt-3 text-xl font-extrabold text-slate-800">Interview complete!</h2>
          <p className="mt-1 text-4xl font-extrabold text-brand-700">{report.overall_score}%</p>
          <p className="mx-auto mt-2 max-w-xl text-sm leading-relaxed text-slate-600">{report.summary}</p>
        </div>

        <div className="rounded-3xl border border-slate-100 bg-white p-6 shadow-soft">
          <p className="text-sm font-bold text-slate-700">Performance breakdown</p>
          <div className="mt-4 space-y-3">
            {Object.entries(report.breakdown).map(([k, v]) => <ScoreBar key={k} label={k} value={v} />)}
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="rounded-3xl border border-emerald-100 bg-emerald-50/50 p-5">
            <p className="text-xs font-bold uppercase tracking-wide text-emerald-600">Strong topics</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {report.strong_topics.length ? report.strong_topics.map((t) => (
                <span key={t} className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-emerald-700 shadow-soft">{t}</span>
              )) : <p className="text-sm text-slate-500">Answer a few more questions to reveal these.</p>}
            </div>
          </div>
          <div className="rounded-3xl border border-amber-100 bg-amber-50/50 p-5">
            <p className="text-xs font-bold uppercase tracking-wide text-amber-600">Needs work</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {report.weak_topics.length ? report.weak_topics.map((t) => (
                <span key={t} className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-amber-700 shadow-soft">{t}</span>
              )) : <p className="text-sm text-slate-500">Nothing critical — keep practising.</p>}
            </div>
          </div>
        </div>

        <div className="rounded-3xl border border-slate-100 bg-white p-6 shadow-soft">
          <p className="text-sm font-bold text-slate-700">Your personal improvement plan</p>
          <ul className="mt-3 space-y-2">
            {report.suggestions.map((s, i) => (
              <li key={i} className="flex gap-2.5 rounded-xl bg-slate-50 px-4 py-2.5 text-sm text-slate-700">
                <span className="font-extrabold text-brand-600">{i + 1}.</span>{s}
              </li>
            ))}
          </ul>
        </div>

        <div className="flex flex-wrap gap-3">
          <button
            onClick={() => setView("setup")}
            className="flex items-center gap-2 rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-bold text-white shadow-lift transition hover:bg-brand-700"
          >
            <RotateCcw size={16} /> New Interview
          </button>
          <Link
            to="/analytics"
            className="flex items-center gap-2 rounded-xl border border-slate-200 px-5 py-2.5 text-sm font-semibold text-slate-600 transition hover:border-brand-300 hover:text-brand-700"
          >
            View Analytics <ArrowRight size={16} />
          </Link>
        </div>
      </div>
    );
  }

  return (
    <EmptyState icon={Trophy} title="Something went wrong" description="Please reload the page to restart the interview." />
  );
}
