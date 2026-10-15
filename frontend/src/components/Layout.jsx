import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import {
  BookOpenCheck,
  BotMessageSquare,
  ChartSpline,
  Compass,
  FileText,
  GraduationCap,
  LayoutDashboard,
  ListChecks,
  LogOut,
  Menu,
  Mic,
  Target,
  User as UserIcon,
  X,
} from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import { ProgressBar } from "./ui.jsx";

const NAV = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/resume", label: "Resume Analysis", icon: FileText },
  { to: "/careers", label: "Careers", icon: Compass },
  { to: "/roadmap", label: "Planner", icon: BookOpenCheck },
  { to: "/interview-prep", label: "Interview Prep", icon: ListChecks },
  { to: "/mock-interview", label: "Mock Interview", icon: BotMessageSquare },
  { to: "/speech", label: "Speech Practice", icon: Mic },
  { to: "/analytics", label: "Analytics", icon: ChartSpline },
  { to: "/placement", label: "Placement", icon: Target },
  { to: "/profile", label: "Profile", icon: UserIcon },
];

function NavItems({ onNavigate }) {
  return (
    <nav className="flex flex-col gap-1">
      {NAV.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          onClick={onNavigate}
          className={({ isActive }) =>
            `flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-semibold transition-all ${
              isActive
                ? "bg-brand-600 text-white shadow-lift"
                : "text-slate-500 hover:bg-brand-50 hover:text-brand-700"
            }`
          }
        >
          <Icon size={18} />
          {label}
        </NavLink>
      ))}
    </nav>
  );
}

function Brand({ compact = false }) {
  return (
    <div className="flex items-center gap-2.5">
      <div className="rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 p-2 text-white shadow-lift">
        <GraduationCap size={compact ? 18 : 22} />
      </div>
      {!compact && (
        <div>
          <p className="text-base font-extrabold leading-tight text-slate-800">CareerBoost</p>
          <p className="text-[11px] font-medium text-slate-400">AI Career Assistant</p>
        </div>
      )}
    </div>
  );
}

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleLogout = () => {
    logout();
    toast.info("Logged out. See you soon! 👋");
    navigate("/login");
  };

  const firstName = (user?.name || "Student").split(" ")[0];
  const completion = user?.profile ? 100 : 0;

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r border-slate-100 bg-white px-4 py-6 lg:flex">
        <div className="px-2">
          <Brand />
        </div>
        <div className="mt-8 flex-1">
          <p className="mb-2 px-3.5 text-[11px] font-bold uppercase tracking-wider text-slate-400">Menu</p>
          <NavItems />
        </div>
        <div className="rounded-2xl bg-gradient-to-br from-brand-600 to-brand-800 p-4 text-white">
          <p className="text-sm font-bold">Profile strength</p>
          <p className="mt-0.5 text-xs text-brand-100">A complete profile = better matches</p>
          <div className="mt-3">
            <ProgressBar value={completion} tone="emerald" size="sm" />
          </div>
          <button
            onClick={() => navigate("/profile")}
            className="mt-3 w-full rounded-lg bg-white/15 py-1.5 text-xs font-semibold backdrop-blur transition hover:bg-white/25"
          >
            Complete profile
          </button>
        </div>
      </aside>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm animate-fade-in" onClick={() => setMobileOpen(false)} />
          <div className="absolute inset-y-0 left-0 w-72 animate-fade-in bg-white p-5 shadow-2xl">
            <div className="flex items-center justify-between">
              <Brand />
              <button onClick={() => setMobileOpen(false)} className="rounded-lg p-2 text-slate-400 hover:bg-slate-100" aria-label="Close menu">
                <X size={20} />
              </button>
            </div>
            <div className="mt-8">
              <NavItems onNavigate={() => setMobileOpen(false)} />
            </div>
            <button
              onClick={handleLogout}
              className="mt-6 flex w-full items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-semibold text-rose-500 hover:bg-rose-50"
            >
              <LogOut size={18} /> Log out
            </button>
          </div>
        </div>
      )}

      {/* Main column */}
      <div className="lg:pl-64">
        {/* Top navbar */}
        <header className="sticky top-0 z-20 border-b border-slate-100 bg-white/80 backdrop-blur">
          <div className="flex items-center justify-between gap-3 px-4 py-3 sm:px-6">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setMobileOpen(true)}
                className="rounded-xl p-2 text-slate-500 hover:bg-slate-100 lg:hidden"
                aria-label="Open menu"
              >
                <Menu size={22} />
              </button>
              <div className="lg:hidden">
                <Brand compact />
              </div>
              <p className="hidden text-sm font-medium text-slate-500 lg:block">
                Welcome back, <span className="font-bold text-slate-800">{firstName}</span> 👋
              </p>
            </div>
            <div className="flex items-center gap-2">
              <NavLink
                to="/profile"
                className="hidden items-center gap-2 rounded-xl border border-slate-200 py-1.5 pl-1.5 pr-3 text-sm font-semibold text-slate-600 transition hover:border-brand-300 hover:text-brand-700 sm:flex"
              >
                <span className="rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 p-1.5 text-white">
                  <UserIcon size={14} />
                </span>
                {firstName}
              </NavLink>
              <button
                onClick={handleLogout}
                className="rounded-xl p-2 text-slate-400 transition hover:bg-rose-50 hover:text-rose-500"
                title="Log out"
                aria-label="Log out"
              >
                <LogOut size={19} />
              </button>
            </div>
          </div>
        </header>

        <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-8">
          <div className="page-enter" key={window.location.pathname}>
            {children}
          </div>
        </main>

        {/* Mobile bottom nav */}
        <nav className="sticky bottom-0 z-20 flex items-center justify-around border-t border-slate-100 bg-white/90 py-2 backdrop-blur lg:hidden">
          {NAV.slice(0, 5).map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex flex-col items-center gap-0.5 rounded-lg px-2 py-1 text-[10px] font-semibold ${
                  isActive ? "text-brand-600" : "text-slate-400"
                }`
              }
            >
              <Icon size={19} />
              {label.split(" ")[0]}
            </NavLink>
          ))}
        </nav>
      </div>
    </div>
  );
}
