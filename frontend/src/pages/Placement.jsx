import { useCallback, useEffect, useState } from "react";
import { CalendarRange, CheckCircle2, CircleDashed, RefreshCw, ShieldCheck, Target } from "lucide-react";
import { api, getErrorMessage } from "../services/api.js";
import { useToast } from "../context/ToastContext.jsx";
import { EmptyState, ErrorState, LoadingSpinner, ProgressBar, ScoreRing, SectionHeader } from "../components/ui.jsx";

function TaskRow({ task, onToggle, busy }) {
  const done = task.status === "done";
  return (
    <button
      onClick={() => onToggle(task)}
      disabled={busy}
      className={`flex w-full items-start gap-3 rounded-2xl border p-3.5 text-left transition ${
        done ? "border-emerald-100 bg-emerald-50/60" : "border-slate-100 bg-white hover:border-brand-200 hover:shadow-soft"
      }`}
    >
      {done ? (
        <CheckCircle2 size={20} className="mt-0.5 shrink-0 text-emerald-500" />
      ) : (
        <CircleDashed size={20} className="mt-0.5 shrink-0 text-slate-300" />
      )}
      <span className="flex-1">
        <span className={`block text-sm font-semibold ${done ? "text-slate-400 line-through" : "text-slate-700"}`}>{task.title}</span>
        <span className="block text-xs text-slate-400">{task.detail} · Week {task.week_number} · {task.category && task.category !== "General" ? task.category : task.focus}</span>
      </span>
    </button>
  );
}

export default function Placement() {
  const toast = useToast();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);
  const [plan, setPlan] = useState(null);
  const [busyTask, setBusyTask] = useState(null);
  const [generating, setGenerating] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [p, pl] = await Promise.all([api.placement(), api.placementPlan()]);
      setData(p);
      setPlan(pl);
    } catch (e) {
      setError(getErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const toggleTask = async (task) => {
    const next = task.status === "done" ? "pending" : "done";
    setBusyTask(task.id);
    try {
      const updated = await api.setPlanTaskStatus(task.id, next);
      setPlan(updated);
      toast.success(next === "done" ? "Nice — task completed! 🎉" : "Task reopened");
    } catch (e) {
      toast.error(getErrorMessage(e));
    } finally {
      setBusyTask(null);
    }
  };

  const generate = async () => {
    setGenerating(true);
    try {
      const res = await api.generatePlan();
      setPlan(res.plan);
      toast.success(res.detail);
    } catch (e) {
      toast.error(getErrorMessage(e));
    } finally {
      setGenerating(false);
    }
  };

  if (loading) return <div className="flex justify-center py-24"><LoadingSpinner label="Checking your readiness…" /></div>;
  if (error) return <ErrorState message={error} onRetry={load} />;

  if (!data.has_data) {
    return (
      <div className="space-y-6">
        <SectionHeader title="Placement Readiness" subtitle="A progress indicator — never a prediction of results." />
        <EmptyState
          icon={Target}
          title="No preparation data yet"
          description="Analyse a resume, pick a career or answer a few prep questions — your readiness overview builds itself from real activity."
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Placement Readiness"
        subtitle="A preparation progress indicator — use it to guide effort, not to predict outcomes."
      />

      {/* overall + summary */}
      <div className="grid gap-6 lg:grid-cols-[auto_1fr]">
        <div className="rounded-3xl border border-slate-100 bg-white p-6 text-center shadow-soft">
          <p className="text-xs font-bold uppercase tracking-wide text-slate-400">Overall preparation</p>
          <div className="mt-3 flex justify-center">
            <ScoreRing value={data.overall} size={140} label="ready" />
          </div>
        </div>
        <div className="rounded-3xl border border-slate-100 bg-white p-6 shadow-soft">
          <p className="flex items-center gap-2 text-sm font-bold text-slate-700"><ShieldCheck size={16} className="text-brand-600" /> Your readiness summary</p>
          <p className="mt-2 text-sm leading-relaxed text-slate-600">{data.summary}</p>
          <div className="mt-4 space-y-2.5">
            {data.areas.map((a) => (
              <div key={a.label}>
                <div className="flex justify-between text-xs font-semibold">
                  <span className="text-slate-600">{a.label}</span>
                  <span className="text-slate-800">{a.percent}%</span>
                </div>
                <ProgressBar value={a.percent} size="sm" tone={a.percent >= 70 ? "emerald" : a.percent >= 50 ? "brand" : "rose"} />
                <p className="mt-0.5 text-[11px] text-slate-400">{a.detail}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ready / improve */}
      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-3xl border border-emerald-100 bg-emerald-50/50 p-5">
          <p className="text-xs font-bold uppercase tracking-wide text-emerald-600">Ready areas</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {data.ready_areas.length
              ? data.ready_areas.map((a) => <span key={a} className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-emerald-700 shadow-soft">{a}</span>)
              : <p className="text-sm text-slate-500">Keep practising — strong areas will show up here.</p>}
          </div>
        </div>
        <div className="rounded-3xl border border-amber-100 bg-amber-50/50 p-5">
          <p className="text-xs font-bold uppercase tracking-wide text-amber-600">Areas to improve</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {data.improve_areas.length
              ? data.improve_areas.map((a) => <span key={a} className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-amber-700 shadow-soft">{a}</span>)
              : <p className="text-sm text-slate-500">Nothing critical — you're on track.</p>}
          </div>
        </div>
      </div>

      {/* next steps */}
      <div className="rounded-3xl border border-slate-100 bg-white p-6 shadow-soft">
        <p className="text-sm font-bold text-slate-700">Recommended next steps</p>
        <ul className="mt-3 space-y-2">
          {data.next_steps.map((s, i) => (
            <li key={i} className="flex gap-2.5 rounded-xl bg-slate-50 px-4 py-2.5 text-sm text-slate-700">
              <span className="font-extrabold text-brand-600">{i + 1}.</span>{s}
            </li>
          ))}
        </ul>
      </div>

      {/* 4-week plan */}
      <div className="rounded-3xl border border-slate-100 bg-white p-6 shadow-soft">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="flex items-center gap-2 text-sm font-bold text-slate-700"><CalendarRange size={16} className="text-brand-600" /> My Placement Plan</p>
            {plan && <p className="mt-0.5 text-xs text-slate-400">{plan.completed}/{plan.total} tasks · {plan.progress}% complete</p>}
          </div>
          <button
            onClick={generate}
            disabled={generating}
            className="flex items-center gap-2 rounded-xl bg-brand-600 px-4 py-2 text-sm font-bold text-white shadow-lift transition hover:bg-brand-700 disabled:opacity-60"
          >
            {generating ? <LoadingSpinner size={15} /> : <RefreshCw size={15} />}
            {plan?.total ? "Regenerate Plan" : "Generate My Plan"}
          </button>
        </div>

        {plan && <ProgressBar value={plan.progress} className="mt-4" />}

        <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {plan?.weeks?.map((w) => (
            <div key={w.week} className="rounded-2xl border border-slate-100 p-4">
              <p className="text-xs font-bold uppercase tracking-wide text-brand-600">Week {w.week}</p>
              <p className="text-sm font-bold text-slate-700">{w.focus}</p>
              <div className="mt-3 space-y-2">
                {w.tasks.map((t) => <TaskRow key={t.id} task={t} onToggle={toggleTask} busy={busyTask === t.id} />)}
              </div>
            </div>
          ))}
        </div>

        {plan && !plan.total && (
          <p className="mt-3 text-sm text-slate-400">Generate a plan to get a personal 4-week schedule built from your weakest areas.</p>
        )}
      </div>
    </div>
  );
}
