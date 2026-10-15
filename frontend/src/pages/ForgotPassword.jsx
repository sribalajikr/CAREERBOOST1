import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Eye, EyeOff, KeyRound, Loader2, Mail } from "lucide-react";
import AuthShell from "../components/AuthShell.jsx";
import { api, getErrorMessage } from "../services/api.js";
import { useToast } from "../context/ToastContext.jsx";
import { passwordProblem } from "../validation.js";

export default function ForgotPassword() {
  const toast = useToast();
  const navigate = useNavigate();
  const [step, setStep] = useState(1); // 1 request code, 2 reset
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [sent, setSent] = useState(""); // friendly confirmation once the email is sent
  const [showPass, setShowPass] = useState(false);

  const requestCode = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    setSent("");
    try {
      const res = await api.forgotPassword(email.trim());
      setSent(res.detail || "Reset code sent.");
      setStep(2);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const doReset = async (e) => {
    e.preventDefault();
    setError("");
    const problem = passwordProblem(newPassword);
    if (problem) {
      setError(problem);
      return;
    }
    setBusy(true);
    try {
      const res = await api.resetPassword({ email: email.trim(), code, new_password: newPassword });
      toast.success(res.detail || "Password updated!");
      navigate("/login", { replace: true });
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell title="Reset your password" subtitle="We'll help you get back into your account.">
      {step === 1 ? (
        <form onSubmit={requestCode} className="space-y-4">
          {error ? (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700">{error}</div>
          ) : null}
          <div>
            <label className="label" htmlFor="email">Account email</label>
            <input id="email" type="email" required className="input" placeholder="you@college.edu" value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <button className="btn-primary w-full" disabled={busy}>
            {busy ? <Loader2 size={18} className="animate-spin" /> : <Mail size={18} />}
            {busy ? "Sending…" : "Send reset code"}
          </button>
        </form>
      ) : (
        <form onSubmit={doReset} className="space-y-4">
          {error ? (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700">{error}</div>
          ) : null}
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
            <span className="font-bold">Check your inbox!</span> We sent a 6-digit code to{" "}
            <span className="font-bold">{email}</span>. Enter it below to set a new password.
            {sent ? <span className="mt-1 block text-xs text-emerald-700">{sent}</span> : null}
          </div>
          <div>
            <label className="label" htmlFor="code">6-digit code</label>
            <input id="code" required maxLength={6} className="input text-center text-lg tracking-[0.4em]" placeholder="••••••" value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} />
          </div>
          <div>
            <label className="label" htmlFor="newPassword">New password</label>
            <div className="relative">
              <input
                id="newPassword"
                type={showPass ? "text" : "password"}
                required
                className="input pr-11"
                placeholder="8+ chars, 1 uppercase, 1 special"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
              />
              <button
                type="button"
                onClick={() => setShowPass(!showPass)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                aria-label={showPass ? "Hide password" : "Show password"}
              >
                {showPass ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
            {newPassword && passwordProblem(newPassword) ? (
              <p className="mt-1.5 text-xs font-medium text-rose-600">{passwordProblem(newPassword)}</p>
            ) : null}
          </div>
          <button className="btn-primary w-full" disabled={busy}>
            {busy ? <Loader2 size={18} className="animate-spin" /> : <KeyRound size={18} />}
            {busy ? "Updating…" : "Set new password"}
          </button>
          <button type="button" className="btn-ghost w-full" onClick={() => setStep(1)}>
            Use a different email
          </button>
        </form>
      )}
      <p className="mt-6 text-center text-sm text-slate-500">
        Remembered it?{" "}
        <Link to="/login" className="font-bold text-brand-600 hover:text-brand-700">
          Back to login
        </Link>
      </p>
    </AuthShell>
  );
}
