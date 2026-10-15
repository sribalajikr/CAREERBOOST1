import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { CheckCircle2, CircleAlert, Compass, Loader2, RefreshCw } from "lucide-react";
import { api, getErrorMessage } from "../services/api.js";
import { EmptyState, ErrorState, LoadingSpinner, ProgressBar, SectionHeader, SkillPill, Tooltip } from "../components/ui.jsx";

const LEVEL_TONE = {
  Beginner: "bg-emerald-50 text-emerald-700 border-emerald-200",
  Intermediate: "bg-amber-50 text-amber-700 border-amber-200",
  Advanced: "bg-rose-50 text-rose-700 border-rose-200",
};

export default function Careers() {
  const navigate = useNavigate();
  const [recs, setRecs] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = () => {
    setLoading(true);
    setError("");
    api.careerRecommendations()
      .then((d) => setRecs(d.recommendations || []))
      .catch((e) => setError(getErrorMessage(e)))
      .finally(() => setLoading(false));
  };
  useEffect(load, []);

  if (loading) return <div className="py-20"><LoadingSpinner size={36} label="Matching careers to your profile…" /></div>;
  if (error) return <ErrorState message={error} onRetry={load} />;

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Your Career Matches"
        subtitle="Ranked by how well each role fits your skills, education and interests. There's no single 'right' answer — explore a few!"
        right={
          <button className="btn-secondary" onClick={load}>
            <RefreshCw size={15} /> Refresh matches
          </button>
        }
      />

      {!recs?.length ? (
        <EmptyState
          icon={Compass}
          title="Add a few skills first"
          description="Career matches are powered by your profile skills. Add them on the Profile page and come back."
          action={<button className="btn-primary" onClick={() => navigate("/profile")}>Go to profile</button>}
        />
      ) : (
        <div className="grid gap-5 lg:grid-cols-2">
          {recs.map((c, idx) => (
            <div
              key={c.career}
              className={`card flex flex-col p-6 transition-all hover:shadow-lift ${idx === 0 ? "ring-2 ring-brand-200" : ""}`}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-lg font-extrabold text-slate-800">{c.career}</h3>
                    {idx === 0 && <span className="chip bg-brand-600 text-white">Best match</span>}
                    <Tooltip text="How well your current profile fits this role">
                      <span className={`chip border ${LEVEL_TONE[c.level] || "bg-slate-50 text-slate-600 border-slate-200"}`}>{c.level}</span>
                    </Tooltip>
                  </div>
                  <p className="mt-1.5 text-sm leading-relaxed text-slate-500">{c.description}</p>
                </div>
                <div className="shrink-0 text-center">
                  <p className="text-3xl font-extrabold text-brand-600">{c.match_percent}%</p>
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">match</p>
                </div>
              </div>

              <div className="mt-4"><ProgressBar value={c.match_percent} tone={c.match_percent >= 70 ? "emerald" : "brand"} /></div>

              <div className="mt-4 space-y-2.5 text-sm">
                <p className="flex items-start gap-2">
                  <CheckCircle2 size={15} className="mt-0.5 shrink-0 text-emerald-500" />
                  <span className="text-slate-600"><span className="font-semibold text-slate-700">You already have:</span>{" "}
                    {c.user_skills?.length ? c.user_skills.slice(0, 8).join(", ") : "—"}
                  </span>
                </p>
                <p className="flex items-start gap-2">
                  <CircleAlert size={15} className="mt-0.5 shrink-0 text-amber-500" />
                  <span className="text-slate-600"><span className="font-semibold text-slate-700">You should improve:</span>{" "}
                    {c.missing_skills?.length ? c.missing_skills.slice(0, 8).join(", ") : "Nothing — you're covered! 🎉"}
                  </span>
                </p>
              </div>

              <div className="mt-4 flex flex-wrap gap-1.5">
                {c.required_skills?.slice(0, 8).map((s) => (
                  <SkillPill key={s} skill={s} tone={c.user_skills?.includes(s) ? "green" : "amber"} />
                ))}
              </div>

              {c.why?.length ? (
                <div className="mt-4 rounded-xl bg-brand-50/70 px-4 py-3">
                  <p className="text-xs font-bold uppercase tracking-wide text-brand-600">Why this fits you</p>
                  <ul className="mt-1.5 space-y-1">
                    {c.why.slice(0, 3).map((w, i) => (
                      <li key={i} className="text-xs leading-relaxed text-slate-600">• {w}</li>
                    ))}
                  </ul>
                </div>
              ) : null}

              <div className="mt-auto pt-5">
                <button className="btn-primary w-full" onClick={() => navigate(`/roadmap?career=${encodeURIComponent(c.career)}`)}>
                  Explore Career
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
