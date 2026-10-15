import { useEffect, useState } from "react";
import { Check, Loader2, Pencil, X } from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import { api, getErrorMessage } from "../services/api.js";
import { ProgressBar, SectionHeader, SkillPill } from "../components/ui.jsx";
import { cgpaIsValid, cgpaKeyAllowed, DEGREE_OPTIONS } from "../validation.js";

const CAREER_OPTIONS = [
  "Software Developer", "Full Stack Developer", "Backend Developer", "Frontend Developer",
  "Data Analyst", "Data Scientist", "AI/ML Engineer", "Cloud Engineer",
  "Cybersecurity Analyst", "DevOps Engineer", "QA / Automation Engineer",
];

export default function Profile() {
  const { user, refresh } = useAuth();
  const toast = useToast();
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [completion, setCompletion] = useState(null);
  const [form, setForm] = useState(null);

  useEffect(() => {
    if (!user) return;
    setForm({
      name: user.name || "",
      phone: user.profile?.phone || "",
      college: user.profile?.college || "",
      degree: user.profile?.degree || "",
      department: user.profile?.department || "",
      year_of_study: user.profile?.year_of_study || "",
      cgpa: user.profile?.cgpa ?? "",
      skills: user.profile?.skills || [],
      preferred_career: user.profile?.preferred_career || "",
      experience_level: user.profile?.experience_level || "Beginner",
    });
    api.completion().then(setCompletion).catch(() => {});
  }, [user]);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const isOtherDegree = form?.degree === "Other";
  const finalDegree = () => (isOtherDegree ? (form.customDegree || "").trim() : form.degree);

  const save = async () => {
    if (!cgpaIsValid(form.cgpa)) {
      setError("CGPA must be between 0 and 10.");
      return;
    }
    if (isOtherDegree && (form.customDegree || "").trim().length === 0) {
      setError("Please type your degree name.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await api.updateMe({
        name: form.name.trim() || null,
        phone: form.phone || null,
        college: form.college || null,
        degree: finalDegree() || null,
        department: form.department || null,
        year_of_study: form.year_of_study || null,
        cgpa: form.cgpa === "" ? null : Number(form.cgpa),
        skills: form.skills,
        preferred_career: form.preferred_career || null,
        experience_level: form.experience_level,
      });
      await refresh();
      setEditing(false);
      toast.success("Profile updated successfully ✨");
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  if (!user || !form) return null;

  const p = user.profile || {};
  const rows = [
    ["Email", user.email],
    ["Phone", p.phone || "—"],
    ["College", p.college || "—"],
    ["Degree", p.degree || "—"],
    ["Department", p.department || "—"],
    ["Year of Study", p.year_of_study || "—"],
    ["CGPA", p.cgpa != null ? String(p.cgpa) : "—"],
    ["Experience Level", p.experience_level || "—"],
  ];

  return (
    <div className="space-y-6">
      <SectionHeader
        title="My Profile"
        subtitle="Keep this up to date — better info means better career matches."
        right={
          !editing && (
            <button className="btn-primary" onClick={() => setEditing(true)}>
              <Pencil size={16} /> Edit Profile
            </button>
          )
        }
      />

      {/* Completion card */}
      <div className="card p-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-bold text-slate-800">Profile completion</h3>
            <p className="text-sm text-slate-500">
              {completion?.completion === 100
                ? "Perfect! Your matches will be as accurate as possible. 🎉"
                : completion?.next_missing_field
                ? `Next: add your ${completion.next_missing_field.replace(/_/g, " ")}.`
                : "Fill in more details for smarter recommendations."}
            </p>
          </div>
          <span className="text-3xl font-extrabold text-brand-600">{completion?.completion ?? 0}%</span>
        </div>
        <div className="mt-4">
          <ProgressBar value={completion?.completion ?? 0} size="lg" tone={(completion?.completion ?? 0) >= 80 ? "emerald" : "brand"} />
        </div>
      </div>

      {/* View mode */}
      {!editing ? (
        <div className="grid gap-5 lg:grid-cols-3">
          <div className="card p-6 lg:col-span-2">
            <h3 className="section-title mb-4">Personal & Education Details</h3>
            <dl className="grid gap-x-6 gap-y-4 sm:grid-cols-2">
              {rows.map(([k, v]) => (
                <div key={k}>
                  <dt className="text-xs font-semibold uppercase tracking-wide text-slate-400">{k}</dt>
                  <dd className="mt-0.5 text-sm font-medium text-slate-800">{v}</dd>
                </div>
              ))}
            </dl>
          </div>
          <div className="space-y-5">
            <div className="card p-6">
              <h3 className="section-title mb-3">Skills</h3>
              {p.skills?.length ? (
                <div className="flex flex-wrap gap-1.5">
                  {p.skills.map((s) => <SkillPill key={s} skill={s} tone="green" />)}
                </div>
              ) : (
                <p className="text-sm text-slate-400">No skills added yet.</p>
              )}
            </div>
            <div className="card p-6">
              <h3 className="section-title mb-3">Career Goal</h3>
              <p className="text-sm font-bold text-brand-700">{p.preferred_career || "Not set yet"}</p>
              {p.interests?.length ? (
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {p.interests.map((i) => <SkillPill key={i} skill={i} />)}
                </div>
              ) : null}
            </div>
          </div>
        </div>
      ) : (
        /* Edit mode */
        <div className="card p-6">
          {error ? (
            <div className="mb-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700">{error}</div>
          ) : null}
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="label">Full name</label>
              <input className="input" value={form.name} onChange={(e) => set("name", e.target.value)} />
            </div>
            <div>
              <label className="label">Phone</label>
              <input className="input" value={form.phone} onChange={(e) => set("phone", e.target.value)} />
            </div>
            <div>
              <label className="label">College</label>
              <input className="input" value={form.college} onChange={(e) => set("college", e.target.value)} />
            </div>
            <div>
              <label className="label">Degree</label>
              <select
                className="input"
                value={isOtherDegree ? "Other" : form.degree}
                onChange={(e) => {
                  const v = e.target.value;
                  if (v === "Other") {
                    // keep the previously saved degree as a starting point for editing
                    setForm((f) => ({ ...f, degree: "Other", customDegree: f.degree && f.degree !== "Other" ? f.degree : "" }));
                  } else {
                    set("degree", v);
                  }
                }}
              >
                {[...new Set([form.degree, ...DEGREE_OPTIONS].filter((d) => d && d !== "Other")), "Other"].map((d) => (
                  <option key={d}>{d}</option>
                ))}
              </select>
            </div>
            {isOtherDegree && (
              <div>
                <label className="label">Enter your degree *</label>
                <input
                  className="input"
                  placeholder="B.Sc. Computer Science"
                  value={form.customDegree || ""}
                  onChange={(e) => set("customDegree", e.target.value)}
                />
              </div>
 )}
            <div>
              <label className="label">Department</label>
              <input className="input" value={form.department} onChange={(e) => set("department", e.target.value)} />
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
            <div>
              <label className="label">Experience level</label>
              <select className="input" value={form.experience_level} onChange={(e) => set("experience_level", e.target.value)}>
                {["Beginner", "Intermediate", "Advanced"].map((l) => <option key={l}>{l}</option>)}
              </select>
            </div>
            <div>
              <label className="label">Preferred career</label>
              <select className="input" value={form.preferred_career} onChange={(e) => set("preferred_career", e.target.value)}>
                <option value="">Not decided yet</option>
                {CAREER_OPTIONS.map((c) => <option key={c}>{c}</option>)}
              </select>
            </div>
          </div>
          <div className="mt-4">
            <label className="label">Skills</label>
            <div className="flex flex-wrap gap-1.5">
              {form.skills.map((s) => (
                <button key={s} type="button" onClick={() => set("skills", form.skills.filter((x) => x !== s))}
                  className="chip border border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-rose-50 hover:text-rose-600">
                  {s} <X size={12} />
                </button>
              ))}
            </div>
            <input
              className="input mt-2"
              placeholder="Type a skill and press Enter…"
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === ",") {
                  e.preventDefault();
                  const v = e.target.value.trim().replace(/,$/, "");
                  if (v && !form.skills.includes(v)) set("skills", [...form.skills, v]);
                  e.target.value = "";
                }
              }}
            />
          </div>
          <div className="mt-6 flex justify-end gap-2">
            <button className="btn-ghost" onClick={() => setEditing(false)} disabled={busy}>
              <X size={16} /> Cancel
            </button>
            <button className="btn-primary" onClick={save} disabled={busy}>
              {busy ? <Loader2 size={16} className="animate-spin" /> : <Check size={16} />}
              {busy ? "Saving…" : "Save changes"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
