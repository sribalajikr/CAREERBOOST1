import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Eye, EyeOff, Loader2, UserPlus } from "lucide-react";
import AuthShell from "../components/AuthShell.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import { getErrorMessage } from "../services/api.js";
import { passwordProblem } from "../validation.js";

function PasswordInput({ id, value, onChange, placeholder, autoComplete, required = true }) {
  const [show, setShow] = useState(false);
  return (
    <div className="relative">
      <input
        id={id}
        type={show ? "text" : "password"}
        required={required}
        autoComplete={autoComplete}
        className="input pr-11"
        placeholder={placeholder}
        value={value}
        onChange={onChange}
      />
      <button
        type="button"
        onClick={() => setShow(!show)}
        className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
        aria-label={show ? "Hide password" : "Show password"}
      >
        {show ? <EyeOff size={18} /> : <Eye size={18} />}
      </button>
    </div>
  );
}

export default function Signup() {
  const { signup } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "", confirm: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const pwProblem = form.password ? passwordProblem(form.password) : "";

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    const problem = passwordProblem(form.password);
    if (problem) {
      setError(problem);
      return;
    }
    if (form.password !== form.confirm) {
      setError("Passwords don't match. Please check and try again.");
      return;
    }
    setBusy(true);
    try {
      await signup(form.name.trim(), form.email.trim(), form.password);
      toast.success("Account created! Let's set up your profile.");
      navigate("/onboarding", { replace: true });
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell title="Create your free account" subtitle="Two minutes to set up. A whole semester of smarter prep.">
      <form onSubmit={submit} className="space-y-4">
        {error ? (
          <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700">{error}</div>
        ) : null}
        <div>
          <label className="label" htmlFor="name">Full name</label>
          <input id="name" required className="input" placeholder="Priya Sharma" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </div>
        <div>
          <label className="label" htmlFor="email">Email</label>
          <input id="email" type="email" required autoComplete="email" className="input" placeholder="you@college.edu" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="password">Password</label>
            <PasswordInput
              id="password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              placeholder="8+ chars, 1 uppercase, 1 special"
              autoComplete="new-password"
            />
            {pwProblem ? (
              <p className="mt-1.5 text-xs font-medium text-rose-600">{pwProblem}</p>
            ) : (
              <p className="mt-1.5 text-xs font-medium text-emerald-600">✓ Strong password</p>
            )}
          </div>
          <div>
            <label className="label" htmlFor="confirm">Confirm password</label>
            <PasswordInput
              id="confirm"
              value={form.confirm}
              onChange={(e) => setForm({ ...form, confirm: e.target.value })}
              placeholder="Repeat it"
              autoComplete="new-password"
            />
            {form.confirm && form.confirm !== form.password ? (
              <p className="mt-1.5 text-xs font-medium text-rose-600">Passwords don't match yet.</p>
            ) : null}
          </div>
        </div>
        <button className="btn-primary w-full" disabled={busy}>
          {busy ? <Loader2 size={18} className="animate-spin" /> : <UserPlus size={18} />}
          {busy ? "Creating account…" : "Create account"}
        </button>
      </form>
      <p className="mt-6 text-center text-sm text-slate-500">
        Already have an account?{" "}
        <Link to="/login" className="font-bold text-brand-600 hover:text-brand-700">
          Log in
        </Link>
      </p>
    </AuthShell>
  );
}
