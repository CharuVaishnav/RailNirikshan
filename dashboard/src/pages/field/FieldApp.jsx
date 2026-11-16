// Field screens for inspecting officers and department staff.
// They are laid out as one narrow column, so they work on a phone and look like a phone app on a laptop.
import { useEffect, useRef, useState } from "react";
import { api, hasToken, userName } from "../../api.js";
import Officer from "./Officer.jsx";
import Staff from "./Staff.jsx";

export default function FieldApp({ role, onLogout }) {
  const [me, setMe] = useState(null);
  const [toast, setToast] = useState("");
  const [home, setHome] = useState(0); // changing this number sends the screens back to their first page
  const toastTimer = useRef(null);

  useEffect(() => {
    api("/auth/me")
      .then(setMe)
      .catch(() => {
        if (!hasToken()) onLogout();
      });
  }, [onLogout]);

  function notify(message) {
    setToast(message);
    clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(""), 4500);
  }

  // If the session has ended, any failed request sends the user back to the sign-in page.
  function onError(err) {
    if (!hasToken()) onLogout();
    return err.message;
  }

  const roleLine = role === "officer" ? "Inspecting officer" : me?.department ? `${me.department.name} staff` : "Department staff";

  return (
    <div className="app">
      <header className="topbar">
        <button type="button" className="board" onClick={() => setHome((n) => n + 1)} aria-label="RailNirikshan, go to the first screen">
          <span lang="hi">रेल निरीक्षण</span>
          <span>RailNirikshan</span>
        </button>
        <div className="who">
          <span className="who-id">
            <strong>{userName()}</strong>
            <span>{roleLine}</span>
          </span>
          <button type="button" className="btn btn-onnavy" onClick={onLogout}>
            Log out
          </button>
        </div>
      </header>

      <main className="field-page">
        {role === "officer" ? (
          <Officer key={home} notify={notify} onError={onError} />
        ) : (
          <Staff key={home} me={me} notify={notify} onError={onError} />
        )}
      </main>

      <div className={`toast${toast ? " is-shown" : ""}`} role="status" aria-live="polite">
        {toast}
      </div>
    </div>
  );
}
