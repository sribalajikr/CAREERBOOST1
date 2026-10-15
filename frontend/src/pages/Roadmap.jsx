import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  AlertTriangle, ArrowDown, BarChart3, BookOpen, Brain, CheckCircle2, Clock, Cloud,
  Code2, Cpu, Database, ExternalLink, FlaskConical, FolderGit2, GitBranch,
  GraduationCap, Library, Lightbulb, Loader2, Lock, Mic2, Rocket, RotateCcw,
  Server, ShieldCheck, Terminal, Wrench, X,
} from "lucide-react";
import { api, getErrorMessage } from "../services/api.js";
import { useToast } from "../context/ToastContext.jsx";
import { ErrorState, LoadingSpinner, SectionHeader } from "../components/ui.jsx";

const RESOURCE_ICON = { video: "🎬", doc: "📄", course: "🎓", practice: "🧪" };

const LEVEL_ICONS = {
  foundation: BookOpen, code: Code2, collections: Library, warning: AlertTriangle,
  threads: Cpu, devops: GitBranch, api: Server, database: Database, career: Rocket,
  interview: Mic2, project: FolderGit2, practice: Terminal, testing: FlaskConical,
  data: BarChart3, ai: Brain, cloud: Cloud, security: ShieldCheck,
};

const STATES = {
  completed: { label: "✓ COMPLETED", pill: "bg-emerald-400/15 text-emerald-300 border border-emerald-400/30" },
  current: { label: "▶ CURRENT LEVEL", pill: "bg-yellow-300 text-slate-950 font-black" },
  unlocked: { label: "→ NEXT LEVEL", pill: "bg-amber-200/15 text-amber-200 border border-amber-200/40" },
  locked: { label: "🔒 LOCKED", pill: "bg-white/10 text-slate-300 border border-white/15" },
};

const fmtEst = (m) => (m >= 60 ? `~${Math.round(m / 60)}h` : `~${m}m`);

function LevelIcon({ name }) {
  const Ico = LEVEL_ICONS[name] || BookOpen;
  return <Ico size={16} />;
}

/* ---------------------------------------------------------------- level card */
function LevelCard({ level, onOpen }) {
  const st = STATES[level.state] || STATES.locked;
  const locked = level.state === "locked";
  const bright = level.index % 2 === 0;

  const circle = locked
    ? "bg-white/10 text-slate-300 ring-1 ring-white/20"
    : bright
      ? "bg-gradient-to-br from-yellow-300 to-amber-400 text-slate-950 shadow-[0_0_18px_rgba(250,204,21,0.35)]"
      : "bg-gradient-to-br from-[#9a7b45] to-[#7a5f33] text-amber-50 ring-1 ring-amber-200/20";

  const frame =
    level.state === "current"
      ? "border-yellow-300/70 bg-yellow-300/[0.08] ring-2 ring-yellow-300/40 shadow-[0_0_30px_rgba(250,204,21,0.22)]"
      : level.state === "completed"
        ? "border-emerald-400/30 bg-emerald-400/[0.06] hover:bg-emerald-400/[0.1]"
        : level.state === "unlocked"
          ? "border-amber-200/40 bg-white/[0.06] hover:bg-white/[0.1]"
          : "border-white/10 bg-white/[0.03] opacity-75";

  const badge =
    level.state === "completed" ? "bg-emerald-400 text-slate-950"
      : level.state === "current" ? "bg-yellow-300 text-slate-950"
        : level.state === "unlocked" ? "bg-amber-200 text-slate-950"
          : "bg-white/15 text-slate-300";

  return (
    <button
      onClick={() => onOpen(level.index)}
      className={`group w-full rounded-3xl border p-5 text-left transition-all duration-200 hover:-translate-y-0.5 ${frame}`}
      aria-label={`Level ${level.number}: ${level.title} (${level.state})`}
    >
      <div className="flex items-start gap-4">
        {/* big circular node with two-digit number */}
        <div className="relative shrink-0">
          <div className={`flex h-20 w-20 flex-col items-center justify-center rounded-full ${circle} transition group-hover:scale-105`}>
            <LevelIcon name={level.icon} />
            <span className="mt-0.5 text-2xl font-black leading-none tracking-tight">{level.number}</span>
          </div>
          <span className={`absolute -bottom-1 -right-1 flex h-7 w-7 items-center justify-center rounded-full text-sm font-black ring-2 ring-[#141043] ${badge}`}>
            {level.state === "completed" ? "✓" : level.state === "current" ? "▶" : level.state === "unlocked" ? "→" : "🔒"}
          </span>
        </div>

        {/* info */}
        <div className="min-w-0 flex-1">
          <span className={`inline-block rounded-full px-2.5 py-1 text-[10px] font-black tracking-wider ${st.pill}`}>
            {st.label}
          </span>
          <p className="mt-2 truncate text-base font-bold text-white">{level.title}</p>
          <p className="mt-0.5 line-clamp-2 text-xs leading-snug text-indigo-200/70">{level.description}</p>

          <div className="mt-2.5 flex items-center gap-3 text-[11px] font-semibold text-amber-200/80">
            <span className="flex items-center gap-1"><Clock size={12} /> {fmtEst(level.est_minutes)}</span>
            <span>{level.completed_tasks}/{level.total_tasks} tasks</span>
          </div>

          <div className="mt-2 flex items-center gap-2">
            <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/10">
              <div
                className={`h-full rounded-full transition-all duration-500 ${level.progress === 100 ? "bg-emerald-400" : "bg-gradient-to-r from-yellow-300 to-amber-400"}`}
                style={{ width: `${level.progress}%` }}
              />
            </div>
            <span className="text-[11px] font-black text-white">{level.progress}%</span>
          </div>

          <div className="mt-2 flex flex-wrap gap-1">
            {level.topics.slice(0, 2).map((t) => (
              <span key={t} className="rounded-md bg-white/10 px-1.5 py-0.5 text-[10px] font-medium text-amber-100/80">{t}</span>
            ))}
            {level.topics.length > 2 && (
              <span className="rounded-md bg-white/5 px-1.5 py-0.5 text-[10px] font-medium text-amber-100/60">+{level.topics.length - 2}</span>
            )}
          </div>
        </div>
      </div>
    </button>
  );
}

/* ------------------------------------------------- connectors between levels */
function RowConnector() {
  return (
    <div className="relative" aria-hidden="true">
      {/* mobile / tablet: straight vertical link */}
      <div className="flex justify-center py-1 lg:hidden">
        <ArrowDown size={18} className="text-yellow-300/70" />
      </div>
      {/* desktop: thin golden curve with arrowhead, row-end -> next row start */}
      <div className="hidden py-2 lg:block">
        <svg viewBox="0 0 1000 56" className="h-12 w-full" fill="none" preserveAspectRatio="none">
          <path
            d="M 840 0 C 900 34, 100 22, 96 50"
            stroke="#facc15" strokeOpacity="0.55" strokeWidth="1.5"
            vectorEffect="non-scaling-stroke" strokeLinecap="round"
          />
          <path d="M 88 40 L 96 52 L 106 42" stroke="#facc15" strokeOpacity="0.8"
            strokeWidth="1.5" vectorEffect="non-scaling-stroke" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
    </div>
  );
}

function InlineArrow({ show }) {
  if (!show) return null;
  return (
    <div className="flex justify-center py-0.5 lg:hidden" aria-hidden="true">
      <ArrowDown size={14} className="text-yellow-300/60" />
    </div>
  );
}

/* -------------------------------------------------------------------- page */
export default function Roadmap() {
  const [params] = useSearchParams();
  const toast = useToast();
  const [career, setCareer] = useState(params.get("career") || "");
  const [careers, setCareers] = useState([]);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [active, setActive] = useState(null); // open level index (modal)
  const [toggling, setToggling] = useState(null);

  useEffect(() => {
    api.roadmapCareers().then(setCareers).catch(() => {});
  }, []);

  const load = useCallback(async () => {
    if (!career) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError("");
    try {
      setData(await api.roadmapLevels(career));
    } catch (e) {
      setError(getErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }, [career]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && setActive(null);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const toggleTask = async (taskId) => {
    if (!data || toggling) return;
    const before = data.levels.find((l) => l.index === active);
    setToggling(taskId);
    try {
      await api.toggleRoadmapTask(career, taskId);
      const fresh = await api.roadmapLevels(career);
      setData(fresh);
      const after = fresh.levels.find((l) => l.index === active);
      if (before && after && before.progress < 100 && after.progress === 100) {
        if (fresh.current_level != null) {
          toast.success(`Level ${after.number} complete — Level ${fresh.levels[fresh.current_level].number} unlocked! 🎉`);
        } else {
          toast.success(`Level ${after.number} complete — you finished the whole path! 🏆`);
        }
      }
    } catch (e) {
      toast.error(getErrorMessage(e));
    } finally {
      setToggling(null);
    }
  };

  const reset = async () => {
    if (!window.confirm("Reset all progress for this roadmap? This can't be undone.")) return;
    try {
      await api.resetRoadmap(career);
      await load();
      toast.info("Roadmap progress reset.");
    } catch (e) {
      toast.error(getErrorMessage(e));
    }
  };

  const selectCareer = (c) => {
    setCareer(c);
    setData(null);
    setError("");
    setActive(null);
    setLoading(true);
  };

  /* ---------- career picker ---------- */
  if (!career) {
    return (
      <div className="space-y-6">
        <SectionHeader title="Planner" subtitle="Pick a career to start your game-style level progression." />
        {careers.length ? (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
            {careers.map((c) => (
              <button key={c} onClick={() => selectCareer(c)}
                className="card flex flex-col items-center gap-2 p-5 text-center transition-all hover:shadow-lift hover:-translate-y-0.5">
                <span className="rounded-2xl bg-brand-50 p-3 text-brand-600"><GraduationCap size={22} /></span>
                <p className="text-sm font-bold text-slate-700">{c}</p>
              </button>
            ))}
          </div>
        ) : (
          <LoadingSpinner label="Loading careers…" />
        )}
      </div>
    );
  }

  if (loading) return <div className="py-20"><LoadingSpinner size={36} label={`Loading your ${career} levels…`} /></div>;
  if (error) return <ErrorState message={error} onRetry={() => selectCareer(career)} />;
  if (!data) return <div className="py-20"><LoadingSpinner size={36} label={`Loading your ${career} levels…`} /></div>;

  const openLevel = data.levels.find((l) => l.index === active) || null;
  const rows = [];
  for (let i = 0; i < data.levels.length; i += 3) rows.push(data.levels.slice(i, i + 3));

  return (
    <div className="space-y-6">
      <SectionHeader
        title={`${career} Planner`}
        subtitle={`Level up through ${data.levels.length} career stages · finish a level to unlock the next`}
        right={
          <div className="flex items-center gap-2">
            <select className="input w-auto py-2" value={career} onChange={(e) => selectCareer(e.target.value)}>
              {careers.map((c) => <option key={c}>{c}</option>)}
            </select>
            <button className="btn-secondary" onClick={reset} title="Reset progress">
              <RotateCcw size={15} />
            </button>
          </div>
        }
      />

      {/* ============================ game map ============================ */}
      <div className="relative overflow-hidden rounded-3xl border border-yellow-300/15 bg-gradient-to-br from-[#0b1237] via-[#1c1550] to-[#35104f] p-5 shadow-lift sm:p-7">
        <div className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-yellow-300/10 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-28 -left-16 h-80 w-80 rounded-full bg-purple-500/10 blur-3xl" />

        {/* header: readiness + legend */}
        <div className="relative flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-black uppercase tracking-[0.2em] text-yellow-300/90">Career readiness</p>
            <div className="mt-1 flex items-end gap-3">
              <p className="text-5xl font-black leading-none text-yellow-300">{data.overall_progress}%</p>
              <p className="pb-1 text-xs font-semibold text-indigo-200/70">
                {data.completed_tasks}/{data.total_tasks} tasks · {data.completed_levels}/{data.levels.length} levels complete
                {data.estimated_weeks ? ` · ~${data.estimated_weeks} weeks` : ""}
              </p>
            </div>
            <div className="mt-3 h-2.5 w-full max-w-md overflow-hidden rounded-full bg-white/10">
              <div
                className="h-full rounded-full bg-gradient-to-r from-yellow-300 to-amber-400 transition-all duration-700"
                style={{ width: `${data.overall_progress}%` }}
              />
            </div>
          </div>

          {/* legend */}
          <div className="flex flex-wrap gap-2 text-[10px] font-black tracking-wider">
            <span className="rounded-full border border-emerald-400/30 bg-emerald-400/15 px-3 py-1.5 text-emerald-300">✓ COMPLETED</span>
            <span className="rounded-full bg-yellow-300 px-3 py-1.5 text-slate-950">▶ CURRENT LEVEL</span>
            <span className="rounded-full border border-amber-200/40 bg-amber-200/15 px-3 py-1.5 text-amber-200">→ NEXT LEVEL</span>
            <span className="rounded-full border border-white/15 bg-white/10 px-3 py-1.5 text-slate-300">🔒 LOCKED</span>
          </div>
        </div>

        {/* the winding path */}
        <div className="relative mt-7 space-y-1">
          {rows.map((row, ri) => (
            <div key={ri}>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {row.map((lvl, ci) => (
                  <div key={lvl.index} className="relative">
                    <LevelCard level={lvl} onOpen={setActive} />
                    {/* thin golden line joining cards across a desktop row */}
                    {ci < row.length - 1 && (
                      <span className="absolute right-[-17px] top-[58px] hidden h-px w-4 bg-yellow-300/50 lg:block" aria-hidden="true" />
                    )}
                    <InlineArrow show={ci < row.length - 1} />
                  </div>
                ))}
              </div>
              {ri < rows.length - 1 && <RowConnector />}
            </div>
          ))}
        </div>

        {data.overall_progress === 100 && (
          <div className="relative mt-6 rounded-3xl border border-yellow-300/30 bg-yellow-300/10 p-6 text-center">
            <Rocket size={26} className="mx-auto text-yellow-300" />
            <h3 className="mt-2 text-lg font-extrabold text-white">All levels complete — career ready! 🏆</h3>
            <p className="mt-1 text-sm text-indigo-200/70">Keep the momentum: practice interviews and start applying.</p>
            <div className="mt-4 flex justify-center gap-2">
              <Link to="/mock-interview" className="rounded-xl bg-yellow-300 px-5 py-2.5 text-sm font-black text-slate-950 transition hover:bg-yellow-200">Practice an interview</Link>
              <Link to="/careers" className="rounded-xl border border-white/20 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-white/10">Explore more careers</Link>
            </div>
          </div>
        )}
      </div>

      {/* ============================ level modal ============================ */}
      {openLevel && (
        <div
          className="fixed inset-0 z-50 overflow-y-auto bg-black/70 p-4 backdrop-blur-sm"
          onClick={(e) => e.target === e.currentTarget && setActive(null)}
        >
          <div className="mx-auto my-6 w-full max-w-2xl animate-fade-up rounded-3xl border border-yellow-300/25 bg-gradient-to-br from-[#101640] via-[#1c1550] to-[#31104e] p-6 text-white shadow-2xl sm:p-8">
            {/* modal header */}
            <div className="flex items-start gap-4">
              <div className={`flex h-16 w-16 shrink-0 flex-col items-center justify-center rounded-full ${
                openLevel.state === "locked"
                  ? "bg-white/10 text-slate-300 ring-1 ring-white/20"
                  : openLevel.index % 2 === 0
                    ? "bg-gradient-to-br from-yellow-300 to-amber-400 text-slate-950"
                    : "bg-gradient-to-br from-[#9a7b45] to-[#7a5f33] text-amber-50 ring-1 ring-amber-200/20"
              }`}>
                <LevelIcon name={openLevel.icon} />
                <span className="mt-0.5 text-xl font-black leading-none">{openLevel.number}</span>
              </div>
              <div className="min-w-0 flex-1">
                <span className={`inline-block rounded-full px-2.5 py-1 text-[10px] font-black tracking-wider ${STATES[openLevel.state].pill}`}>
                  {STATES[openLevel.state].label}
                </span>
                <h2 className="mt-2 text-xl font-extrabold leading-tight">{openLevel.title}</h2>
                <p className="mt-1 text-xs font-semibold text-amber-200/80">
                  <Clock size={12} className="mr-1 inline" />{fmtEst(openLevel.est_minutes)} · {openLevel.completed_tasks}/{openLevel.total_tasks} tasks
                </p>
              </div>
              <button
                onClick={() => setActive(null)}
                className="rounded-xl bg-white/10 p-2 text-slate-300 transition hover:bg-white/20 hover:text-white"
                aria-label="Close level"
              >
                <X size={18} />
              </button>
            </div>

            {/* progress */}
            <div className="mt-4 flex items-center gap-3">
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-white/10">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${openLevel.progress === 100 ? "bg-emerald-400" : "bg-gradient-to-r from-yellow-300 to-amber-400"}`}
                  style={{ width: `${openLevel.progress}%` }}
                />
              </div>
              <span className="text-sm font-black">{openLevel.progress}%</span>
            </div>

            {/* locked notice */}
            {openLevel.state === "locked" && (
              <div className="mt-4 flex items-center gap-2 rounded-xl border border-white/15 bg-white/5 px-4 py-3 text-xs font-semibold text-slate-300">
                <Lock size={14} className="shrink-0 text-slate-400" />
                Complete Level {String(openLevel.index).padStart(2, "0")} ({data.levels[openLevel.index - 1]?.title}) to unlock this level.
              </div>
            )}

            {/* description / note */}
            <p className="mt-4 text-sm leading-relaxed text-indigo-100/85">{openLevel.description}</p>
            {openLevel.note && (
              <div className="mt-3 rounded-xl border-l-2 border-yellow-300/70 bg-white/5 px-4 py-3">
                <p className="flex items-center gap-1.5 text-xs font-bold text-yellow-300"><Lightbulb size={13} /> In plain words</p>
                <p className="mt-1 text-sm leading-relaxed text-indigo-100/80">{openLevel.note}</p>
              </div>
            )}

            {/* topics */}
            <p className="mb-2 mt-5 text-xs font-black uppercase tracking-wider text-amber-200/70">Skills & topics covered</p>
            <div className="flex flex-wrap gap-1.5">
              {openLevel.topics.map((t) => (
                <span key={t} className="rounded-full bg-white/10 px-3 py-1 text-xs font-semibold text-amber-100">{t}</span>
              ))}
            </div>

            {/* tasks */}
            <p className="mb-2 mt-5 text-xs font-black uppercase tracking-wider text-amber-200/70">
              Tasks to complete {openLevel.state === "locked" && "· locked"}
            </p>
            <ul className="space-y-1.5">
              {openLevel.tasks.map((t) => (
                <li key={t.id}>
                  <button
                    onClick={() => toggleTask(t.id)}
                    disabled={openLevel.state === "locked" || toggling === t.id}
                    className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm transition-all disabled:cursor-not-allowed disabled:opacity-60 ${
                      t.done ? "bg-emerald-400/10 text-emerald-200" : "bg-white/5 text-indigo-100 hover:bg-white/10"
                    }`}
                  >
                    {t.done
                      ? <CheckCircle2 size={17} className="shrink-0 text-emerald-400" />
                      : <span className="h-[17px] w-[17px] shrink-0 rounded-full border-2 border-white/30" />}
                    <span className={t.done ? "line-through decoration-emerald-400/60" : ""}>{t.title}</span>
                    {toggling === t.id && <Loader2 size={14} className="ml-auto animate-spin text-yellow-300" />}
                  </button>
                </li>
              ))}
            </ul>

            {/* practice + mini project (phase levels) */}
            {openLevel.practice?.length > 0 && (
              <div className="mt-5">
                <p className="mb-1.5 flex items-center gap-1 text-xs font-black uppercase tracking-wider text-amber-200/70">
                  <Wrench size={12} /> Practice
                </p>
                <ul className="space-y-1 text-xs leading-relaxed text-indigo-100/75">
                  {openLevel.practice.map((p, i) => <li key={i}>• {p}</li>)}
                </ul>
              </div>
            )}
            {openLevel.mini_project && (
              <div className="mt-4 rounded-xl border border-amber-300/25 bg-amber-300/10 px-4 py-3">
                <p className="flex items-center gap-1.5 text-xs font-bold text-amber-200"><Lightbulb size={13} /> Mini project</p>
                <p className="mt-1 text-xs leading-relaxed text-indigo-100/80">{openLevel.mini_project}</p>
              </div>
            )}

            {/* resources */}
            {openLevel.resources?.length > 0 && (
              <div className="mt-5">
                <p className="mb-2 text-xs font-black uppercase tracking-wider text-amber-200/70">Free learning resources</p>
                <ul className="space-y-1.5">
                  {openLevel.resources.map((r, i) => (
                    <li key={i} className="rounded-xl bg-white/5 px-3 py-2 transition hover:bg-white/10">
                      {r.url ? (
                        <a href={r.url} target="_blank" rel="noopener noreferrer" className="block" title={r.url}>
                          <span className="flex items-center gap-2 text-xs font-semibold text-amber-100 transition hover:text-yellow-300">
                            <span>{RESOURCE_ICON[r.type] || "🔗"}</span>
                            <span className="min-w-0 flex-1 truncate">{r.name || r.title}</span>
                            <ExternalLink size={12} className="shrink-0 text-amber-200/60" />
                          </span>
                          <span className="mt-0.5 block truncate text-[11px] font-medium text-amber-300/70">{r.url}</span>
                        </a>
                      ) : (
                        <span className="flex items-center gap-2 text-xs font-semibold text-amber-100/90">
                          <span>{RESOURCE_ICON[r.type] || "🔗"}</span>
                          <span className="min-w-0 flex-1 truncate">{r.name || r.title}</span>
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* footer state line */}
            <div className="mt-6 flex items-center justify-between rounded-xl bg-white/5 px-4 py-3">
              {openLevel.state === "completed" ? (
                <p className="text-xs font-black text-emerald-300">✓ Level complete</p>
              ) : openLevel.state === "locked" ? (
                <p className="text-xs font-black text-slate-300">🔒 Locked — finish the previous level first</p>
              ) : (
                <p className="text-xs font-black text-yellow-300">
                  {openLevel.state === "current" ? "▶ This is your active level" : "→ Available to start"}
                </p>
              )}
              <span className="text-[11px] font-semibold text-indigo-200/60">Progress saves to your account</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
