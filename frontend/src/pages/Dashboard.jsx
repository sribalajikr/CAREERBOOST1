import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight, BookOpenCheck, Compass, FileText, Target, TrendingUp,
} from "lucide-react";
import {
  Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip as ReTooltip, XAxis, YAxis,
} from "recharts";
import { api, getErrorMessage } from "../services/api.js";
import { ErrorState, LoadingSpinner, ProgressBar, SectionHeader } from "../components/ui.jsx";

const QUICK_ACTIONS = [
  { to: "/resume", label: "Analyze Resume", icon: FileText, desc: "Get your resume score" },
  { to: "/careers", label: "Explore Careers", icon: Compass, desc: "Find your best fit" },
  { to: "/roadmap", label: "Open Planner", icon: BookOpenCheck, desc: "Your step-by-step path" },
  { to: "/interview-prep", label: "Interview Prep", icon: Target, desc: "Practice questions daily" },
];

const SKILL_COLORS = ["#4f46e5", "#6366f1", "#818cf8", "#a5b4fc", "#c7d2fe"];

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = () => {
    setLoading(true);
    setError("");
    api.dashboard()
      .then(setData)
      .catch((e) => setError(getErrorMessage(e)))
      .finally(() => setLoading(false));
  };
  useEffect(load, []);

  if (loading) return <div className="py-20"><LoadingSpinner size={36} label="Preparing your dashboard…" /></div>;
  if (error) return <ErrorState message={error} onRetry={load} />;

  const firstName = (data.name || "Student").split(" ")[0];
  const stats = [
    { label: "Resume Score", value: data.resume_score != null ? `${data.resume_score}` : "—", accent: "brand", to: "/resume", icon: FileText, sub: data.resume_file || "No resume analyzed yet" },
    { label: "Career Match", value: data.career_match != null ? `${data.career_match}` : "—", accent: "emerald", to: "/careers", icon: Compass, sub: data.recommended_career || "Explore careers" },
    { label: "Roadmap Progress", value: data.roadmap_progress != null ? `${data.roadmap_progress}` : "—", accent: "sky", to: "/roadmap", icon: BookOpenCheck, sub: data.roadmap_career ? `${data.roadmap_completed}/${data.roadmap_total} tasks` : "Pick a career first" },
  ];

  const skillData = (data.upcoming || []).slice(0, 5).map((t, i) => ({
    name: t.title.length > 22 ? t.title.slice(0, 20) + "…" : t.title,
    minutes: t.duration_minutes,
    fill: SKILL_COLORS[i % SKILL_COLORS.length],
  }));

  return (
    <div className="space-y-6">
      {/* Greeting banner */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-brand-700 via-brand-600 to-brand-800 p-6 text-white sm:p-8">
        <div className="pointer-events-none absolute -right-16 -top-16 h-56 w-56 rounded-full bg-white/10 blur-2xl" />
        <div className="pointer-events-none absolute -bottom-20 right-32 h-44 w-44 rounded-full bg-brand-400/20 blur-2xl" />
        <div className="relative flex flex-wrap items-center justify-between gap-4">
          <div className="max-w-xl">
            <h1 className="text-2xl font-extrabold sm:text-3xl">Welcome back, {firstName}! 👋</h1>
            <p className="mt-2 text-sm leading-relaxed text-brand-100 sm:text-base">{data.message}</p>
          </div>
          {data.roadmap_progress != null && (
            <div className="rounded-2xl bg-white/10 p-4 backdrop-blur">
              <p className="text-xs font-semibold text-brand-100">{data.roadmap_career} readiness</p>
              <p className="mt-1 text-3xl font-extrabold">{data.roadmap_progress}%</p>
              <div className="mt-2 w-36"><ProgressBar value={data.roadmap_progress} tone="emerald" size="sm" /></div>
            </div>
          )}
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
        {stats.map((s) => (
          <Link key={s.label} to={s.to} className="card group p-5 transition-all duration-200 hover:shadow-lift hover:-translate-y-0.5">
            <div className="flex items-center justify-between">
              <s.icon size={20} className="text-brand-500" />
              <ArrowRight size={15} className="text-slate-300 transition group-hover:translate-x-0.5 group-hover:text-brand-500" />
            </div>
            <p className="mt-3 text-2xl font-extrabold text-slate-800">
              {s.value}{s.value !== "—" && <span className="text-base text-slate-400">%</span>}
            </p>
            <p className="text-xs font-semibold text-slate-500">{s.label}</p>
            <p className="mt-1 truncate text-[11px] text-slate-400">{s.sub}</p>
          </Link>
        ))}
      </div>

      {/* Quick actions */}
      <div>
        <SectionHeader title="Quick Actions" subtitle="Jump straight to your next step." />
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {QUICK_ACTIONS.map(({ to, label, icon: Icon, desc }) => (
            <Link key={to} to={to} className="card group flex flex-col items-center p-5 text-center transition-all hover:shadow-lift hover:-translate-y-0.5">
              <span className="rounded-2xl bg-brand-50 p-3 text-brand-600 transition group-hover:bg-brand-600 group-hover:text-white">
                <Icon size={22} />
              </span>
              <p className="mt-3 text-sm font-bold text-slate-800">{label}</p>
              <p className="mt-0.5 text-xs text-slate-400">{desc}</p>
            </Link>
          ))}
        </div>
      </div>

      {/* Bottom grid: continue + recommended career */}
      <div className="grid gap-5 lg:grid-cols-2">
        {/* Continue where you left off */}
        <div className="card p-6">
          <h3 className="section-title flex items-center gap-2"><TrendingUp size={18} className="text-brand-500" /> Continue Where You Left Off</h3>
          {data.roadmap_career ? (
            <>
              <p className="mt-2 text-sm text-slate-500">{data.roadmap_career} roadmap</p>
              <div className="mt-3"><ProgressBar value={data.roadmap_progress || 0} size="lg" /></div>
              <p className="mt-2 text-xs font-semibold text-slate-400">{data.roadmap_completed} / {data.roadmap_total} tasks completed</p>
              <Link to="/roadmap" className="btn-primary mt-4 w-full">Continue Learning</Link>
            </>
          ) : (
            <div className="mt-3">
              <p className="text-sm text-slate-500">You haven't started a roadmap yet.</p>
              <Link to="/careers" className="btn-secondary mt-3 w-full">Choose a career to begin</Link>
            </div>
          )}
        </div>

        {/* Recommended career */}
        <div className="card p-6">
          <h3 className="section-title flex items-center gap-2"><Target size={18} className="text-brand-500" /> Recommended Career</h3>
          {data.recommended_career ? (
            <>
              <p className="mt-3 text-lg font-extrabold text-brand-700">{data.recommended_career}</p>
              <p className="text-sm text-slate-500">Best match for your skills & interests.</p>
              {data.career_match != null && (
                <div className="mt-3">
                  <div className="flex items-center justify-between text-xs font-semibold text-slate-500">
                    <span>Match score</span><span>{data.career_match}%</span>
                  </div>
                  <div className="mt-1"><ProgressBar value={data.career_match} tone="emerald" /></div>
                </div>
              )}
              {data.resume_score != null && (
                <p className="mt-4 rounded-xl bg-brand-50 px-3 py-2 text-xs font-medium text-brand-700">
                  Recent resume: {data.resume_file} scored {data.resume_score}/100
                </p>
              )}
              <Link to="/careers" className="btn-secondary mt-4 w-full">Explore Career</Link>
            </>
          ) : skillData.length ? (
            <div className="mt-2 h-44">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={skillData} layout="vertical" margin={{ left: 0, right: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f1f5f9" />
                  <XAxis type="number" hide />
                  <YAxis type="category" dataKey="name" width={120} tick={{ fontSize: 10, fill: "#64748b" }} axisLine={false} tickLine={false} />
                  <ReTooltip wrapperClassName="rounded-lg shadow-lift" contentStyle={{ fontSize: 12 }} />
                  <Bar dataKey="minutes" radius={[0, 6, 6, 0]} barSize={14}>
                    {skillData.map((d) => <Cell key={d.name} fill={d.fill} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
              <p className="text-center text-[11px] text-slate-400">Planned study minutes per task</p>
            </div>
          ) : (
            <p className="mt-3 text-sm text-slate-500">Add skills in your profile to see recommendations.</p>
          )}
        </div>
      </div>
    </div>
  );
}
