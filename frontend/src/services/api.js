/**
 * API service layer — every backend call goes through here.
 * Adds the JWT header, unwraps friendly error messages, handles 401 globally.
 */
const BASE_URL = import.meta.env.VITE_API_URL || "/api";

const TOKEN_KEY = "cb_token";

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

async function request(path, { method = "GET", body, isForm = false, auth = true, headers = {} } = {}) {
  const opts = { method, headers: { ...headers } };
  if (auth && tokenStore.get()) {
    opts.headers.Authorization = `Bearer ${tokenStore.get()}`;
  }
  if (body !== undefined) {
    if (isForm) {
      opts.body = body; // FormData
    } else {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
  }

  let res;
  try {
    res = await fetch(`${BASE_URL}${path}`, opts);
  } catch {
    throw new Error("Can't reach the server. Check that the backend is running.");
  }

  if (res.status === 401 && auth) {
    tokenStore.clear();
    if (!window.location.pathname.startsWith("/login")) {
      window.location.assign("/login?expired=1");
    }
    throw new Error("Your session expired. Please log in again.");
  }

  let data = null;
  const text = await res.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = null;
    }
  }

  if (!res.ok) {
    const msg = (data && data.detail) || `Request failed (${res.status})`;
    throw new Error(typeof msg === "string" ? msg : "Something went wrong. Please try again.");
  }
  return data;
}

export const api = {
  // auth
  signup: (payload) => request("/auth/signup", { method: "POST", body: payload, auth: false }),
  login: (payload) => request("/auth/login", { method: "POST", body: payload, auth: false }),
  forgotPassword: (email) => request("/auth/forgot-password", { method: "POST", body: { email }, auth: false }),
  resetPassword: (payload) => request("/auth/reset-password", { method: "POST", body: payload, auth: false }),

  // users / profile
  me: () => request("/users/me"),
  updateMe: (payload) => request("/users/me", { method: "PUT", body: payload }),
  completion: () => request("/users/me/completion"),

  // resume
  analyzeResume: (file, onProgress) =>
    new Promise((resolve, reject) => {
      const form = new FormData();
      form.append("file", file);
      const xhr = new XMLHttpRequest();
      xhr.open("POST", `${BASE_URL}/resumes/analyze`);
      const token = tokenStore.get();
      if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable && onProgress) onProgress(Math.round((e.loaded / e.total) * 100));
      };
      xhr.onload = () => {
        try {
          const data = JSON.parse(xhr.responseText || "{}");
          if (xhr.status >= 200 && xhr.status < 300) resolve(data);
          else reject(new Error(data.detail || "Analysis failed. Please try again."));
        } catch {
          reject(new Error("Analysis failed. Please try again."));
        }
      };
      xhr.onerror = () => reject(new Error("Can't reach the server. Check that the backend is running."));
      xhr.send(form);
    }),
  latestResume: () => request("/resumes/latest"),
  resumeHistory: () => request("/resumes/history"),

  // careers
  careerRecommendations: () => request("/careers/recommend"),
  roadmapCareers: () => request("/roadmap/careers"),

  // roadmap (displayed as "Planner" in the UI)
  getRoadmap: (career) => request(`/roadmap/${encodeURIComponent(career)}`),
  roadmapLevels: (career) => request(`/roadmap/${encodeURIComponent(career)}/levels`), // game-style level path
  toggleRoadmapTask: (career, taskId) => request(`/roadmap/${encodeURIComponent(career)}/tasks/${taskId}`, { method: "POST" }),
  resetRoadmap: (career) => request(`/roadmap/${encodeURIComponent(career)}`, { method: "DELETE" }),

  // dashboard
  dashboard: () => request("/dashboard"),

  // module 6 — technical prep
  prepNext: () => request("/interview/prep/next"),
  prepAnswer: (questionId, answer) =>
    request(`/interview/prep/answer?question_id=${encodeURIComponent(questionId)}`, {
      method: "POST", body: { answer },
    }),
  prepHistory: () => request("/interview/prep/history"),
  prepStats: () => request("/interview/prep/stats"),

  // module 7 — mock interview
  startSession: (payload) => request("/interview/sessions", { method: "POST", body: payload }),
  getSession: (id) => request(`/interview/sessions/${id}`),
  answerSession: (id, payload) => request(`/interview/sessions/${id}/answer`, { method: "POST", body: payload }),
  finishSession: (id) => request(`/interview/sessions/${id}/finish`, { method: "POST" }),
  sessionHistory: () => request("/interview/sessions"),

  // module 8 — speech
  analyzeSpeech: (payload) => request("/speech/analyze", { method: "POST", body: payload }),
  speechHistory: () => request("/speech/history"),
  speechParagraph: () => request("/speech/paragraph"), // fresh interview paragraph each call
  transcribeStatus: () => request("/speech/transcribe-status"),
  transcribeAudio: (blob) => {
    const form = new FormData();
    form.append("audio", blob, "answer.webm");
    return request("/speech/transcribe", { method: "POST", body: form, isForm: true });
  },

  // module 9 — analytics
  analytics: () => request("/analytics"),
  progress: () => request("/analytics/progress"), // single source of truth for module %

  // module 10 — placement
  placement: () => request("/placement"),
  placementPlan: () => request("/placement/plan"),
  generatePlan: () => request("/placement/plan/generate", { method: "POST" }),
  setPlanTaskStatus: (taskId, status) =>
    request(`/placement/plan/tasks/${taskId}`, { method: "PATCH", body: { status } }),
};

export function getErrorMessage(err) {
  return err?.message || "Something went wrong. Please try again.";
}
