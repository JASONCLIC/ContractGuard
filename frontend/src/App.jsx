import { useEffect } from "react";
import { NavLink, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";

import client from "./api/client";
import useAuthStore from "./store/useAuthStore";
import PortalPage from "./pages/PortalPage";
import HomePage from "./pages/HomePage";
import LoginPage from "./pages/LoginPage";
import AnalysisPage from "./pages/AnalysisPage";
import AnalysisLoadingPage from "./pages/AnalysisLoadingPage";
import TemplatePage from "./pages/TemplatePage";
import SharePage from "./pages/SharePage";
import GamePage from "./pages/GamePage";
import AdvancedGamePage from "./pages/AdvancedGamePage";
import SharedViewPage from "./pages/SharedViewPage";
import AdminPage from "./pages/AdminPage";

const NAV_LINKS = [
  { to: "/analysis",  label: "Analysis" },
  { to: "/templates", label: "Templates" },
  { to: "/share",     label: "Share" },
  { to: "/game",      label: "Risk Quiz" },
];

export default function App() {
  const user = useAuthStore((s) => s.user);
  const setUser = useAuthStore((s) => s.setUser);
  const clearUser = useAuthStore((s) => s.logout);
  const navigate = useNavigate();
  const location = useLocation();
  const hideNav = location.pathname === "/login" || location.pathname.startsWith("/admin");

  useEffect(() => {
    client
      .get("/auth/me")
      .then(({ data }) => setUser(data.data))
      .catch(() => clearUser());
  }, [setUser, clearUser]);

  const logout = async () => {
    await client.post("/auth/logout");
    clearUser();
    navigate("/login");
  };

  return (
    <div>
      {/* ── Frosted-glass navigation ── */}
      {!hideNav && <nav className="nav" style={{ display: hideNav ? "none" : undefined }}>
        <div className="nav-inner">
          <NavLink to="/" className="nav-logo">
            <img src="/logo.png" alt="ContractGuard" style={{ width: 36, height: 36, borderRadius: 9, objectFit: "contain" }} />
            <span>ContractGuard</span>
          </NavLink>

          <div className="nav-links">
            {NAV_LINKS.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
              >
                {label}
              </NavLink>
            ))}
          </div>

          <div className="nav-user">
            {user ? (
              <>
                {/* 圆形头像：取用户名首字 */}
                <div className="nav-avatar">
                  {(user.name || "U").charAt(0).toUpperCase()}
                </div>
                <button className="btn btn-text" onClick={logout} style={{ fontSize: 13 }}>
                  Sign Out
                </button>
              </>
            ) : (
              <NavLink to="/login" className="btn btn-primary sm">
                Sign In
              </NavLink>
            )}
          </div>
        </div>
      </nav>}

      {/* ── Routes ── */}
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            user
              ? (user.is_admin ? <Navigate to="/admin" replace /> : <PortalPage />)
              : <Navigate to="/login" replace />
          }
        />
        <Route
          path="/analysis"
          element={user ? <HomePage /> : <Navigate to="/login" replace />}
        />
        <Route
          path="/analysis/loading"
          element={user ? <AnalysisLoadingPage /> : <Navigate to="/login" replace />}
        />
        <Route
          path="/analysis/result"
          element={user ? <AnalysisPage /> : <Navigate to="/login" replace />}
        />
        <Route
          path="/templates"
          element={user ? <TemplatePage /> : <Navigate to="/login" replace />}
        />
        <Route
          path="/share"
          element={user ? <SharePage /> : <Navigate to="/login" replace />}
        />
        <Route
          path="/game"
          element={user ? <GamePage /> : <Navigate to="/login" replace />}
        />
        <Route
          path="/advanced"
          element={user ? <AdvancedGamePage /> : <Navigate to="/login" replace />}
        />
        <Route
          path="/admin"
          element={user?.is_admin ? <AdminPage /> : <Navigate to="/" replace />}
        />
        <Route path="/shared/:token" element={<SharedViewPage />} />
      </Routes>
    </div>
  );
}
