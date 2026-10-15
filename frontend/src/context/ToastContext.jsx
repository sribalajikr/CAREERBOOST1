import { createContext, useCallback, useContext, useMemo, useState } from "react";
import { CheckCircle2, Info, X, XCircle } from "lucide-react";

const ToastContext = createContext(null);
let idCounter = 0;

const STYLES = {
  success: { icon: CheckCircle2, cls: "border-emerald-200 bg-emerald-50 text-emerald-800" },
  error: { icon: XCircle, cls: "border-rose-200 bg-rose-50 text-rose-800" },
  info: { icon: Info, cls: "border-sky-200 bg-sky-50 text-sky-800" },
};

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const dismiss = useCallback((id) => setToasts((t) => t.filter((x) => x.id !== id)), []);

  const push = useCallback(
    (message, type = "info", ttl = 4200) => {
      const id = ++idCounter;
      setToasts((t) => [...t, { id, message, type }]);
      window.setTimeout(() => dismiss(id), ttl);
    },
    [dismiss]
  );

  const value = useMemo(
    () => ({
      success: (m) => push(m, "success"),
      error: (m) => push(m, "error", 6000),
      info: (m) => push(m, "info"),
    }),
    [push]
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="fixed bottom-4 right-4 z-[100] flex w-[min(92vw,380px)] flex-col gap-2">
        {toasts.map((t) => {
          const { icon: Icon, cls } = STYLES[t.type] || STYLES.info;
          return (
            <div
              key={t.id}
              className={`animate-scale-in flex items-start gap-2.5 rounded-xl border px-4 py-3 shadow-lift ${cls}`}
              role="status"
            >
              <Icon size={18} className="mt-0.5 shrink-0" />
              <p className="flex-1 text-sm font-medium leading-snug">{t.message}</p>
              <button onClick={() => dismiss(t.id)} className="shrink-0 opacity-60 hover:opacity-100" aria-label="Dismiss">
                <X size={16} />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used inside ToastProvider");
  return ctx;
}
