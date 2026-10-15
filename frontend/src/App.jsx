import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import { useAuth } from "./context/AuthContext.jsx";
import { PageLoader } from "./components/ui.jsx";
import Login from "./pages/Login.jsx";
import Signup from "./pages/Signup.jsx";
import ForgotPassword from "./pages/ForgotPassword.jsx";
import Onboarding from "./pages/Onboarding.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import ResumeAnalysis from "./pages/ResumeAnalysis.jsx";
import Careers from "./pages/Careers.jsx";
import Roadmap from "./pages/Roadmap.jsx";
import Profile from "./pages/Profile.jsx";
import InterviewPrep from "./pages/InterviewPrep.jsx";
import MockInterview from "./pages/MockInterview.jsx";
import SpeechPractice from "./pages/SpeechPractice.jsx";
import Analytics from "./pages/Analytics.jsx";
import Placement from "./pages/Placement.jsx";

function Protected({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <PageLoader label="Setting things up…" />;
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />;
  if (!user.onboarded && location.pathname !== "/onboarding") {
    return <Navigate to="/onboarding" replace />;
  }
  return children;
}

function PublicOnly({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <PageLoader label="Checking your session…" />;
  if (user) return <Navigate to={user.onboarded ? "/dashboard" : "/onboarding"} replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<PublicOnly><Login /></PublicOnly>} />
      <Route path="/signup" element={<PublicOnly><Signup /></PublicOnly>} />
      <Route path="/forgot-password" element={<PublicOnly><ForgotPassword /></PublicOnly>} />
      <Route path="/onboarding" element={<Protected><Onboarding /></Protected>} />
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="/dashboard" element={<Protected><Layout><Dashboard /></Layout></Protected>} />
      <Route path="/resume" element={<Protected><Layout><ResumeAnalysis /></Layout></Protected>} />
      <Route path="/careers" element={<Protected><Layout><Careers /></Layout></Protected>} />
      <Route path="/roadmap" element={<Protected><Layout><Roadmap /></Layout></Protected>} />
      <Route path="/interview-prep" element={<Protected><Layout><InterviewPrep /></Layout></Protected>} />
      <Route path="/mock-interview" element={<Protected><Layout><MockInterview /></Layout></Protected>} />
      <Route path="/speech" element={<Protected><Layout><SpeechPractice /></Layout></Protected>} />
      <Route path="/analytics" element={<Protected><Layout><Analytics /></Layout></Protected>} />
      <Route path="/placement" element={<Protected><Layout><Placement /></Layout></Protected>} />
      <Route path="/profile" element={<Protected><Layout><Profile /></Layout></Protected>} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
