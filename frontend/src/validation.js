/**
 * Shared form validation rules (used by Signup, ForgotPassword, Onboarding, Profile).
 * Keep messages short and student-friendly.
 */

export const DEGREE_OPTIONS = ["B.Tech", "B.E.", "B.Sc", "BCA", "M.Tech", "M.Sc", "MCA", "Other"];

/** Returns "" when the password is valid, otherwise a friendly message. */
export function passwordProblem(pw) {
  const p = pw || "";
  if (p.length < 8) return "Password must be at least 8 characters long.";
  if (!/[A-Z]/.test(p)) return "Password must include at least 1 uppercase letter (A-Z).";
  if (!/[^A-Za-z0-9]/.test(p)) return "Password must include at least 1 special character (e.g. @ # $ % !).";
  return "";
}

/** True when the string is empty, or a number between 0 and 10 (decimals allowed). */
export function cgpaIsValid(v) {
  if (v === "" || v === null || v === undefined) return true; // optional field
  const n = Number(v);
  return Number.isFinite(n) && n >= 0 && n <= 10;
}

/** CGPA must be a plain number (digits + optional decimal point) while typing. */
export function cgpaKeyAllowed(e) {
  return ["Backspace", "Delete", "Tab", "ArrowLeft", "ArrowRight", "Home", "End"].includes(e.key) ||
    /^[0-9.]$/.test(e.key);
}
