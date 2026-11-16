// Department staff: my department's tasks -> open one -> submit the fix with an after-photo and GPS.
import { useEffect, useMemo, useState } from "react";
import { api, apiForm } from "../../api.js";
import { Empty, Lightbox, Photo, PointRow, Status, TaskStatus } from "../../components/ui.jsx";
import { usePosition } from "../../device.js";
import { AI_RESULT, deadlineInfo, enrichTasks, fmtDate, fmtDateTime, lastFix, parseUtc } from "../../format.js";
import { AiCheck, Journey } from "../Points.jsx";
import { GpsLine, PhotoPicker, ScreenHead } from "./parts.jsx";

const TABS = [
  { id: "todo", label: "To do", test: (t) => t.status === "open" },
  { id: "sent", label: "Fix sent", test: (t) => t.status === "fix_submitted" },
  { id: "closed", label: "Closed", test: (t) => t.status === "closed" },
];

const EMPTY_TEXT = {
  todo: ["Nothing to do", "New points from inspections appear here."],
  sent: ["No fixes waiting", "Fixes you send wait here until the senior officer reviews them."],
  closed: ["No closed points yet", "Points move here when your fix is accepted."],
};

export default function Staff({ me, notify, onError }) {
  const [tasks, setTasks] = useState(null);
  const [error, setError] = useState("");
  const [tab, setTab] = useState("todo");
  const [openId, setOpenId] = useState(null);

  // Staff only receive their own department's tasks. The inspections are loaded to know each task's location.
  async function load() {
    const [list, inspections] = await Promise.all([api("/tasks"), api("/inspections")]);
    setTasks(enrichTasks(list, inspections));
  }

  useEffect(() => {
    load().catch((err) => setError(onError(err)));
  }, []);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [openId]);

  const current = TABS.find((t) => t.id === tab);
  const list = useMemo(
    () => (tasks || []).filter(current.test).sort((a, b) => parseUtc(a.deadline) - parseUtc(b.deadline)),
    [tasks, current]
  );
  const open = tasks?.find((t) => t.id === openId);

  if (open) {
    return (
      <TaskScreen task={open} onBack={() => setOpenId(null)} onError={onError}
                  onSent={async (result) => {
                    await load();
                    setTab("sent");
                    const check = AI_RESULT[result]?.label.toLowerCase();
                    notify(check ? `Fix sent for review. AI check: ${check}.` : "Fix sent for review.");
                  }} />
    );
  }

  const department = me?.department?.name;
  return (
    <>
      <ScreenHead title={department ? `${department} tasks` : "Department tasks"}
                  sub="Points raised in inspections for your department. Fix each one and send photo proof." />
      {error && <p className="notice" role="alert">{error}</p>}
      {!tasks && !error && <p className="loading">Loading your tasks</p>}
      {tasks && (
        <>
          <div className="tabs tabs-wide" role="tablist" aria-label="Filter tasks">
            {TABS.map((t) => (
              <button key={t.id} type="button" role="tab" aria-selected={tab === t.id}
                      className={`tab${tab === t.id ? " is-active" : ""}`} onClick={() => setTab(t.id)}>
                {t.label}
                <span className="tab-count">{tasks.filter(t.test).length}</span>
              </button>
            ))}
          </div>
          <section className="panel">
            {list.length === 0 ? (
              <Empty title={EMPTY_TEXT[tab][0]}>{EMPTY_TEXT[tab][1]}</Empty>
            ) : (
              <div className="rows">
                {list.map((t) => <PointRow key={t.id} task={t} onClick={() => setOpenId(t.id)} />)}
              </div>
            )}
          </section>
        </>
      )}
    </>
  );
}

function TaskScreen({ task, onBack, onSent, onError }) {
  const [zoom, setZoom] = useState(null);
  const obs = task.observation;
  const fix = lastFix(task);
  const due = deadlineInfo(task);
  const wasRejected = task.status === "open" && fix;
  const rejection = wasRejected ? [...task.updates].reverse().find((u) => !u.photo_key && !u.verification?.result) : null;

  return (
    <>
      <ScreenHead title={obs.text} onBack={onBack} sub={`Point #${task.id} at ${task.station}`} />
      <div className="detail-top">
        <TaskStatus task={task} />
        {due.overdue && <Status tone="danger">Overdue</Status>}
        <span className={`due${due.overdue ? " is-overdue" : ""}`}>
          {task.status === "closed" ? due.text : `Deadline ${fmtDate(task.deadline)} (${due.text.toLowerCase()})`}
        </span>
      </div>

      {rejection && (
        <div className="aicheck aicheck-danger" role="note">
          <div className="aicheck-head">
            <span>Your last fix was rejected</span>
            <span className="tag">Escalation level {task.escalation_level}</span>
          </div>
          <p>{rejection.remark} ({rejection.user.full_name}, {fmtDate(rejection.created_at)})</p>
        </div>
      )}

      <section className="panel card">
        <Journey task={task} fix={fix} />
        <div className="photos">
          <figure>
            <Photo photoKey={obs.photo_key} alt={`Before: ${obs.text}`} onOpen={setZoom} emptyText="No photo was taken" />
            <figcaption>Before, {fmtDate(obs.created_at)}</figcaption>
          </figure>
          {fix && (
            <figure>
              <Photo photoKey={fix.photo_key} alt={`After: ${fix.remark || obs.text}`} onOpen={setZoom} emptyText="Fix sent without a photo" />
              <figcaption>{wasRejected ? "Rejected fix" : "After"}, {fmtDate(fix.created_at)}</figcaption>
            </figure>
          )}
        </div>
        {fix && !wasRejected && <AiCheck fix={fix} />}
        {task.status === "fix_submitted" && <p className="quiet">Your fix is waiting for the senior officer's review.</p>}
      </section>

      {task.status === "open" && <FixForm task={task} onSent={onSent} onError={onError} />}

      {task.updates.length > 0 && (
        <section className="panel card history">
          <h3>History</h3>
          <ol>
            {task.updates.map((u) => (
              <li key={u.id}>
                <p className="history-who">
                  <strong>{u.user.full_name}</strong>
                  <span>{fmtDateTime(u.created_at)}</span>
                </p>
                <p>{u.remark || (u.photo_key ? "Submitted a fix." : "No remark.")}</p>
              </li>
            ))}
          </ol>
        </section>
      )}

      <Lightbox image={zoom} onClose={() => setZoom(null)} />
    </>
  );
}

function FixForm({ task, onSent, onError }) {
  const [remark, setRemark] = useState("");
  const [photo, setPhoto] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const position = usePosition();

  async function send(e) {
    e.preventDefault();
    if (!photo) {
      setError("Add an after-photo. The fix is checked from the photo.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const updated = await apiForm(`/tasks/${task.id}/fix`, {
        remark: remark.trim(),
        latitude: position.coords?.latitude,
        longitude: position.coords?.longitude,
      }, photo);
      const result = updated.updates[updated.updates.length - 1]?.verification?.result;
      await onSent(result);
    } catch (err) {
      setError(onError(err));
      setBusy(false);
    }
  }

  return (
    <form onSubmit={send} className="panel card">
      <h2>Send your fix</h2>
      <label className="field">
        <span>What was done?</span>
        <textarea rows="2" value={remark} onChange={(e) => setRemark(e.target.value)}
                  placeholder="For example: Replaced both LED fittings" />
      </label>
      <PhotoPicker file={photo} onChange={setPhoto} label="Add after-photo" />
      <GpsLine position={position} missingNote="Without GPS the fix needs a manual check." />
      {error && <p className="form-error" role="alert">{error}</p>}
      <button className="btn btn-primary btn-wide" disabled={busy}>
        {busy ? "Sending" : "Send fix for review"}
      </button>
    </form>
  );
}
