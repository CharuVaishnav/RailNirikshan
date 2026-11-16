// Admin screens: users, departments and locations. Only the admin account sees this page.
// Each tab is a list on the left and a form on the right, the same pattern as the other pages.
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { Empty, Status } from "../components/ui.jsx";
import { plural } from "../format.js";

const ROLE = {
  officer: "Inspecting officer",
  staff: "Department staff",
  senior: "Senior officer",
  admin: "Administrator",
};
const KIND = { station: "Station", lc_gate: "Level crossing gate", depot: "Depot", office: "Office" };

const NEW_USER = { username: "", password: "", full_name: "", designation: "", email: "", role: "staff", department_id: "", is_active: true };
const NEW_DEPARTMENT = { code: "", name: "" };
const NEW_LOCATION = { name: "", kind: "station", division: "", latitude: "", longitude: "" };

const isWide = () => window.matchMedia("(min-width: 1000px)").matches;

export default function Admin({ notify, onChanged }) {
  const [tab, setTab] = useState("users");
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState(null); // an id, "new", or null

  const load = useCallback(async () => {
    try {
      const [users, departments, locations] = await Promise.all([
        api("/admin/users"), api("/departments"), api("/locations"),
      ]);
      setData({ users, departments, locations });
      setError("");
    } catch (err) {
      setError(err.message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const detailRef = useRef(null);
  useEffect(() => {
    detailRef.current?.scrollTo(0, 0);
    if (!isWide() && selected != null) window.scrollTo(0, 0); // on a phone the form replaces the list
  }, [selected, tab]);

  if (error && !data) return <div className="notice" role="alert"><span>{error}</span></div>;
  if (!data) return <p className="loading">Loading users, departments and locations</p>;

  const TABS = [
    { id: "users", label: "Users", rows: data.users, add: "Add user" },
    { id: "departments", label: "Departments", rows: data.departments, add: "Add department" },
    { id: "locations", label: "Locations", rows: data.locations, add: "Add location" },
  ];
  const current = TABS.find((t) => t.id === tab);
  const item = selected === "new" ? null : current.rows.find((r) => r.id === selected) || null;
  const showForm = selected === "new" || item;

  // After a save or delete: reload the lists here and the dashboard data behind the other tabs.
  async function done(message, nextSelected) {
    notify(message);
    setSelected(nextSelected);
    await load();
    onChanged();
  }

  const staffCount = (deptId) => data.users.filter((u) => u.department?.id === deptId && u.is_active).length;

  return (
    <div className="stack">
      <div className="page-head">
        <h1>Administration</h1>
        <p>The people who use RailNirikshan, the departments points are sent to, and the places that are inspected.</p>
      </div>

      <div className="toolbar">
        <div className="tabs" role="tablist" aria-label="What to manage">
          {TABS.map((t) => (
            <button key={t.id} type="button" role="tab" aria-selected={tab === t.id}
                    className={`tab${tab === t.id ? " is-active" : ""}`}
                    onClick={() => { setTab(t.id); setSelected(null); }}>
              {t.label}
              <span className="tab-count">{t.rows.length}</span>
            </button>
          ))}
        </div>
        <button type="button" className="btn btn-primary" onClick={() => setSelected("new")}>
          {current.add}
        </button>
      </div>

      <div className={`split${showForm ? " has-selection" : ""}`}>
        <section className="panel list-panel" aria-label={current.label}>
          <div className="rows">
            {tab === "users" && data.users.map((u) => (
              <Row key={u.id} selected={u.id === selected} onClick={() => setSelected(u.id)}
                   title={u.full_name}
                   meta={<><span className="row-id">{u.username}</span><span>{ROLE[u.role] || u.role}</span>
                     {u.department && <span className="tag">{u.department.name}</span>}</>}
                   side={<Status tone={u.is_active ? "clear" : "idle"}>{u.is_active ? "Active" : "Switched off"}</Status>} />
            ))}
            {tab === "departments" && data.departments.map((d) => (
              <Row key={d.id} selected={d.id === selected} onClick={() => setSelected(d.id)}
                   title={d.name} meta={<span className="row-id">{d.code}</span>}
                   side={<span className="due">{plural(staffCount(d.id), "staff user")}</span>} />
            ))}
            {tab === "locations" && data.locations.map((l) => (
              <Row key={l.id} selected={l.id === selected} onClick={() => setSelected(l.id)}
                   title={l.name} meta={<><span>{KIND[l.kind] || l.kind}</span><span>{l.division} division</span></>}
                   side={<span className="due">{l.latitude.toFixed(3)}, {l.longitude.toFixed(3)}</span>} />
            ))}
          </div>
        </section>

        <section className="panel detail" aria-label="Details" ref={detailRef}>
          {!showForm ? (
            <Empty title={`Select one of the ${current.label.toLowerCase()}`}>
              Or use {current.add} to make a new one.
            </Empty>
          ) : tab === "users" ? (
            <UserForm key={selected} user={item} departments={data.departments} done={done} onBack={() => setSelected(null)} />
          ) : tab === "departments" ? (
            <DepartmentForm key={selected} department={item} done={done} onBack={() => setSelected(null)} />
          ) : (
            <LocationForm key={selected} location={item} done={done} onBack={() => setSelected(null)} />
          )}
        </section>
      </div>
    </div>
  );
}

function Row({ title, meta, side, selected, onClick }) {
  return (
    <button type="button" className={`row${selected ? " is-selected" : ""}`} onClick={onClick}
            aria-current={selected ? "true" : undefined}>
      <span className="row-main">
        <span className="row-title">{title}</span>
        <span className="row-meta">{meta}</span>
      </span>
      <span className="row-side">{side}</span>
    </button>
  );
}

// The frame every form shares: heading, the fields, the error line and the buttons at the bottom.
function FormFrame({ title, sub, onBack, onSubmit, busy, error, saveLabel, onDelete, deleteLabel, children }) {
  const [confirming, setConfirming] = useState(false);
  return (
    <form className="detail-body" onSubmit={(e) => { e.preventDefault(); onSubmit(); }}>
      <button type="button" className="btn btn-quiet detail-back" onClick={onBack}>Back to list</button>
      <div>
        <h2 className="admin-title">{title}</h2>
        {sub && <p className="quiet">{sub}</p>}
      </div>
      <div className="admin-fields">{children}</div>
      <div className="actionbar">
        {error && <p className="form-error" role="alert">{error}</p>}
        {confirming ? (
          <div className="actionbar-buttons">
            <button type="button" className="btn btn-danger" disabled={busy} onClick={onDelete}>Yes, delete</button>
            <button type="button" className="btn btn-plain" disabled={busy} onClick={() => setConfirming(false)}>Cancel</button>
            <span className="actionbar-note">This cannot be undone.</span>
          </div>
        ) : (
          <div className="actionbar-buttons">
            <button type="submit" className="btn btn-primary" disabled={busy}>{busy ? "Saving" : saveLabel}</button>
            {onDelete && (
              <button type="button" className="btn btn-plain" disabled={busy} onClick={() => setConfirming(true)}>
                {deleteLabel}
              </button>
            )}
          </div>
        )}
      </div>
    </form>
  );
}

function Field({ label, hint, wide, children }) {
  return (
    <label className={`field${wide ? " admin-wide" : ""}`}>
      <span>{label}</span>
      {children}
      {hint && <span className="admin-hint">{hint}</span>}
    </label>
  );
}

// Shared by the three forms: the values, a setter for one field, and a save / delete that shows errors.
function useForm(initial) {
  const [values, setValues] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const set = (name) => (e) => setValues((v) => ({ ...v, [name]: e.target.type === "checkbox" ? e.target.checked : e.target.value }));
  async function run(work) {
    setBusy(true);
    setError("");
    try {
      await work();
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }
  return { values, set, busy, error, run };
}

function UserForm({ user, departments, done, onBack }) {
  const f = useForm(user
    ? { ...NEW_USER, ...user, email: user.email || "", department_id: user.department?.id ?? "", password: "" }
    : NEW_USER);
  const v = f.values;
  const isStaff = v.role === "staff";

  const save = () => f.run(async () => {
    const body = {
      full_name: v.full_name, designation: v.designation, email: v.email, role: v.role,
      department_id: isStaff && v.department_id !== "" ? Number(v.department_id) : null,
    };
    if (user) {
      await api(`/admin/users/${user.id}`, { method: "PUT", body: { ...body, is_active: v.is_active, password: v.password } });
      await done(`${v.full_name} saved.`, user.id);
    } else {
      const made = await api("/admin/users", { method: "POST", body: { ...body, username: v.username, password: v.password } });
      await done(`${made.full_name} added. They can sign in as ${made.username}.`, made.id);
    }
  });

  return (
    <FormFrame title={user ? user.full_name : "New user"} onBack={onBack} onSubmit={save} busy={f.busy} error={f.error}
               sub={user ? `Signs in as ${user.username}` : "The person signs in with the username and password you set here."}
               saveLabel={user ? "Save changes" : "Add user"}>
      {!user && (
        <Field label="Username" hint="Small letters, digits, _ or . It cannot be changed later.">
          <input value={v.username} onChange={f.set("username")} required autoFocus autoCapitalize="none" autoComplete="off" />
        </Field>
      )}
      <Field label="Full name">
        <input value={v.full_name} onChange={f.set("full_name")} required />
      </Field>
      <Field label="Designation">
        <input value={v.designation} onChange={f.set("designation")} placeholder="For example: Supervisor" />
      </Field>
      <Field label="Role">
        <select value={v.role} onChange={f.set("role")}>
          {Object.entries(ROLE).map(([id, label]) => <option key={id} value={id}>{label}</option>)}
        </select>
      </Field>
      {isStaff && (
        <Field label="Department" hint="Staff see only the points of their own department.">
          <select value={v.department_id} onChange={f.set("department_id")} required>
            <option value="">Choose a department</option>
            {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
        </Field>
      )}
      <Field label="Email (optional)" hint="Overdue reminders are sent here.">
        <input type="email" value={v.email} onChange={f.set("email")} autoComplete="off" />
      </Field>
      <Field label={user ? "New password" : "Password"}
             hint={user ? "Leave empty to keep the current password." : "At least 6 characters."}>
        <input type="password" value={v.password} onChange={f.set("password")} required={!user} minLength={6}
               autoComplete="new-password" />
      </Field>
      {user && (
        <label className="check-row admin-wide">
          <input type="checkbox" checked={v.is_active} onChange={f.set("is_active")} />
          <span className="check-label">This account can sign in</span>
          <span className="check-state">{v.is_active ? "Active" : "Switched off"}</span>
        </label>
      )}
    </FormFrame>
  );
}

function DepartmentForm({ department, done, onBack }) {
  const f = useForm(department || NEW_DEPARTMENT);
  const v = f.values;

  const save = () => f.run(async () => {
    if (department) {
      await api(`/admin/departments/${department.id}`, { method: "PUT", body: { name: v.name } });
      await done(`${v.name} saved.`, department.id);
    } else {
      const made = await api("/admin/departments", { method: "POST", body: { code: v.code, name: v.name } });
      await done(`${made.name} added.`, made.id);
    }
  });
  const remove = () => f.run(async () => {
    await api(`/admin/departments/${department.id}`, { method: "DELETE" });
    await done(`${department.name} deleted.`, null);
  });

  return (
    <FormFrame title={department ? department.name : "New department"} onBack={onBack} onSubmit={save}
               busy={f.busy} error={f.error} saveLabel={department ? "Save changes" : "Add department"}
               sub={department ? `Code ${department.code}` : "Inspection points are sent to a department, and its staff fix them."}
               onDelete={department ? remove : null} deleteLabel="Delete department">
      {!department && (
        <Field label="Code" hint="A short code in capitals, for example OPTG. It cannot be changed later.">
          <input value={v.code} onChange={f.set("code")} required autoFocus autoCapitalize="characters" />
        </Field>
      )}
      <Field label="Name" wide={Boolean(department)}>
        <input value={v.name} onChange={f.set("name")} required />
      </Field>
      {!department && (
        <p className="quiet admin-wide">
          The AI suggests only the seven original departments. For a new one the officer picks the department by hand.
        </p>
      )}
    </FormFrame>
  );
}

function LocationForm({ location, done, onBack }) {
  const f = useForm(location || NEW_LOCATION);
  const v = f.values;

  const body = () => ({
    name: v.name, kind: v.kind, division: v.division, latitude: Number(v.latitude), longitude: Number(v.longitude),
  });
  const save = () => f.run(async () => {
    if (location) {
      await api(`/admin/locations/${location.id}`, { method: "PUT", body: body() });
      await done(`${v.name} saved.`, location.id);
    } else {
      const made = await api("/admin/locations", { method: "POST", body: body() });
      await done(`${made.name} added.`, made.id);
    }
  });
  const remove = () => f.run(async () => {
    await api(`/admin/locations/${location.id}`, { method: "DELETE" });
    await done(`${location.name} deleted.`, null);
  });

  return (
    <FormFrame title={location ? location.name : "New location"} onBack={onBack} onSubmit={save}
               busy={f.busy} error={f.error} saveLabel={location ? "Save changes" : "Add location"}
               sub="A place that officers inspect. Its position puts it on the dashboard map."
               onDelete={location ? remove : null} deleteLabel="Delete location">
      <Field label="Name" wide>
        <input value={v.name} onChange={f.set("name")} required autoFocus={!location} placeholder="For example: Kota Junction" />
      </Field>
      <Field label="Type">
        <select value={v.kind} onChange={f.set("kind")}>
          {Object.entries(KIND).map(([id, label]) => <option key={id} value={id}>{label}</option>)}
        </select>
      </Field>
      <Field label="Division">
        <input value={v.division} onChange={f.set("division")} required placeholder="For example: Jaipur" />
      </Field>
      <Field label="Latitude" hint="Between -90 and 90. Jaipur is about 26.92.">
        <input type="number" step="any" min="-90" max="90" value={v.latitude} onChange={f.set("latitude")} required />
      </Field>
      <Field label="Longitude" hint="Between -180 and 180. Jaipur is about 75.79.">
        <input type="number" step="any" min="-180" max="180" value={v.longitude} onChange={f.set("longitude")} required />
      </Field>
    </FormFrame>
  );
}
