import { useState } from "react";
import { api, setSession } from "../api.js";

export default function Login({ onLogin }) {
  const [username, setUsername] = useState("senior");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const res = await api("/auth/login", { method: "POST", body: { username, password } });
      // The role decides which screens open: senior/admin get the dashboard, officers and staff the field screens.
      setSession(res.access_token, res.full_name, res.role);
      onLogin();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login">
      <div className="login-inner">
        {/* The brand is drawn like a platform station board: Hindi first, then English. */}
        <div className="signboard" aria-hidden="true">
          <div className="signboard-face">
            <span lang="hi">रेल निरीक्षण</span>
            <span>RailNirikshan</span>
            <small>North Western Railway</small>
          </div>
          <div className="signboard-posts" />
        </div>

        <form onSubmit={submit} className="login-card">
          <h1>Sign in</h1>
          <p className="login-sub">Track every inspection point until it is fixed.</p>
          <label className="field">
            <span>Username</span>
            <input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" />
          </label>
          <label className="field">
            <span>Password</span>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                   autoComplete="current-password" autoFocus />
          </label>
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <button className="btn btn-primary btn-wide" disabled={busy}>
            {busy ? "Signing in" : "Sign in"}
          </button>
          <p className="login-hint">
            Demo accounts, password demo123:
            <br />
            senior (dashboard), officer (inspections), staff_elec (department tasks)
          </p>
        </form>
      </div>
      <div className="login-track" aria-hidden="true" />
    </div>
  );
}
