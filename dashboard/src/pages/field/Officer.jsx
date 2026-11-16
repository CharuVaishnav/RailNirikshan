// Inspecting officer: my inspections -> new inspection (checklist) -> observations with photo and GPS
// -> AI department suggestion -> AI-drafted note -> approve.
import { useEffect, useState } from "react";
import { api, apiForm } from "../../api.js";
import { CHECKLISTS, checklistResult } from "../../checklists/index.js";
import { ChecklistSummary, Empty, Photo, Status, TaskStatus } from "../../components/ui.jsx";
import { usePosition } from "../../device.js";
import { INSPECTION_TYPE, deadlineInfo, fmtDate, inspectionTitle, plural } from "../../format.js";
import { Meter, NoteSheet, progress } from "../Inspections.jsx";
import { GpsLine, PhotoPicker, ScreenHead } from "./parts.jsx";

export default function Officer({ notify, onError }) {
  const [screen, setScreen] = useState({ name: "home" });

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [screen]);

  if (screen.name === "new") {
    return <NewInspection onBack={() => setScreen({ name: "home" })} onError={onError}
                          onCreated={(id) => setScreen({ name: "inspection", id })} />;
  }
  if (screen.name === "inspection") {
    return <InspectionScreen id={screen.id} onBack={() => setScreen({ name: "home" })} notify={notify} onError={onError} />;
  }
  return <Home onNew={() => setScreen({ name: "new" })} onError={onError}
               onOpen={(id) => setScreen({ name: "inspection", id })} />;
}

function Home({ onNew, onOpen, onError }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api("/inspections"), api("/tasks")])
      .then(([inspections, tasks]) =>
        setData({ inspections, taskByObservation: new Map(tasks.map((t) => [t.observation.id, t])) }))
      .catch((err) => setError(onError(err)));
  }, []);

  return (
    <>
      <ScreenHead title="My inspections" sub="Record what you see. Points go to departments after you approve the note." />
      <button type="button" className="btn btn-primary btn-wide" onClick={onNew}>
        New inspection
      </button>
      {error && <p className="notice" role="alert">{error}</p>}
      {!data && !error && <p className="loading">Loading your inspections</p>}
      {data && (
        <section className="panel">
          {data.inspections.length === 0 ? (
            <Empty title="No inspections yet">Start with New inspection.</Empty>
          ) : (
            <div className="rows">
              {data.inspections.map((insp) => {
                const p = progress(insp, data.taskByObservation);
                return (
                  <button type="button" key={insp.id} className="row" onClick={() => onOpen(insp.id)}>
                    <span className="row-main">
                      <span className="row-title">{insp.location.name}</span>
                      <span className="row-meta">
                        <span>{inspectionTitle(insp)}</span>
                        <span>{fmtDate(insp.created_at)}</span>
                      </span>
                    </span>
                    <span className="row-side">
                      {insp.status === "approved" ? (
                        <>
                          <Meter p={p} />
                          <span className="due">{p.closed} of {plural(p.total, "point")} closed</span>
                        </>
                      ) : (
                        <>
                          <Status tone="caution">Draft</Status>
                          <span className="due">{plural(insp.observations.length, "point")} so far</span>
                        </>
                      )}
                    </span>
                  </button>
                );
              })}
            </div>
          )}
        </section>
      )}
    </>
  );
}

function NewInspection({ onBack, onCreated, onError }) {
  const [locations, setLocations] = useState([]);
  const [locationId, setLocationId] = useState("");
  const [type, setType] = useState("station");
  const [notOk, setNotOk] = useState(() => new Set());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/locations").then(setLocations).catch((err) => setError(onError(err)));
  }, []);

  const items = CHECKLISTS[type].items;

  function changeType(next) {
    setType(next);
    setNotOk(new Set()); // each inspection type has its own checklist
  }

  function pickLocation(id) {
    setLocationId(id);
    const loc = locations.find((l) => String(l.id) === id);
    if (loc?.kind === "lc_gate" && type !== "lc_gate") changeType("lc_gate");
    if (loc && loc.kind !== "lc_gate" && type === "lc_gate") changeType("station");
  }

  function toggle(id) {
    const next = new Set(notOk);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setNotOk(next);
  }

  async function start(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const checklist = Object.fromEntries(items.map((i) => [i.id, !notOk.has(i.id)]));
      const insp = await api("/inspections", {
        method: "POST",
        body: { location_id: Number(locationId), inspection_type: type, checklist },
      });
      onCreated(insp.id);
    } catch (err) {
      setError(onError(err));
      setBusy(false);
    }
  }

  return (
    <form onSubmit={start} className="field-form">
      <ScreenHead title="New inspection" onBack={onBack} />
      <section className="panel card">
        <label className="field">
          <span>Location</span>
          <select value={locationId} onChange={(e) => pickLocation(e.target.value)} required>
            <option value="" disabled>Choose a station or gate</option>
            {locations.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
          </select>
        </label>
        <label className="field">
          <span>Inspection type</span>
          <select value={type} onChange={(e) => changeType(e.target.value)}>
            {Object.entries(INSPECTION_TYPE).map(([id, label]) => <option key={id} value={id}>{label}</option>)}
          </select>
        </label>
      </section>

      <section className="panel">
        <header className="panel-head">
          <h2>Checklist</h2>
          <p>Everything starts as OK. Untick what is not OK.</p>
        </header>
        {items.map((item) => {
          const ok = !notOk.has(item.id);
          return (
            <label key={item.id} className={`check-row${ok ? "" : " is-bad"}`}>
              <input type="checkbox" checked={ok} onChange={() => toggle(item.id)} />
              <span className="check-label">{item.label}</span>
              <span className="check-state">{ok ? "OK" : "Not OK"}</span>
            </label>
          );
        })}
      </section>

      {error && <p className="form-error" role="alert">{error}</p>}
      <button className="btn btn-primary btn-wide" disabled={busy || !locationId}>
        {busy ? "Starting" : "Start inspection"}
      </button>
    </form>
  );
}

function ObservationForm({ inspectionId, hints, onAdded, onError }) {
  const [text, setText] = useState("");
  const [photo, setPhoto] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const position = usePosition();

  async function add(e) {
    e.preventDefault();
    if (!text.trim()) {
      setError("Write what you observed first.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const obs = await apiForm(`/inspections/${inspectionId}/observations`, {
        text: text.trim(),
        latitude: position.coords?.latitude,
        longitude: position.coords?.longitude,
      }, photo);
      setText("");
      setPhoto(null);
      onAdded(obs);
    } catch (err) {
      setError(onError(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={add} className="panel card">
      <h2>Add an observation</h2>
      {hints.length > 0 && (
        <div className="chips">
          <span>Not OK in the checklist:</span>
          {hints.map((label) => (
            <button type="button" key={label} className="chip" onClick={() => setText(`${label}: not OK. `)}>
              {label}
            </button>
          ))}
        </div>
      )}
      <label className="field">
        <span>What did you observe?</span>
        <textarea rows="3" value={text} onChange={(e) => setText(e.target.value)}
                  placeholder="For example: Two lights not working on platform 3" />
      </label>
      <PhotoPicker file={photo} onChange={setPhoto} label="Add photo" />
      <GpsLine position={position} missingNote="The observation is saved without GPS." />
      {error && <p className="form-error" role="alert">{error}</p>}
      <button className="btn btn-primary btn-wide" disabled={busy}>
        {busy ? "Adding" : "Add observation"}
      </button>
    </form>
  );
}

function InspectionScreen({ id, onBack, notify, onError }) {
  const [insp, setInsp] = useState(null);
  const [departments, setDepartments] = useState([]);
  const [taskByObservation, setTaskByObservation] = useState(new Map());
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  async function load() {
    const [i, tasks] = await Promise.all([api(`/inspections/${id}`), api("/tasks")]);
    setInsp(i);
    setNote(i.note_text || "");
    setTaskByObservation(new Map(tasks.map((t) => [t.observation.id, t])));
  }

  useEffect(() => {
    load().catch((err) => setError(onError(err)));
    api("/departments").then(setDepartments).catch(() => {});
  }, [id]);

  async function run(name, action) {
    setBusy(name);
    setError("");
    try {
      await action();
    } catch (err) {
      setError(onError(err));
    } finally {
      setBusy("");
    }
  }

  if (!insp) {
    return (
      <>
        <ScreenHead title="Inspection" onBack={onBack} />
        {error ? <p className="notice" role="alert">{error}</p> : <p className="loading">Loading the inspection</p>}
      </>
    );
  }

  const draft = insp.status === "draft";
  const observations = insp.observations;
  const hints = checklistResult(insp)?.notOk || [];
  const undecided = observations.filter((o) => !o.suggested_department).length;
  // Any change to the observations makes the note out of date, so the server clears it
  // and the officer generates it again.
  const hadNote = Boolean(insp.note_text);
  const again = hadNote ? " Generate the note again." : "";

  const changeDepartment = (obs, departmentId) => run("department", async () => {
    await api(`/inspections/${id}/observations/${obs.id}/department`, { method: "PUT", body: { department_id: Number(departmentId) } });
    await load();
    if (hadNote) notify("Department changed. Generate the note again.");
  });

  const removeObservation = (obs) => run("remove", async () => {
    if (!window.confirm(`Remove this observation?\n\n${obs.text}`)) return;
    await api(`/inspections/${id}/observations/${obs.id}`, { method: "DELETE" });
    await load();
    notify(`Observation removed.${again}`);
  });

  const generate = () => run("note", async () => {
    const updated = await api(`/inspections/${id}/generate-note`, { method: "POST" });
    setInsp(updated);
    setNote(updated.note_text);
    notify("Note generated. Read it, edit if needed, then approve.");
  });

  const approve = () => run("approve", async () => {
    if (note !== insp.note_text) await api(`/inspections/${id}/note`, { method: "PUT", body: { note_text: note } });
    await api(`/inspections/${id}/approve`, { method: "POST" });
    await load();
    notify(`Inspection approved. ${plural(observations.length, "point")} sent to departments.`);
    window.scrollTo(0, 0);
  });

  return (
    <>
      <ScreenHead title={insp.location.name} onBack={onBack}
                  sub={`${inspectionTitle(insp)}, ${fmtDate(insp.created_at)}`} />
      <Status tone={draft ? "caution" : "clear"}>
        {draft ? "Draft, not sent to departments yet" : "Approved, points are with departments"}
      </Status>
      {error && <p className="notice" role="alert">{error}</p>}
      <ChecklistSummary inspection={insp} />

      {!draft && insp.note_text && <NoteSheet text={insp.note_text} />}

      <section className="panel">
        <header className="panel-head">
          <h2>{draft ? `Observations (${observations.length})` : "Points raised"}</h2>
        </header>
        {observations.length === 0 && <Empty title="No observations yet">Add the first one below.</Empty>}
        {observations.map((o) => {
          const task = taskByObservation.get(o.id);
          return (
            <div key={o.id} className="obs">
              <Photo photoKey={o.photo_key} alt="" className="row-thumb" emptyText="" />
              <div className="obs-main">
                <p className="obs-text">{o.text}</p>
                {draft ? (
                  <>
                    <label className="obs-dept">
                      <span>
                        {o.suggested_department ? "Department, suggested by AI. Change it if it is wrong." : "The AI could not decide. Choose a department."}
                      </span>
                      <select value={o.suggested_department?.id ?? ""} disabled={Boolean(busy)}
                              onChange={(e) => changeDepartment(o, e.target.value)}>
                        {!o.suggested_department && <option value="" disabled>Choose a department</option>}
                        {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
                      </select>
                    </label>
                    <button type="button" className="btn btn-quiet obs-remove" disabled={Boolean(busy)}
                            onClick={() => removeObservation(o)}>
                      Remove observation
                    </button>
                  </>
                ) : (
                  <p className="row-meta">
                    <span className="tag">{o.suggested_department?.name}</span>
                    {task && <TaskStatus task={task} />}
                    {task && <span className={`due${deadlineInfo(task).overdue ? " is-overdue" : ""}`}>{deadlineInfo(task).text}</span>}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </section>

      {draft && (
        <ObservationForm inspectionId={id} hints={hints} onError={onError}
                         onAdded={(obs) => {
                           load().catch((err) => setError(onError(err)));
                           notify((obs.suggested_department
                             ? `Observation added. AI suggests ${obs.suggested_department.name}.`
                             : "Observation added. Choose its department: the AI could not decide.") + again);
                         }} />
      )}

      {draft && (
        <section className="panel card">
          <h2>Inspection note</h2>
          {note ? (
            <>
              <label className="field">
                <span>Generated from your observations. Edit anything before approving.</span>
                <textarea rows={Math.max(6, note.split("\n").length + 2)} value={note} onChange={(e) => setNote(e.target.value)} />
              </label>
              <p className="quiet">Adding, removing or re-routing an observation clears this note, so finish the observations first.</p>
              {undecided > 0 && <p className="form-error">{plural(undecided, "observation needs", "observations need")} a department before you can approve.</p>}
              <button type="button" className="btn btn-primary btn-wide" disabled={Boolean(busy) || undecided > 0} onClick={approve}>
                {busy === "approve" ? "Approving" : "Approve and send to departments"}
              </button>
              <button type="button" className="btn btn-plain btn-wide" disabled={Boolean(busy)} onClick={generate}>
                {busy === "note" ? "Generating" : "Generate the note again"}
              </button>
            </>
          ) : (
            <>
              <p className="quiet">The note is written from your observations. You review it and approve.</p>
              <button type="button" className="btn btn-primary btn-wide" disabled={Boolean(busy) || observations.length === 0} onClick={generate}>
                {busy === "note" ? "Generating" : "Generate inspection note"}
              </button>
            </>
          )}
        </section>
      )}
    </>
  );
}
