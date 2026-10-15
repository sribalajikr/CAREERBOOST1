import { useCallback, useEffect, useRef, useState } from "react";
import {
  AlertTriangle, CheckCircle2, CloudUpload, FileText, Loader2, RefreshCw, Sparkles, X,
} from "lucide-react";
import { api, getErrorMessage } from "../services/api.js";
import { EmptyState, LoadingSpinner, ProgressBar, ScoreRing, SectionHeader, SkillPill } from "../components/ui.jsx";

export default function ResumeAnalysis() {
  const [file, setFile] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const inputRef = useRef(null);

  const loadLatest = useCallback(() => {
    api.latestResume().then((r) => {
      if (r && r.score > 0) setResult({ ...r.analysis, file_name: r.file_name });
    }).catch(() => {});
    api.resumeHistory().then(setHistory).catch(() => {});
  }, []);
  useEffect(loadLatest, [loadLatest]);

  const pickFile = (f) => {
    setError("");
    if (!f) return;
    if (!f.name.toLowerCase().endsWith(".pdf")) {
      setError("Please choose a PDF file — other formats aren't supported yet.");
      return;
    }
    if (f.size > 5 * 1024 * 1024) {
      setError("That PDF is larger than 5 MB. Please compress it first.");
      return;
    }
    setFile(f);
    setResult(null);
  };

  const analyze = async () => {
    if (!file) return;
    setBusy(true);
    setError("");
    setProgress(0);
    try {
      const data = await api.analyzeResume(file, setProgress);
      setResult(data);
      setHistory((h) => [{ file_name: file.name, score: data.score, created_at: new Date().toISOString() }, ...h].slice(0, 10));
    } catch (e) {
      setError(getErrorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const drop = (e) => {
    e.preventDefault();
    setDragging(false);
    pickFile(e.dataTransfer.files?.[0]);
  };

  return (
    <div className="space-y-6">
      <SectionHeader
        title="AI Resume Analysis"
        subtitle="Upload your resume PDF — get a score, strengths and simple fixes in seconds."
        right={<span className="chip bg-brand-50 text-brand-600"><Sparkles size={13} /> Powered by rule-based AI · 100% free</span>}
      />

      {/* Upload zone */}
      <div
        className={`card relative flex flex-col items-center justify-center border-2 border-dashed p-8 text-center transition-all sm:p-10 ${
          dragging ? "border-brand-500 bg-brand-50/60 scale-[1.01]" : "border-slate-200 hover:border-brand-300 hover:bg-slate-50/50"
        }`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={drop}
      >
        <input ref={inputRef} type="file" accept="application/pdf,.pdf" className="hidden"
          onChange={(e) => pickFile(e.target.files?.[0])} />
        <div className="rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 p-4 text-white shadow-lift">
          <CloudUpload size={28} />
        </div>
        {file ? (
          <>
            <p className="mt-4 flex items-center gap-2 text-sm font-bold text-slate-800">
              <FileText size={16} className="text-brand-500" /> {file.name}
              <button onClick={() => { setFile(null); if (inputRef.current) inputRef.current.value = ""; }}
                className="rounded-full p-1 text-slate-400 hover:bg-rose-50 hover:text-rose-500" aria-label="Remove file">
                <X size={14} />
              </button>
            </p>
            <p className="mt-1 text-xs text-slate-400">{(file.size / 1024).toFixed(0)} KB · ready to analyze</p>
            <div className="mt-4 flex gap-2">
              <button className="btn-primary" onClick={analyze} disabled={busy}>
                {busy ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
                {busy ? "Analyzing…" : result ? "Re-analyze" : "Analyze My Resume"}
              </button>
            </div>
          </>
        ) : (
          <>
            <p className="mt-4 text-sm font-semibold text-slate-700">Drag & drop your resume PDF here</p>
            <p className="mt-1 text-xs text-slate-400">or</p>
            <button className="btn-secondary mt-2" onClick={() => inputRef.current?.click()}>Browse files</button>
            <p className="mt-3 text-[11px] text-slate-400">PDF only · up to 5 MB</p>
          </>
        )}
        {busy && (
          <div className="mt-5 w-full max-w-sm">
            <ProgressBar value={progress || 8} size="sm" />
            <p className="mt-1.5 text-xs text-slate-400">Uploading & analyzing… {progress}%</p>
          </div>
        )}
        {error && (
          <div className="mt-4 flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 px-4 py-2.5 text-sm font-medium text-rose-700">
            <AlertTriangle size={15} /> {error}
          </div>
        )}
      </div>

      {/* Results */}
      {busy && !result && (
        <div className="py-10"><LoadingSpinner label="Reading your resume and checking every section…" /></div>
      )}

      {result && (
        <div className="space-y-5 animate-fade-up">
          {/* Score + summary */}
          <div className="card flex flex-col items-center gap-6 p-6 sm:flex-row sm:p-8">
            <ScoreRing value={result.score} label="/ 100" size={130} />
            <div className="flex-1 text-center sm:text-left">
              <div className="flex flex-wrap items-center justify-center gap-2 sm:justify-start">
                <h3 className="text-xl font-extrabold text-slate-800">{result.grade_label}</h3>
                {result.file_name && <span className="chip bg-slate-100 text-slate-500">{result.file_name}</span>}
              </div>
              <p className="mt-2 text-sm leading-relaxed text-slate-600">{result.summary}</p>
              <div className="mt-3 flex flex-wrap justify-center gap-2 sm:justify-start">
                <span className="chip bg-emerald-50 text-emerald-700">Job readiness: {result.job_readiness}%</span>
                <span className="chip bg-brand-50 text-brand-600">{result.skills?.length || 0} skills found</span>
                <span className="chip bg-amber-50 text-amber-700">{result.improvements?.length || 0} suggestions</span>
              </div>
            </div>
          </div>

          {/* Skills */}
          <div className="grid gap-5 lg:grid-cols-2">
            <div className="card p-6">
              <h3 className="section-title">Skills We Found</h3>
              {result.skills?.length ? (
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {result.skills.map((s) => <SkillPill key={s} skill={s} tone="green" />)}
                </div>
              ) : (
                <p className="mt-2 text-sm text-slate-400">No technical skills detected — try mentioning them explicitly.</p>
              )}
            </div>

            <div className="card p-6">
              <h3 className="section-title flex items-center gap-2 text-emerald-700"><CheckCircle2 size={18} /> Strengths</h3>
              <ul className="mt-3 space-y-2">
                {(result.strengths || []).map((s, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-slate-600">
                    <CheckCircle2 size={15} className="mt-0.5 shrink-0 text-emerald-500" /> {s}
                  </li>
                ))}
              </ul>
              <h3 className="section-title mt-6 flex items-center gap-2 text-amber-700"><AlertTriangle size={18} /> Areas to Improve</h3>
              <ul className="mt-3 space-y-2">
                {(result.improvements || []).map((s, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-slate-600">
                    <AlertTriangle size={15} className="mt-0.5 shrink-0 text-amber-500" /> {s}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Sections checklist + formatting */}
          <div className="grid gap-5 lg:grid-cols-2">
            <div className="card p-6">
              <h3 className="section-title">Resume Sections</h3>
              <div className="mt-3 grid grid-cols-2 gap-2">
                {Object.entries(result.sections || {}).map(([k, ok]) => (
                  <div key={k} className={`flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium ${ok ? "bg-emerald-50 text-emerald-700" : "bg-rose-50 text-rose-600"}`}>
                    {ok ? <CheckCircle2 size={15} /> : <X size={15} />} <span className="capitalize">{k}</span>
                  </div>
                ))}
              </div>
              {result.missing_sections?.length ? (
                <p className="mt-3 rounded-xl bg-amber-50 px-3 py-2 text-xs font-medium text-amber-700">
                  Missing: {result.missing_sections.join(", ")} — recruiters look for these!
                </p>
              ) : null}
            </div>
            <div className="card p-6">
              <h3 className="section-title">Formatting Notes</h3>
              <ul className="mt-3 space-y-2">
                {(result.formatting || []).map((f, i) => {
                  const level = f.level || (f.ok ? "ok" : "warn");
                  const message = f.message || (f.check ? `${f.check} — ${f.ok ? "looks good" : "needs attention"}` : "");
                  if (!message) return null;
                  return (
                    <li key={i} className="flex items-start gap-2 text-sm text-slate-600">
                      {level === "error"
                        ? <X size={15} className="mt-0.5 shrink-0 text-rose-500" />
                        : level === "ok"
                        ? <CheckCircle2 size={15} className="mt-0.5 shrink-0 text-emerald-500" />
                        : <AlertTriangle size={15} className="mt-0.5 shrink-0 text-amber-500" />}
                      <span>{message}</span>
                    </li>
                  );
                })}
                {!result.formatting?.length && <li className="text-sm text-slate-400">No formatting issues detected. 🎉</li>}
              </ul>
            </div>
          </div>

          {/* History + CTA */}
          <div className="flex flex-col items-center gap-4 rounded-3xl bg-gradient-to-br from-brand-600 to-brand-800 p-6 text-white sm:flex-row sm:justify-between sm:p-8">
            <div>
              <h3 className="text-lg font-extrabold">Your resume is getting stronger! 💪</h3>
              <p className="mt-1 text-sm text-brand-100">Apply the fixes above, upload again, and watch your score climb.</p>
              {history.length > 1 && (
                <p className="mt-2 text-xs text-brand-200">
                  Previous uploads: {history.slice(1, 4).map((h) => `${h.file_name} (${h.score})`).join(" · ")}
                </p>
              )}
            </div>
            <button
              className="btn bg-white text-brand-700 hover:bg-brand-50 active:scale-[.98]"
              onClick={() => { setFile(null); setResult(null); if (inputRef.current) inputRef.current.value = ""; loadLatest(); }}
            >
              <RefreshCw size={16} /> Analyze another resume
            </button>
          </div>
        </div>
      )}

      {!result && !busy && !file && (
        <EmptyState
          icon={FileText}
          title="No resume analyzed yet"
          description="Upload the PDF of your current resume to see your score, strengths and the exact fixes that matter most."
          action={<button className="btn-primary" onClick={() => inputRef.current?.click()}>Choose my resume PDF</button>}
        />
      )}
    </div>
  );
}
