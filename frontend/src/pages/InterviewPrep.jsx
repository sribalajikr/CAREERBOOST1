import { useCallback, useEffect, useState } from "react";
import { ArrowRight, Eye, Lightbulb, ListChecks, RefreshCw, Trophy } from "lucide-react";
import { api, getErrorMessage } from "../services/api.js";
import { useToast } from "../context/ToastContext.jsx";
import {
  EmptyState, ErrorState, LoadingSpinner, ProgressBar, SectionHeader, SkillPill,
} from "../components/ui.jsx";

const DIFF_TONE = { Beginner: "emerald", Intermediate: "amber", Advanced: "rose" };

function VerdictBadge({ verdict, overall }) {
  const tone =
    overall >= 75 ? "bg-emerald-50 text-emerald-700 border-emerald-200"
    : overall >= 55 ? "bg-amber-50 text-amber-700 border-amber-200"
    : "bg-rose-50 text-rose-700 border-rose-200";
  return (
    <span className={`inline-block rounded-full border px-3 py-1 text-xs font-bold ${tone}`}>
      {verdict} · {overall}%
    </span>
  );
}

export default function InterviewPrep() {
  const toast = useToast();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [question, setQuestion] = useState(null);
  const [answer, setAnswer] = useState("");
  const [showHint, setShowHint] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [stats, setStats] = useState(null);
  const [answered, setAnswered] = useState(new Set());

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [q, s, h] = await Promise.all([api.prepNext(), api.prepStats(), api.prepHistory()]);
      setQuestion(q);
      setStats(s);
      setAnswered(new Set(h.answered_ids));
    } catch (e) {
      setError(getErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadAll(); }, [loadAll]);

  const submit = async () => {
    if (!answer.trim()) {
      toast.info("Write a short answer first — even 2–3 sentences help.");
      return;
    }
    setSubmitting(true);
    try {
      const res = await api.prepAnswer(question.id, answer);
      setResult(res);
      setAnswered((prev) => new Set([...prev, question.id]));
      const s = await api.prepStats();
      setStats(s);
    } catch (e) {
      toast.error(getErrorMessage(e));
    } finally {
      setSubmitting(false);
    }
  };

  const next = async () => {
    setAnswer("");
    setResult(null);
    setShowHint(false);
    setSubmitting(true);
    try {
      setQuestion(await api.prepNext());
    } catch (e) {
      toast.error(getErrorMessage(e));
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <div className="flex justify-center py-24"><LoadingSpinner label="Fetching your next question…" /></div>;
  if (error) return <ErrorState message={error} onRetry={loadAll} />;

  const attempted = stats?.attempted ?? 0;
  const avg = stats?.avg_score ?? 0;

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Technical Interview Prep"
        subtitle="Questions adapt to your career, skills and past answers — a few minutes a day builds real confidence."
      />

      {/* practice summary */}
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-2xl border border-slate-100 bg-white p-4 shadow-soft">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Questions attempted</p>
          <p className="mt-1 text-2xl font-extrabold text-slate-800">{attempted}</p>
        </div>
        <div className="rounded-2xl border border-slate-100 bg-white p-4 shadow-soft">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Average score</p>
          <p className="mt-1 text-2xl font-extrabold text-slate-800">{avg}%</p>
        </div>
        <div className="rounded-2xl border border-slate-100 bg-white p-4 shadow-soft">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Topics covered</p>
          <p className="mt-1 text-2xl font-extrabold text-slate-800">{stats?.topics_covered ?? 0}</p>
        </div>
      </div>

      {question && answered.has(question.id) && !result && (
        <div className="flex items-center gap-2 rounded-2xl border border-brand-100 bg-brand-50 px-4 py-3 text-sm text-brand-800">
          <Trophy size={16} /> You've answered this one before — acing it again still counts.
          <button onClick={next} className="ml-auto flex items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-bold text-white transition hover:bg-brand-700">
            New question <ArrowRight size={14} />
          </button>
        </div>
      )}

      {/* question card */}
      <div className="rounded-3xl border border-slate-100 bg-white p-6 shadow-soft sm:p-8">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-brand-50 px-3 py-1 text-xs font-bold text-brand-700">{question?.category}</span>
          <SkillPill skill={question?.topic} />
          <span className={`rounded-full border px-3 py-1 text-xs font-bold ${
            DIFF_TONE[question?.difficulty] === "emerald" ? "border-emerald-200 bg-emerald-50 text-emerald-700"
            : DIFF_TONE[question?.difficulty] === "rose" ? "border-rose-200 bg-rose-50 text-rose-700"
            : "border-amber-200 bg-amber-50 text-amber-700"}`}>
            {question?.difficulty}
          </span>
        </div>

        <h2 className="mt-4 text-lg font-bold leading-snug text-slate-800 sm:text-xl">{question?.question}</h2>

        {showHint && question?.hint && (
          <div className="mt-4 flex items-start gap-2 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-800 animate-fade-in">
            <Lightbulb size={16} className="mt-0.5 shrink-0" />
            <span><strong>Hint:</strong> {question.hint}</span>
          </div>
        )}

        {!result ? (
          <>
            <textarea
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              rows={5}
              placeholder="Explain it like you would to an interviewer — structure, examples, trade-offs…"
              className="mt-5 w-full resize-y rounded-2xl border border-slate-200 p-4 text-sm text-slate-700 outline-none transition focus:border-brand-400 focus:ring-4 focus:ring-brand-100"
            />
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <button
                onClick={submit}
                disabled={submitting}
                className="flex items-center gap-2 rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-bold text-white shadow-lift transition hover:bg-brand-700 disabled:opacity-60"
              >
                {submitting ? <LoadingSpinner size={16} /> : <ListChecks size={16} />}
                Submit Answer
              </button>
              <button
                onClick={() => setShowHint((v) => !v)}
                disabled={!question?.hint}
                className="flex items-center gap-2 rounded-xl border border-slate-200 px-5 py-2.5 text-sm font-semibold text-slate-600 transition hover:border-brand-300 hover:text-brand-700 disabled:opacity-40"
              >
                <Eye size={16} /> {showHint ? "Hide Hint" : "Show Hint"}
              </button>
              <button
                onClick={next}
                className="ml-auto flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold text-slate-500 transition hover:bg-slate-100 hover:text-slate-700"
              >
                Skip / Next Question <ArrowRight size={16} />
              </button>
            </div>
          </>
        ) : (
          <div className="mt-6 animate-fade-in space-y-4">
            <div className="grid gap-3 sm:grid-cols-4">
              {Object.entries(result.scores).map(([k, v]) => (
                <div key={k} className="rounded-xl bg-slate-50 p-3">
                  <p className="text-[11px] font-bold uppercase tracking-wide text-slate-400">{k}</p>
                  <p className="mt-0.5 text-lg font-extrabold text-slate-800">{v}%</p>
                  <ProgressBar value={v} size="sm" tone={v >= 70 ? "emerald" : v >= 50 ? "brand" : "rose"} />
                </div>
              ))}
            </div>

            <div className="rounded-2xl border border-slate-100 bg-slate-50/60 p-5">
              <VerdictBadge verdict={result.feedback.verdict} overall={result.overall} />
              <p className="mt-3 text-sm leading-relaxed text-slate-700">{result.feedback.explanation}</p>

              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <div>
                  <p className="text-xs font-bold uppercase tracking-wide text-emerald-600">What you did well</p>
                  <ul className="mt-2 space-y-1.5">
                    {result.feedback.strengths.map((s, i) => (
                      <li key={i} className="flex gap-2 text-sm text-slate-600"><span className="text-emerald-500">✓</span>{s}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <p className="text-xs font-bold uppercase tracking-wide text-amber-600">What to improve</p>
                  <ul className="mt-2 space-y-1.5">
                    {result.feedback.improvements.map((s, i) => (
                      <li key={i} className="flex gap-2 text-sm text-slate-600"><span className="text-amber-500">→</span>{s}</li>
                    ))}
                  </ul>
                </div>
              </div>

              <p className="mt-4 rounded-xl bg-brand-50 px-4 py-2.5 text-sm text-brand-800">
                <strong>Revise:</strong> {result.feedback.revise}
              </p>
            </div>

            <div className="flex flex-wrap gap-3">
              <button
                onClick={next}
                className="flex items-center gap-2 rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-bold text-white shadow-lift transition hover:bg-brand-700"
              >
                Next Question <ArrowRight size={16} />
              </button>
              <button
                onClick={() => { setResult(null); setAnswer(""); }}
                className="flex items-center gap-2 rounded-xl border border-slate-200 px-5 py-2.5 text-sm font-semibold text-slate-600 transition hover:border-brand-300 hover:text-brand-700"
              >
                <RefreshCw size={15} /> Try Again
              </button>
            </div>
          </div>
        )}
      </div>

      {attempted === 0 && (
        <EmptyState
          icon={ListChecks}
          title="Your prep streak starts here"
          description="Answer one question — the coach tailors everything after that to your answers."
        />
      )}
    </div>
  );
}
