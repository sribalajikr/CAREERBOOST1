import { Compass, FileText, Sparkles, Target } from "lucide-react";

const PERKS = [
  { icon: FileText, title: "AI resume feedback", text: "See your score and exactly what to fix — in plain language." },
  { icon: Compass, title: "Find your best-fit careers", text: "Personalized matches based on your skills and interests." },
  { icon: Target, title: "A roadmap you can follow", text: "Step-by-step phases with free resources and mini projects." },
  { icon: Sparkles, title: "Practice interviews that coach", text: "Mock interviews with instant, actionable feedback." },
];

export default function AuthShell({ title, subtitle, children }) {
  return (
    <div className="flex min-h-screen bg-slate-50">
      {/* Left brand panel — desktop only */}
      <div className="relative hidden w-[46%] flex-col justify-between overflow-hidden bg-gradient-to-br from-brand-700 via-brand-600 to-brand-800 p-10 text-white lg:flex">
        <div className="pointer-events-none absolute -right-24 -top-24 h-80 w-80 rounded-full bg-white/10 blur-2xl" />
        <div className="pointer-events-none absolute -bottom-32 -left-16 h-96 w-96 rounded-full bg-brand-400/20 blur-3xl" />
        <div className="relative flex items-center gap-3">
          <div className="rounded-2xl bg-white/15 p-2.5 backdrop-blur">
            <svg width="26" height="26" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2L2 7l10 5 10-5-10-5zm0 9L2 6v6c0 5.52 4.48 10 10 10s10-4.48 10-10V6l-10 5z" /></svg>
          </div>
          <div>
            <p className="text-lg font-extrabold">CareerBoost</p>
            <p className="text-xs text-brand-100">AI Interview Prep & Career Guidance</p>
          </div>
        </div>
        <div className="relative">
          <h2 className="max-w-md text-3xl font-extrabold leading-tight">
            Your personal career assistant, built for students.
          </h2>
          <p className="mt-3 max-w-md text-sm leading-relaxed text-brand-100">
            Analyze your resume, discover careers that fit you, follow a guided roadmap and get a study plan that adapts every day — completely free.
          </p>
          <div className="mt-8 grid grid-cols-2 gap-4">
            {PERKS.map(({ icon: Icon, title: t, text }) => (
              <div key={t} className="rounded-2xl bg-white/10 p-4 backdrop-blur transition hover:bg-white/15">
                <Icon size={20} className="text-brand-100" />
                <p className="mt-2 text-sm font-bold">{t}</p>
                <p className="mt-1 text-xs leading-relaxed text-brand-100/90">{text}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right form panel */}
      <div className="flex flex-1 items-center justify-center px-4 py-10">
        <div className="w-full max-w-md animate-fade-up">
          {/* Mobile brand */}
          <div className="mb-8 flex items-center justify-center gap-2.5 lg:hidden">
            <div className="rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 p-2 text-white shadow-lift">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2L2 7l10 5 10-5-10-5zm0 9L2 6v6c0 5.52 4.48 10 10 10s10-4.48 10-10V6l-10 5z" /></svg>
            </div>
            <p className="text-xl font-extrabold text-slate-800">CareerBoost</p>
          </div>
          <div className="card p-6 sm:p-8">
            <h1 className="text-2xl font-extrabold text-slate-800">{title}</h1>
            {subtitle ? <p className="mt-1.5 text-sm text-slate-500">{subtitle}</p> : null}
            <div className="mt-6">{children}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
