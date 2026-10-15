import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Eye, EyeOff, Loader2, LogIn } from "lucide-react";
import AuthShell from "../components/AuthShell.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import { getErrorMessage } from "../services/api.js";

export default function Login() {
  const { login } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ email: "", password: "" });
  const [showPass, setShowPass] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const expired = new URLSearchParams(location.search).get("expired");

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const user = await login(form.email.trim(), form.password);
      toast.success(`Welcome back, ${user.name.split(" ")[0]}! 👋`);
      navigate(user.onboarded ? "/dashboard" : "/onboarding", { replace: true });
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell
      title="Welcome back"
      subtitle={expired ? "Your session expired — please log in again." : "Let's continue your career journey."}
    >
      <form onSubmit={submit} className="space-y-4">
        {error ? (
          <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700">{error}</div>
        ) : null}
        <div>
          <label className="label" htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            required
            autoComplete="email"
            className="input"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
          />
        </div>
        <div>
          <div className="flex items-center justify-between">
            <label className="label" htmlFor="password">Password</label>
            <Link to="/forgot-password" className="mb-1.5 text-xs font-semibold text-brand-600 hover:text-brand-700">
              Forgot password?
            </Link>
          </div>
          <div className="relative">
            <input
              id="password"
              type={showPass ? "text" : "password"}
              required
              autoComplete="current-password"
              className="input pr-11"
              placeholder="••••••••"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
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
        </div>
        <button className="btn-primary w-full" disabled={busy}>
          {busy ? <Loader2 size={18} className="animate-spin" /> : <LogIn size={18} />}
          {busy ? "Logging in…" : "Log in"}
        </button>
      </form>
      <p className="mt-6 text-center text-sm text-slate-500">
        New here?{" "}
        <Link to="/signup" className="font-bold text-brand-600 hover:text-brand-700">
          Create a free account
        </Link>
      </p>
    </AuthShell>
  );
}
