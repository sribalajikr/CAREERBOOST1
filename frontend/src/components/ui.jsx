import { useEffect } from "react";
import { X } from "lucide-react";

/** Small stat card used across the dashboard and headers. */
export function DashboardCard({ icon: Icon, label, value, suffix = "%", sub, accent = "brand", onClick, cta }) {
  const accents = {
    brand: "bg-brand-50 text-brand-600",
    emerald: "bg-emerald-50 text-emerald-600",
    amber: "bg-amber-50 text-amber-600",
    sky: "bg-sky-50 text-sky-600",
    rose: "bg-rose-50 text-rose-600",
  };
  return (
    <button
      type="button"
      onClick={onClick}
      className={`card group p-5 text-left transition-all duration-200 ${onClick ? "hover:shadow-lift hover:-translate-y-0.5" : "cursor-default"}`}
    >
      <div className="flex items-start justify-between">
        <div className={`rounded-xl p-2.5 ${accents[accent] || accents.brand}`}>
          {Icon ? <Icon size={20} /> : null}
        </div>
        {cta ? <span className="text-xs font-semibold text-brand-600 opacity-0 transition group-hover:opacity-100">{cta} →</span> : null}
      </div>
      <p className="mt-3 text-3xl font-extrabold tracking-tight text-slate-800">
        {value}
        {value !== "—" && suffix ? <span className="text-lg text-slate-400">{suffix}</span> : null}
      </p>
      <p className="mt-0.5 text-sm font-medium text-slate-500">{label}</p>
      {sub ? <p className="mt-1 text-xs text-slate-400">{sub}</p> : null}
    </button>
  );
}

export function ProgressBar({ value = 0, size = "md", tone = "brand", className = "" }) {
  const heights = { sm: "h-1.5", md: "h-2.5", lg: "h-3.5" };
  const tones = {
    brand: "bg-gradient-to-r from-brand-500 to-brand-400",
    emerald: "bg-gradient-to-r from-emerald-500 to-emerald-400",
    amber: "bg-gradient-to-r from-amber-500 to-amber-400",
  };
  return (
    <div className={`w-full overflow-hidden rounded-full bg-slate-100 ${heights[size]} ${className}`}>
      <div
        className={`${heights[size]} rounded-full ${tones[tone]} transition-all duration-700 ease-out`}
        style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
      />
    </div>
  );
}

/** Circular progress ring for scores. */
export function ScoreRing({ value, size = 120, stroke = 10, label, tone = "#4f46e5" }) {
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (Math.max(0, Math.min(100, value)) / 100) * circumference;
  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} stroke="#e2e8f0" strokeWidth={stroke} fill="none" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={tone}
          strokeWidth={stroke}
          fill="none"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 1s ease" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-extrabold text-slate-800">{value}</span>
        {label ? <span className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">{label}</span> : null}
      </div>
    </div>
  );
}

export function LoadingSpinner({ size = 28, className = "", label }) {
  return (
    <div className={`flex flex-col items-center justify-center gap-3 ${className}`} role="status">
      <div
        className="animate-spin rounded-full border-[3px] border-slate-200 border-t-brand-600"
        style={{ width: size, height: size }}
      />
      {label ? <p className="text-sm text-slate-500">{label}</p> : null}
    </div>
  );
}

export function PageLoader({ label = "Loading…" }) {
  return (
    <div className="flex min-h-[50vh] items-center justify-center">
      <LoadingSpinner size={36} label={label} />
    </div>
  );
}

export function Modal({ open, onClose, title, children, footer }) {
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose?.();
    if (open) window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true">
      <div className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm animate-fade-in" onClick={onClose} />
      <div className="card relative z-10 w-full max-w-lg animate-scale-in p-6">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-bold text-slate-800">{title}</h3>
          <button onClick={onClose} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600" aria-label="Close">
            <X size={18} />
          </button>
        </div>
        <div>{children}</div>
        {footer ? <div className="mt-6 flex justify-end gap-2">{footer}</div> : null}
      </div>
    </div>
  );
}

export function EmptyState({ icon: Icon, title, description, action }) {
  return (
    <div className="card flex flex-col items-center justify-center px-6 py-14 text-center">
      {Icon ? (
        <div className="mb-4 rounded-2xl bg-brand-50 p-4 text-brand-500">
          <Icon size={30} />
        </div>
      ) : null}
      <h3 className="text-base font-bold text-slate-800">{title}</h3>
      {description ? <p className="mt-1 max-w-sm text-sm text-slate-500">{description}</p> : null}
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  );
}

export function ErrorState({ message, onRetry }) {
  return (
    <div className="card flex flex-col items-center justify-center px-6 py-12 text-center">
      <div className="mb-3 rounded-2xl bg-rose-50 p-3 text-rose-500">
        <X size={26} />
      </div>
      <h3 className="text-base font-bold text-slate-800">Something went wrong</h3>
      <p className="mt-1 max-w-sm text-sm text-slate-500">{message}</p>
      {onRetry ? (
        <button className="btn-secondary mt-4" onClick={onRetry}>
          Try again
        </button>
      ) : null}
    </div>
  );
}

/** Friendly section header with optional emoji. */
export function SectionHeader({ title, subtitle, right }) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h2 className="text-xl font-bold text-slate-800 sm:text-2xl">{title}</h2>
        {subtitle ? <p className="mt-1 text-sm text-slate-500">{subtitle}</p> : null}
      </div>
      {right}
    </div>
  );
}

export function SkillPill({ skill, tone = "slate" }) {
  const tones = {
    slate: "bg-slate-100 text-slate-600",
    green: "bg-emerald-50 text-emerald-700 border border-emerald-200",
    amber: "bg-amber-50 text-amber-700 border border-amber-200",
  };
  return <span className={`chip ${tones[tone]}`}>{skill}</span>;
}

export function Tooltip({ text, children }) {
  return (
    <span className="group relative inline-flex items-center">
      {children}
      <span className="pointer-events-none absolute bottom-full left-1/2 z-30 mb-1.5 -translate-x-1/2 whitespace-nowrap rounded-lg bg-slate-800 px-2.5 py-1.5 text-xs font-medium text-white opacity-0 shadow-lift transition-opacity duration-200 group-hover:opacity-100">
        {text}
      </span>
    </span>
  );
}
