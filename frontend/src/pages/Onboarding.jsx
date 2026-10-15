import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, ArrowRight, Check, Loader2, Sparkles } from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import { api, getErrorMessage } from "../services/api.js";
import { ProgressBar } from "../components/ui.jsx";
import { cgpaIsValid, cgpaKeyAllowed, DEGREE_OPTIONS } from "../validation.js";

const STEPS = ["Personal", "Education", "Skills", "Career Goal"];

const CAREER_OPTIONS = [
  "Software Developer", "Full Stack Developer", "Backend Developer", "Frontend Developer",
  "Data Analyst", "Data Scientist", "AI/ML Engineer", "Cloud Engineer",
  "Cybersecurity Analyst", "DevOps Engineer", "QA / Automation Engineer",
];

const SKILL_SUGGESTIONS = [
  "Python", "Java", "C", "C++", "JavaScript", "SQL", "HTML", "CSS", "React", "Git",
  "Data Structures", "OOP", "Machine Learning", "Excel", "Communication",
];

export default function Onboarding() {
  const { user, refresh } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const [form, setForm] = useState({
    name: user?.name || "",
    phone: "",
    college: "",
    degree: "B.Tech",
    customDegree: "",
    department: "",
    year_of_study: "",
    cgpa: "",
    skills: [],
    preferred_career: "",
    experience_level: "Beginner",
    daily_study_minutes: 60,
  });

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const isOtherDegree = form.degree === "Other";

  // The final degree value: the typed custom name when "Other" is selected.
  const finalDegree = () => (isOtherDegree ? form.customDegree.trim() : form.degree);

  const toggleSkill = (s) =>
    setForm((f) => ({
      ...f,
      skills: f.skills.includes(s) ? f.skills.filter((x) => x !== s) : [...f.skills, s],
    }));

  const stepValid = () => {
    if (step === 0) return form.name.trim().length > 0;
    if (step === 1) {
      if (form.college.trim().length === 0 || form.department.trim().length === 0) return false;
      if (!cgpaIsValid(form.cgpa)) return false;
      if (isOtherDegree && form.customDegree.trim().length === 0) return false;
      return true;
    }
    if (step === 2) return form.skills.length > 0;
    return form.preferred_career !== "";
  };

  const finish = async () => {
    if (!cgpaIsValid(form.cgpa)) {
      setError("CGPA must be between 0 and 10.");
      return;
    }
    if (isOtherDegree && form.customDegree.trim().length === 0) {
      setError("Please type your degree name.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const payload = {
        name: form.name.trim(),
        phone: form.phone || null,
        college: form.college.trim() || null,
        degree: finalDegree() || null,
        department: form.department.trim() || null,
        year_of_study: form.year_of_study || null,
        cgpa: form.cgpa === "" ? null : Number(form.cgpa),
        skills: form.skills,
        preferred_career: form.preferred_career || null,
        experience_level: form.experience_level,
        daily_study_minutes: Number(form.daily_study_minutes),
      };
      await api.updateMe(payload);
      await refresh();
      toast.success("Profile ready! Your dashboard is personalized now. 🎉");
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-10">
      <div className="w-full max-w-xl animate-fade-up">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 text-white shadow-lift">
            <Sparkles size={22} />
          </div>
          <h1 className="text-2xl font-extrabold text-slate-800">Let's personalize your journey</h1>
          <p className="mt-1 text-sm text-slate-500">4 quick steps — it takes about 2 minutes.</p>
        </div>

        {/* Step indicator */}
        <div className="card mb-5 p-5">
          <div className="mb-2 flex items-center justify-between">
            {STEPS.map((s, i) => (
              <div key={s} className="flex flex-1 items-center">
                <div className="flex flex-col items-center">
                  <div
                    className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold transition-all ${
                      i < step
                        ? "bg-emerald-500 text-white"
                        : i === step
                        ? "bg-brand-600 text-white ring-4 ring-brand-100"
                        : "bg-slate-100 text-slate-400"
                    }`}
                  >
                    {i < step ? <Check size={14} /> : i + 1}
                  </div>
                  <span className={`mt-1.5 hidden text-[11px] font-semibold sm:block ${i === step ? "text-brand-700" : "text-slate-400"}`}>
                    {s}
                  </span>
                </div>
                {i < STEPS.length - 1 && (
                  <div className={`mx-1 mb-4 h-0.5 flex-1 rounded ${i < step ? "bg-emerald-400" : "bg-slate-100"}`} />
                )}
              </div>
            ))}
          </div>
          <ProgressBar value={((step + 1) / STEPS.length) * 100} size="sm" />
        </div>

        <div className="card p-6 sm:p-8">
          {error ? (
            <div className="mb-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700">{error}</div>
          ) : null}

          {step === 0 && (
            <div className="space-y-4 animate-fade-in">
              <h2 className="text-lg font-bold text-slate-800">Tell us about yourself</h2>
              <div>
                <label className="label">Full name *</label>
                <input className="input" placeholder="Priya Sharma" value={form.name} onChange={(e) => set("name", e.target.value)} />
              </div>
              <div>
                <label className="label">Phone (optional)</label>
                <input className="input" placeholder="+91 98765 43210" value={form.phone} onChange={(e) => set("phone", e.target.value)} />
              </div>
            </div>
          )}

          {step === 1 && (
            <div className="space-y-4 animate-fade-in">
              <h2 className="text-lg font-bold text-slate-800">Your education</h2>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="label">College *</label>
                  <input className="input" placeholder="Sunrise Institute of Technology" value={form.college} onChange={(e) => set("college", e.target.value)} />
                </div>
                <div>
                  <label className="label">Degree</label>
                  <select className="input" value={form.degree} onChange={(e) => set("degree", e.target.value)}>
                    {DEGREE_OPTIONS.map((d) => <option key={d}>{d}</option>)}
                  </select>
                </div>
              </div>
              {isOtherDegree && (
                <div className="animate-fade-in">
                  <label className="label">Enter your degree *</label>
                  <input
                    className="input"
                    placeholder="B.Sc. Computer Science"
                    value={form.customDegree}
                    onChange={(e) => set("customDegree", e.target.value)}
                  />
                </div>
              )}
              <div className="grid gap-4 sm:grid-cols-3">
                <div>
                  <label className="label">Department *</label>
                  <input className="input" placeholder="Computer Science" value={form.department} onChange={(e) => set("department", e.target.value)} />
                </div>
                <div>
                  <label className="label">Year of study</label>
                  <select className="input" value={form.year_of_study} onChange={(e) => set("year_of_study", e.target.value)}>
                    <option value="">Select…</option>
                    {["1st Year", "2nd Year", "3rd Year", "4th Year", "Final Year", "Graduate"].map((y) => <option key={y}>{y}</option>)}
                  </select>
                </div>
                <div>
                  <label className="label">CGPA (0–10)</label>
                  <input
                    className="input"
                    type="text"
                    inputMode="decimal"
                    placeholder="8.5"
                    value={form.cgpa}
                    onKeyDown={(e) => { if (!cgpaKeyAllowed(e)) e.preventDefault(); }}
                    onChange={(e) => set("cgpa", e.target.value)}
                  />
                  {form.cgpa !== "" && !cgpaIsValid(form.cgpa) ? (
                    <p className="mt-1.5 text-xs font-medium text-rose-600">CGPA must be between 0 and 10.</p>
                  ) : null}
                </div>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4 animate-fade-in">
              <h2 className="text-lg font-bold text-slate-800">What skills do you have?</h2>
              <p className="text-sm text-slate-500">Pick everything you know, even a little. This powers your career matches.</p>
              <div className="flex flex-wrap gap-2">
                {SKILL_SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => toggleSkill(s)}
                    className={`chip border transition-all ${
                      form.skills.includes(s)
                        ? "border-brand-600 bg-brand-600 text-white shadow-lift"
                        : "border-slate-200 bg-white text-slate-600 hover:border-brand-300 hover:text-brand-700"
                    }`}
                  >
                    {form.skills.includes(s) && <Check size={12} />} {s}
                  </button>
                ))}
              </div>
              <div>
                <label className="label">More skills (comma separated)</label>
                <input
                  className="input"
                  placeholder="Node.js, MongoDB, Figma…"
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === ",") {
                      e.preventDefault();
                      const v = e.target.value.trim().replace(/,$/, "");
                      if (v && !form.skills.includes(v)) { toggleSkill(v); e.target.value = ""; }
                    }
                  }}
                />
              </div>
              {form.skills.length > 0 && (
                <p className="text-xs font-semibold text-emerald-600">✓ {form.skills.length} skill{form.skills.length > 1 ? "s" : ""} selected</p>
              )}
            </div>
          )}

          {step === 3 && (
            <div className="space-y-4 animate-fade-in">
              <h2 className="text-lg font-bold text-slate-800">Where do you want to go?</h2>
              <div>
                <label className="label">Dream career role *</label>
                <select className="input" value={form.preferred_career} onChange={(e) => set("preferred_career", e.target.value)}>
                  <option value="">Choose a role…</option>
                  {CAREER_OPTIONS.map((c) => <option key={c}>{c}</option>)}
                </select>
                <p className="mt-1.5 text-xs text-slate-400">You can change this anytime — this just sets your starting roadmap.</p>
              </div>
              <div>
                <label className="label">Experience level</label>
                <div className="grid grid-cols-3 gap-2">
                  {["Beginner", "Intermediate", "Advanced"].map((lvl) => (
                    <button
                      key={lvl}
                      type="button"
                      onClick={() => set("experience_level", lvl)}
                      className={`rounded-xl border px-3 py-2.5 text-sm font-semibold transition-all ${
                        form.experience_level === lvl
                          ? "border-brand-600 bg-brand-50 text-brand-700 ring-2 ring-brand-100"
                          : "border-slate-200 text-slate-500 hover:border-brand-300"
                      }`}
                    >
                      {lvl}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="label">How much time can you study per day?</label>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                  {[
                    { m: 30, l: "30 min" },
                    { m: 60, l: "1 hour" },
                    { m: 120, l: "2 hours" },
                    { m: 210, l: "3+ hours" },
                  ].map(({ m, l }) => (
                    <button
                      key={m}
                      type="button"
                      onClick={() => set("daily_study_minutes", m)}
                      className={`rounded-xl border px-3 py-2.5 text-sm font-semibold transition-all ${
                        Number(form.daily_study_minutes) === m
                          ? "border-brand-600 bg-brand-50 text-brand-700 ring-2 ring-brand-100"
                          : "border-slate-200 text-slate-500 hover:border-brand-300"
                      }`}
                    >
                      {l}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Footer buttons */}
          <div className="mt-8 flex items-center justify-between">
            <button className="btn-ghost" onClick={() => setStep((s) => Math.max(0, s - 1))} disabled={step === 0 || busy}>
              <ArrowLeft size={16} /> Back
            </button>
            {step < STEPS.length - 1 ? (
              <button className="btn-primary" onClick={() => setStep((s) => s + 1)} disabled={!stepValid()}>
                Continue <ArrowRight size={16} />
              </button>
            ) : (
              <button className="btn-primary" onClick={finish} disabled={!stepValid() || busy}>
                {busy ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
                {busy ? "Setting up…" : "Finish setup"}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
