import { useCallback, useEffect, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip as RTooltip,
  XAxis, YAxis,
} from "recharts";
import { CalendarDays, MessageSquareText, Sparkles, TrendingUp, Trophy } from "lucide-react";
import { api, getErrorMessage } from "../services/api.js";
import { EmptyState, ErrorState, LoadingSpinner, ProgressBar, SectionHeader } from "../components/ui.jsx";

function TopicList({ title, tone, items, emptyText }) {
  return (
    <div className={`rounded-3xl border p-5 ${tone === "emerald" ? "border-emerald-100 bg-emerald-50/50" : "border-amber-100 bg-amber-50/50"}`}>
      <p className={`text-xs font-bold uppercase tracking-wide ${tone === "emerald" ? "text-emerald-600" : "text-amber-600"}`}>{title}</p>
      {items.length === 0 ? (
        <p className="mt-2 text-sm text-slate-500">{emptyText}</p>
      ) : (
        <div className="mt-3 space-y-2.5">
          {items.map((t) => (
            <div key={t.topic}>
              <div className="flex justify-between text-xs font-semibold">
                <span className="text-slate-700">{t.topic}</span>
                <span className="text-slate-500">{t.avg}% · {t.attempts}×</span>
              </div>
              <ProgressBar value={t.avg} size="sm" tone={tone} />
            </div>
          ))}
        </div>
      )}      </div>
  );
}

const MODULE_ROWS = [
  ["resumeAnalysis", "Resume Analysis"],
  ["interviewPreparation", "Interview Preparation"],
  ["speechPractice", "Speech Practice"],
  ["mockInterview", "Mock Interview"],
  ["planner", "Planner (Roadmap)"],
  ["placementReadiness", "Placement Readiness"],
];

export default function Analytics() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);
  const [progress, setProgress] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [a, p] = await Promise.all([
        api.analytics(),
        api.progress().catch(() => null), // module % single source of truth
      ]);
      setData(a);
      setProgress(p);
    } catch (e) {
      setError(getErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) return <div className="flex justify-center py-24"><LoadingSpinner label="Crunching your numbers…" /></div>;
  if (error) return <ErrorState message={error} onRetry={load} />;

  if (!data.has_data) {
    return (
      <div className="space-y-6">
        <SectionHeader title="Performance Analytics" subtitle="Real numbers from your actual practice — nothing fake, ever." />
        <EmptyState
          icon={TrendingUp}
          title="Complete your first interview to start seeing your progress."
          description="Answer technical prep questions, run a mock interview or record a speech answer — analytics light up immediately."
        />
      </div>
    );
  }

  const chartData = data.trend.map((t, i) => ({ name: `#${i + 1}`, score: t.score }));
  const chartTip = (
    <RTooltip
      contentStyle={{ borderRadius: 12, border: "1px solid #e2e8f0", fontSize: 12 }}
      formatter={(v) => [`${v}%`, "Score"]}
    />
  );

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Performance Analytics"
        subtitle="Every number here comes from your real interviews, prep answers and speech practice."
      />

      {/* headline stats */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { label: "Mock interviews", value: data.attempts, icon: Trophy },
          { label: "Questions answered", value: data.questions_answered, icon: MessageSquareText },
          { label: "Avg interview score", value: `${data.avg_overall}%`, icon: TrendingUp },
          { label: "Avg communication", value: `${data.speech_avg || data.avg_communication}%`, icon: Sparkles },
        ].map(({ label, value, icon: Icon }) => (
          <div key={label} className="rounded-2xl border border-slate-100 bg-white p-4 shadow-soft">
            <div className="flex items-center gap-2 text-slate-400">
              <Icon size={16} />
              <p className="text-xs font-semibold uppercase tracking-wide">{label}</p>
            </div>
            <p className="mt-1 text-2xl font-extrabold text-slate-800">{value}</p>
          </div>
        ))}
      </div>

      {/* trend chart */}
      <div className="rounded-3xl border border-slate-100 bg-white p-6 shadow-soft">
        <p className="text-sm font-bold text-slate-700">Interview performance trend</p>
        {chartData.length >= 2 ? (
          <div className="mt-4 h-56">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#64748b" }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "#64748b" }} />
                {chartTip}
                <Line type="monotone" dataKey="score" stroke="#4f46e5" strokeWidth={3} dot={{ r: 4, fill: "#4f46e5" }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p className="mt-2 text-sm text-slate-500">Complete one more mock interview to unlock the trend line.</p>
        )}
      </div>

      {/* weekly chart */}
      <div className="rounded-3xl border border-slate-100 bg-white p-6 shadow-soft">
        <p className="text-sm font-bold text-slate-700">Weekly progress</p>
        {data.weekly.length ? (
          <div className="mt-4 h-48">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.weekly} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="week" tick={{ fontSize: 10, fill: "#64748b" }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "#64748b" }} />
                {chartTip}
                <Bar dataKey="avg" fill="#34d399" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p className="mt-2 text-sm text-slate-500">No weekly data yet.</p>
        )}
      </div>

      {/* module progress — single source of truth: GET /api/progress */}
      <div className="rounded-3xl border border-slate-100 bg-white p-6 shadow-soft">
        <p className="text-sm font-bold text-slate-700">Module progress</p>
        <p className="mt-0.5 text-xs text-slate-400">Calculated from your stored activity — the same numbers the Placement page uses.</p>
        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {MODULE_ROWS.map(([key, label]) => {
            const value = progress?.modules?.[key] ?? 0;
            return (
              <div key={key}>
                <div className="flex justify-between text-xs font-semibold">
                  <span className="text-slate-600">{label}</span>
                  <span className="text-slate-800">{value}%</span>
                </div>
                <ProgressBar
                  value={value}
                  size="sm"
                  tone={value >= 70 ? "emerald" : value >= 50 ? "brand" : "rose"}
                />
                {value === 0 && <p className="mt-1 text-[11px] text-slate-400">No activity yet</p>}
              </div>
            );
          })}
        </div>
      </div>

      {/* strong / weak */}
      <div className="grid gap-4 md:grid-cols-2">
        <TopicList
          title="Strong areas"
          tone="emerald"
          items={data.strong_topics}
          emptyText="Nothing above 70% yet — your strengths will show up as you practise."
        />
        <TopicList
          title="Needs improvement"
          tone="amber"
          items={data.weak_topics}
          emptyText="No weak spots detected — keep the streak going!"
        />
      </div>

      {/* prep progress */}
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-3xl border border-slate-100 bg-white p-5 shadow-soft">
          <p className="text-sm font-bold text-slate-700">Roadmap progress</p>
          <p className="mt-1 text-2xl font-extrabold text-brand-700">{data.roadmap_progress}%</p>
          <ProgressBar value={data.roadmap_progress} className="mt-2" />
          <p className="mt-2 text-xs text-slate-400">{data.planner_completed} planner tasks completed</p>
        </div>
        <div className="rounded-3xl border border-slate-100 bg-white p-5 shadow-soft">
          <p className="flex items-center gap-2 text-sm font-bold text-slate-700"><CalendarDays size={15} /> Practice summary</p>
          {data.attempts || data.questions_answered || data.speech_attempts ? (
            <>
              <p className="mt-2 text-sm text-slate-600">
                {data.attempts} interviews · {data.questions_answered} answers · {data.speech_attempts} speech attempts
              </p>
              <p className="mt-1 text-xs text-slate-400">Data updates instantly after every practice activity.</p>
            </>
          ) : (
            <p className="mt-2 text-sm text-slate-400">No practice activity yet</p>
          )}
        </div>
      </div>
    </div>
  );
}
