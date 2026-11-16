import { useCallback, useEffect, useRef, useState } from "react";
import { api, hasToken, setSession, userName, userRole } from "./api.js";
import { enrichTasks } from "./format.js";
import Admin from "./pages/Admin.jsx";
import FieldApp from "./pages/field/FieldApp.jsx";
import Login from "./pages/Login.jsx";
import Overview from "./pages/Overview.jsx";
import Points from "./pages/Points.jsx";
import Inspections from "./pages/Inspections.jsx";

const VIEWS = [
  { id: "overview", label: "Overview" },
  { id: "points", label: "Compliance points" },
  { id: "inspections", label: "Inspections" },
  { id: "admin", label: "Admin", adminOnly: true },   // users, departments and locations
];

// The tabs this user may open: the Admin tab is only for the admin account.
const viewsFor = () => VIEWS.filter((v) => !v.adminOnly || userRole() === "admin");

const NO_FILTER = { status: "review", dept: "", station: "", q: "" };

function viewFromHash() {
  const id = window.location.hash.replace("#/", "");
  return viewsFor().some((v) => v.id === id) ? id : "overview";
}

export default function App() {
  const [loggedIn, setLoggedIn] = useState(hasToken());
  const logout = useCallback(() => {
    setSession("");
    window.history.replaceState(null, "", window.location.pathname); // next sign-in starts on the first screen
    setLoggedIn(false);
  }, []);

  if (!loggedIn) return <Login onLogin={() => setLoggedIn(true)} />;
  // One app, three kinds of user: the role from the login decides which screens open.
  const role = userRole();
  if (role === "officer" || role === "staff") return <FieldApp role={role} onLogout={logout} />;
  return <Shell onLogout={logout} />;
}

function Shell({ onLogout }) {
  const [view, setView] = useState(viewFromHash);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");
  const toastTimer = useRef(null);

  // Which points and which inspection are showing. Kept here so the overview can link into them.
  const [pointsFilter, setPointsFilter] = useState(NO_FILTER);
  const [pointId, setPointId] = useState(null);
  const [inspectionId, setInspectionId] = useState(null);

  const load = useCallback(async () => {
    try {
      const [summary, tasks, inspections] = await Promise.all([
        api("/dashboard/summary"),
        api("/tasks"),
        api("/inspections"),
      ]);
      setData({ summary, inspections, tasks: enrichTasks(tasks, inspections) });
      setError("");
    } catch (err) {
      if (!hasToken()) onLogout(); // session ended: back to the sign-in page
      else setError(err.message);
    }
  }, [onLogout]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const onHash = () => setView(viewFromHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  function go(id) {
    window.location.hash = `#/${id}`;
    setView(id);
    window.scrollTo(0, 0);
  }

  function openPoints({ selectId = null, ...filter } = {}) {
    setPointsFilter({ ...NO_FILTER, status: "all", ...filter });
    setPointId(selectId);
    go("points");
  }

  function openInspection(id = null) {
    setInspectionId(id);
    go("inspections");
  }

  function notify(message) {
    setToast(message);
    clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(""), 4500);
  }

  const toReview = data ? data.tasks.filter((t) => t.status === "fix_submitted").length : 0;

  return (
    // On the two list + detail pages the page itself does not scroll: the list and the detail scroll
    // side by side, so the Accept / Reject buttons are always in view.
    <div className={`app${view === "overview" ? "" : " app-fixed"}`}>
      <header className="topbar">
        <button type="button" className="board" onClick={() => go("overview")} aria-label="RailNirikshan, go to overview">
          <span lang="hi">रेल निरीक्षण</span>
          <span>RailNirikshan</span>
        </button>
        <nav className="nav" aria-label="Sections">
          {viewsFor().map((v) => (
            <button key={v.id} type="button" className={`nav-item${view === v.id ? " is-active" : ""}`}
                    aria-current={view === v.id ? "page" : undefined} onClick={() => go(v.id)}>
              {v.label}
              {v.id === "points" && toReview > 0 && (
                <span className="nav-count" title={`${toReview} waiting for review`}>{toReview}</span>
              )}
            </button>
          ))}
        </nav>
        <div className="who">
          <span className="who-name">{userName() || (userRole() === "admin" ? "Administrator" : "Senior officer")}</span>
          <button type="button" className="btn btn-onnavy" onClick={onLogout}>
            Log out
          </button>
        </div>
      </header>

      <main className="page">
        {error && (
          <div className="notice" role="alert">
            <span>{error}</span>
            <button type="button" className="btn btn-quiet" onClick={load}>
              Try again
            </button>
          </div>
        )}
        {!data && !error && <p className="loading">Loading inspections and points</p>}
        {data && view === "overview" && (
          <Overview data={data} openPoints={openPoints} openInspection={openInspection}
                    onChanged={load} notify={notify} />
        )}
        {data && view === "points" && (
          <Points tasks={data.tasks} filter={pointsFilter} setFilter={setPointsFilter}
                  selectedId={pointId} setSelectedId={setPointId}
                  onChanged={load} openInspection={openInspection} notify={notify} />
        )}
        {data && view === "inspections" && (
          <Inspections inspections={data.inspections} tasks={data.tasks}
                       selectedId={inspectionId} setSelectedId={setInspectionId} openPoints={openPoints} />
        )}
        {view === "admin" && <Admin notify={notify} onChanged={load} />}
      </main>

      <div className={`toast${toast ? " is-shown" : ""}`} role="status" aria-live="polite">
        {toast}
      </div>
    </div>
  );
}
