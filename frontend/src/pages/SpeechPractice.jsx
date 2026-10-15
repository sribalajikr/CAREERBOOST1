import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ArrowRight, Mic, MicOff, RefreshCw, Square, Volume2 } from "lucide-react";
import { api, getErrorMessage } from "../services/api.js";
import { useToast } from "../context/ToastContext.jsx";
import { EmptyState, LoadingSpinner, ProgressBar, SectionHeader } from "../components/ui.jsx";

const FILLER = ["um", "uh", "like", "you know", "basically", "actually", "literally", "sort of", "kind of", "i mean"];

export default function SpeechPractice() {
  const toast = useToast();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [question, setQuestion] = useState(null);
  const [history, setHistory] = useState(null);

  // recording state
  const [supported, setSupported] = useState({ media: false, speech: false });
  const [status, setStatus] = useState("idle"); // idle | recording | paused
  const [seconds, setSeconds] = useState(0);
  const [transcript, setTranscript] = useState("");
  const [micError, setMicError] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [recorded, setRecorded] = useState(false);
  const [serverStt, setServerStt] = useState(false); // backend can transcribe recorded audio
  const [transcribing, setTranscribing] = useState(false);

  const mediaRef = useRef(null);
  const recogRef = useRef(null);
  const timerRef = useRef(null);
  const chunksRef = useRef([]);
  const finalTextRef = useRef("");
  const serverSttRef = useRef(false); // read inside recorder callbacks

  const loadQuestion = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // a NEW interview-style paragraph every time the page loads / refresh / new-paragraph click
      const p = await api.speechParagraph();
      setQuestion({
        id: p.id,
        category: p.category || "Interview Communication",
        topic: p.topic,
        difficulty: p.difficulty || "Intermediate",
        question: p.text,
        word_count: p.word_count,
      });
      setAnalysis(null);
      setTranscript("");
      setStatus("idle");
      setSeconds(0);
      setRecorded(false);
      setMicError(null);
      finalTextRef.current = "";
    } catch (e) {
      setError(getErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }, []);

  const loadHistory = useCallback(() => {
    api.speechHistory().then(setHistory).catch(() => {});
  }, []);

  useEffect(() => {
    setSupported({
      media: !!(navigator.mediaDevices?.getUserMedia && window.MediaRecorder),
      speech: !!(window.SpeechRecognition || window.webkitSpeechRecognition),
    });
    loadQuestion();
    loadHistory();
    // Can the server transcribe recorded audio? (offline Vosk fallback)
    api.transcribeStatus().then((s) => {
      setServerStt(!!s?.available);
      serverSttRef.current = !!s?.available;
    }).catch(() => {});
  }, [loadQuestion, loadHistory]);

  // ---- timer ----
  useEffect(() => {
    if (status === "recording") {
      timerRef.current = setInterval(() => setSeconds((s) => s + 1), 1000);
    }
    return () => clearInterval(timerRef.current);
  }, [status]);

  const fmt = (s) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

  const startRecording = async () => {
    setMicError(null);
    if (!supported.media) {
      setMicError("Voice recording isn't available in this browser — type your answer instead, the analysis is the same.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      chunksRef.current = [];
      mediaRef.current = new MediaRecorder(stream);
      mediaRef.current.ondataavailable = (e) => e.data.size && chunksRef.current.push(e.data);
      mediaRef.current.start();

      // Live transcription (best-effort — Chrome/Edge). When it fails silently
      // (embedded browsers etc.), the recorded audio is sent to the server for
      // offline Vosk transcription after Stop.
      let gotWords = false;
      if (supported.speech) {
        const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
        const r = new SR();
        r.continuous = true;
        r.interimResults = true;
        r.onresult = (ev) => {
          let interim = "";
          for (let i = 0; i < ev.results.length; i++) {
            const res = ev.results[i];
            if (res.isFinal) {
              finalTextRef.current = (finalTextRef.current + " " + res[0].transcript).trim();
              if (res[0].transcript.trim()) gotWords = true;
            } else interim += res[0].transcript;
          }
          setTranscript((finalTextRef.current + " " + interim).trim());
        };
        r.onerror = () => {}; // transcription is optional; recording continues
        r.onend = () => {
          if (mediaRef.current && mediaRef.current.state === "recording") { try { r.start(); } catch { /* ignore */ } }
        };
        r.start();
        recogRef.current = r;
        recogRef.current._gotWords = () => gotWords;
      }
      setStatus("recording");
    } catch (e) {
      setMicError(
        e?.name === "NotAllowedError"
          ? "Microphone access was blocked. Enable it in your browser settings, or use Type Answer — the analysis works the same."
          : "Couldn't start the microphone. Type your answer instead — the analysis works the same."
      );
    }
  };

  const pauseRecording = () => {
    if (mediaRef.current?.state === "recording") {
      mediaRef.current.pause();
      try { recogRef.current?.stop(); } catch { /* ignore */ }
      setStatus("paused");
    }
  };

  const resumeRecording = () => {
    if (mediaRef.current?.state === "paused") {
      mediaRef.current.resume();
      if (supported.speech && recogRef.current) { try { recogRef.current.start(); } catch { /* ignore */ } }
      setStatus("recording");
    }
  };

  const stopRecording = async () => {
    const recog = recogRef.current;
    const recorder = mediaRef.current;
    try { recorder?.stop(); } catch { /* ignore */ }
    try { recorder?.stream.getTracks().forEach((t) => t.stop()); } catch { /* ignore */ }
    try { recog?.stop(); } catch { /* ignore */ }
    recogRef.current = null;
    clearInterval(timerRef.current);
    setStatus("idle");
    setRecorded(true);

    // Live transcript empty but we recorded audio? Send it to the server for
    // offline transcription (Vosk) so speaking still "types" the answer.
    const spokeWords = typeof recog?._gotWords === "function" ? recog._gotWords() : false;
    if (!finalTextRef.current.trim() && recorder && chunksRef.current.length && serverSttRef.current) {
      setTranscribing(true);
      try {
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        const res = await api.transcribeAudio(blob);
        if (res?.text) {
          finalTextRef.current = res.text;
          setTranscript(res.text);
          toast.success("Answer transcribed from your recording. Review and edit if needed.");
        } else {
          toast.info("We couldn't hear clear speech in the recording — type or edit your answer below.");
        }
      } catch (e) {
        toast.info(getErrorMessage(e));
      } finally {
        setTranscribing(false);
      }
    } else if (!spokeWords && !finalTextRef.current.trim() && !serverSttRef.current) {
      // no live transcript and no server fallback installed
      toast.info("Voice typing isn't available here — type your answer below; the analysis is identical.");
    }
  };

  const analyze = async () => {
    const text = transcript.trim();
    if (!text) {
      toast.info("Your answer is empty — record or type something first.");
      return;
    }
    setSubmitting(true);
    try {
      const res = await api.analyzeSpeech({
        question_text: question.question,
        question_id: question.id,
        transcript: text,
        duration_seconds: seconds > 0 ? seconds : null,
        input_mode: recorded ? "voice" : "text",
      });
      setAnalysis(res);
      loadHistory();
    } catch (e) {
      toast.error(getErrorMessage(e));
    } finally {
      setSubmitting(false);
    }
  };

  const reset = () => {
    stopRecording();
    setAnalysis(null);
    setTranscript("");
    setSeconds(0);
    setRecorded(false);
    finalTextRef.current = "";
  };

  const localFillerCount = useMemo(() => {
    if (!transcript) return 0;
    const t = transcript.toLowerCase();
    return FILLER.reduce((n, f) => n + (t.split(f).length - 1), 0);
  }, [transcript]);

  if (loading) return <div className="flex justify-center py-24"><LoadingSpinner label="Generating a fresh paragraph…" /></div>;
  if (error) return <ErrorState message={error} onRetry={loadQuestion} />;

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Speech & Communication Practice"
        subtitle="Answer out loud — get feedback on pace, fillers, structure and relevance based on what can actually be measured."
      />

      {!supported.media && (
        <div className="flex items-start gap-2 rounded-2xl border border-amber-100 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          <MicOff size={16} className="mt-0.5 shrink-0" />
          This browser can't record audio. You can still practise — type your answer and get the full communication analysis.
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        {/* left column */}
        <div className="space-y-6">
          <div className="rounded-3xl border border-slate-100 bg-white p-6 shadow-soft sm:p-8">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full bg-brand-50 px-3 py-1 text-xs font-bold text-brand-700">{question.category}</span>
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">{question.topic}</span>
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">{question.word_count ?? ""} words</span>
            </div>
            <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-400">Read this paragraph aloud — steady pace, clear pronunciation</p>
            <h2 className="mt-1.5 text-lg font-bold leading-snug text-slate-800">{question.question}</h2>

            {/* start row */}
            {status === "idle" && !analysis && (
              <div className="mt-5 flex flex-wrap items-center gap-3">
                <button
                  onClick={startRecording}
                  disabled={submitting || transcribing}
                  className="flex items-center gap-2 rounded-xl bg-rose-500 px-5 py-2.5 text-sm font-bold text-white shadow-lift transition hover:bg-rose-600 disabled:opacity-60"
                >
                  <Mic size={16} /> {recorded ? "Record Again" : "Start Recording"}
                </button>
                <button
                  onClick={() => document.getElementById("sp-typed")?.focus()}
                  className="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-600 transition hover:border-brand-300 hover:text-brand-700"
                >
                  Type Answer
                </button>
              </div>
            )}

            {/* recording bar */}
            {(status === "recording" || status === "paused") && (
              <div className="mt-5 flex flex-wrap items-center gap-3 rounded-2xl bg-slate-900 p-4 text-white animate-fade-in">
                <span className={`h-3 w-3 rounded-full ${status === "recording" ? "animate-pulse bg-rose-500" : "bg-amber-400"}`} />
                <span className="font-mono text-lg font-bold">{fmt(seconds)}</span>
                <span className="text-xs text-slate-300">
                  {status === "recording" ? "Recording… speak naturally" : "Paused"} · {localFillerCount} fillers so far
                </span>
                <div className="ml-auto flex gap-2">
                  {status === "recording" ? (
                    <button onClick={pauseRecording} className="rounded-lg bg-white/10 px-3 py-1.5 text-xs font-bold transition hover:bg-white/20">Pause</button>
                  ) : (
                    <button onClick={resumeRecording} className="rounded-lg bg-white/10 px-3 py-1.5 text-xs font-bold transition hover:bg-white/20">Resume</button>
                  )}
                  <button onClick={stopRecording} className="flex items-center gap-1.5 rounded-lg bg-rose-500 px-3 py-1.5 text-xs font-bold transition hover:bg-rose-600">
                    <Square size={12} /> Stop
                  </button>
                </div>
              </div>
            )}

            {micError && (
              <div className="mt-4 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700">{micError}</div>
            )}

            {/* transcript / typed answer */}
            {transcribing && (
              <div className="mt-4 flex items-center gap-2 rounded-xl bg-brand-50 px-4 py-2.5 text-sm text-brand-700">
                <LoadingSpinner size={14} /> Turning your recording into text…
              </div>
            )}
            <textarea
              id="sp-typed"
              value={transcript}
              onChange={(e) => setTranscript(e.target.value)}
              rows={6}
              placeholder="Your answer appears here as you speak — or just type it. Edit freely before analysing."
              className="mt-4 w-full resize-y rounded-2xl border border-slate-200 p-4 text-sm text-slate-700 outline-none transition focus:border-brand-400 focus:ring-4 focus:ring-brand-100"
              disabled={!!analysis}
            />

            <div className="mt-4 flex flex-wrap items-center gap-3">
              {!analysis ? (
                <>
                  <button
                    onClick={analyze}
                    disabled={submitting}
                    className="flex items-center gap-2 rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-bold text-white shadow-lift transition hover:bg-brand-700 disabled:opacity-60"
                  >
                    {submitting ? <LoadingSpinner size={16} /> : <Volume2 size={16} />} Analyse Answer
                  </button>
                  {(recorded || transcript) && (
                    <button
                      onClick={reset}
                      className="flex items-center gap-2 rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-600 transition hover:border-rose-200 hover:text-rose-500"
                    >
                      <RefreshCw size={15} /> Retry
                    </button>
                  )}
                  <button onClick={loadQuestion} className="ml-auto text-sm font-semibold text-slate-400 transition hover:text-brand-600">
                    New Paragraph
                  </button>
                </>
              ) : (
                <div className="flex flex-wrap gap-3">
                  <button
                    onClick={reset}
                    className="flex items-center gap-2 rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-600 transition hover:border-brand-300 hover:text-brand-700"
                  >
                    <RefreshCw size={15} /> Try Same Question Again
                  </button>
                  <button
                    onClick={loadQuestion}
                    className="flex items-center gap-2 rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-bold text-white shadow-lift transition hover:bg-brand-700"
                  >
                    New Paragraph <ArrowRight size={16} />
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* analysis result */}
          {analysis && (
            <div className="rounded-3xl border border-slate-100 bg-white p-6 shadow-soft animate-fade-in sm:p-8">
              <p className="text-xs font-bold uppercase tracking-wider text-brand-600">Your communication analysis</p>
              <p className="mt-1 text-3xl font-extrabold text-slate-800">
                {analysis.communication_score}%<span className="text-sm font-semibold text-slate-400"> communication</span>
              </p>

              <div className="mt-5 grid gap-4 sm:grid-cols-2">
                <div className="space-y-3">
                  {Object.entries(analysis.scores).filter(([k]) => k !== "communication").map(([k, v]) => (
                    <div key={k}>
                      <div className="flex justify-between text-xs font-semibold">
                        <span className="capitalize text-slate-500">{k}</span>
                        <span className="text-slate-800">{v}%</span>
                      </div>
                      <ProgressBar value={v} size="sm" tone={v >= 70 ? "emerald" : v >= 50 ? "brand" : "rose"} />
                    </div>
                  ))}
                </div>
                <div className="space-y-2 rounded-2xl bg-slate-50 p-4 text-sm text-slate-600">
                  <p><strong>Words:</strong> {analysis.metrics.word_count}</p>
                  <p><strong>Pace:</strong> {analysis.metrics.wpm} wpm</p>
                  <p><strong>Fillers:</strong> {analysis.metrics.total_fillers}</p>
                  {analysis.metrics.duration_seconds ? <p><strong>Duration:</strong> {Math.round(analysis.metrics.duration_seconds)}s</p> : null}
                </div>
              </div>

              <div className="mt-5 grid gap-4 sm:grid-cols-2">
                <div>
                  <p className="text-xs font-bold uppercase tracking-wide text-emerald-600">What you did well</p>
                  <ul className="mt-2 space-y-1.5">
                    {(analysis.feedback.well || []).map((s, i) => (
                      <li key={i} className="flex gap-2 text-sm text-slate-600"><span className="text-emerald-500">✓</span>{s}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <p className="text-xs font-bold uppercase tracking-wide text-amber-600">What you can improve</p>
                  <ul className="mt-2 space-y-1.5">
                    {(analysis.feedback.improve || []).map((s, i) => (
                      <li key={i} className="flex gap-2 text-sm text-slate-600"><span className="text-amber-500">→</span>{s}</li>
                    ))}
                  </ul>
                </div>
              </div>

              <p className="mt-4 rounded-xl bg-brand-50 px-4 py-2.5 text-sm text-brand-800">
                <strong>Practice suggestion:</strong> {analysis.feedback.practice}
              </p>
            </div>
          )}
        </div>

        {/* right column — history */}
        <div className="space-y-4">
          <div className="rounded-3xl border border-slate-100 bg-white p-5 shadow-soft">
            <p className="text-sm font-bold text-slate-700">Recent attempts</p>
            {history?.attempts?.length ? (
              <div className="mt-3 space-y-2">
                {history.attempts.slice(0, 6).map((a) => (
                  <div key={a.id} className="rounded-xl bg-slate-50 px-3 py-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-slate-600">{fmt(a.duration_seconds || 0)}</span>
                      <span className={`font-bold ${a.communication_score >= 70 ? "text-emerald-600" : a.communication_score >= 50 ? "text-amber-600" : "text-rose-500"}`}>
                        {a.communication_score}%
                      </span>
                    </div>
                    <p className="mt-0.5 truncate text-[11px] text-slate-400">{a.question_text}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-2 text-sm text-slate-400">No attempts yet — your scores will appear here.</p>
            )}
          </div>

          <div className="rounded-3xl border border-slate-100 bg-white p-5 shadow-soft">
            <p className="text-sm font-bold text-slate-700">Average communication</p>
            {history?.attempts?.length ? (
              <>
                <p className="mt-1 text-3xl font-extrabold text-brand-700">{history?.avg_communication ?? 0}%</p>
                <ProgressBar value={history?.avg_communication ?? 0} size="sm" className="mt-2" />
              </>
            ) : (
              <p className="mt-2 text-sm text-slate-400">No communication data yet</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
