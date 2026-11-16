import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api.js";
import { Empty, Lightbox, Photo, PointRow, Status, TaskStatus } from "../components/ui.jsx";
import {
  AI_RESULT, deadlineInfo, fmtDate, fmtDateTime, fmtDistance, inspectionTitle, lastFix, parseUtc,
} from "../format.js";

const TABS = [
  { id: "review", label: "To review", test: (t) => t.status === "fix_submitted" },
  { id: "open", label: "Open", test: (t) => t.status === "open" },
  { id: "overdue", label: "Overdue", test: (t) => t.overdue },
  { id: "closed", label: "Closed", test: (t) => t.status === "closed" },
  { id: "all", label: "All", test: () => true },
];

const EMPTY_TEXT = {
  review: ["No fixes waiting for review", "When a department submits a fix with an after-photo, it appears here."],
  open: ["No open points", "Every point has a fix submitted or is closed."],
  overdue: ["No overdue points", "Departments are within their deadlines."],
  closed: ["No closed points yet", "Points you accept move here."],
  all: ["No points match", "Change the search or the filters to see more."],
};

const isWide = () => window.matchMedia("(min-width: 1000px)").matches;

function matchesSearch(task, q) {
  if (!q) return true;
  const text = `#${task.id} ${task.observation.text} ${task.station} ${task.department.name}`.toLowerCase();
  return q.toLowerCase().split(/\s+/).every((word) => text.includes(word));
}

export default function Points({ tasks, filter, setFilter, selectedId, setSelectedId, onChanged, openInspection, notify }) {
  const set = (patch) => setFilter({ ...filter, ...patch });

  const departments = useMemo(() => [...new Set(tasks.map((t) => t.department.name))].sort(), [tasks]);
  const stations = useMemo(() => [...new Set(tasks.map((t) => t.station))].sort(), [tasks]);

  // Department, station and search apply first, so the numbers on the tabs are always true.
  const base = useMemo(
    () => tasks.filter((t) => (!filter.dept || t.department.name === filter.dept)
      && (!filter.station || t.station === filter.station) && matchesSearch(t, filter.q.trim())),
    [tasks, filter.dept, filter.station, filter.q]
  );
  const tab = TABS.find((x) => x.id === filter.status) || TABS[TABS.length - 1];
  const list = useMemo(() => {
    const rows = base.filter(tab.test);
    if (tab.id === "closed") return rows.sort((a, b) => parseUtc(b.closed_at) - parseUtc(a.closed_at));
    // pending points first, most urgent deadline on top
    return rows.sort((a, b) => (a.status === "closed") - (b.status === "closed") || parseUtc(a.deadline) - parseUtc(b.deadline));
  }, [base, tab]);

  // Keep a point selected: the same one if it is still listed, otherwise the one that took its place.
  const lastIndex = useRef(0);
  useEffect(() => {
    const i = list.findIndex((t) => t.id === selectedId);
    if (i >= 0) {
      lastIndex.current = i;
      return;
    }
    const next = isWide() && list.length ? list[Math.min(lastIndex.current, list.length - 1)].id : null;
    if (next !== selectedId) setSelectedId(next);
  }, [list, selectedId, setSelectedId]);

  // When a point is opened from another page, bring its row into view in the list.
  // and start its details from the top.
  const detailRef = useRef(null);
  useEffect(() => {
    document.querySelector(".list-panel .row.is-selected")?.scrollIntoView({ block: "nearest" });
    detailRef.current?.scrollTo(0, 0);
    if (!isWide() && selectedId != null) window.scrollTo(0, 0); // on a phone the details replace the list
  }, [selectedId]);

  const selected = list.find((t) => t.id === selectedId) || null;
  const filtered = filter.dept || filter.station || filter.q;
  const [emptyTitle, emptyHint] = EMPTY_TEXT[filtered ? "all" : tab.id];

  return (
    <div className="stack">
      <div className="page-head">
        <h1>Compliance points</h1>
        <p>Every observation from an approved inspection, tracked until the fix is accepted.</p>
      </div>

      <div className="toolbar">
        <div className="tabs" role="tablist" aria-label="Filter by status">
          {TABS.map((t) => (
            <button key={t.id} type="button" role="tab" aria-selected={tab.id === t.id}
                    className={`tab${tab.id === t.id ? " is-active" : ""}`} onClick={() => set({ status: t.id })}>
              {t.label}
              <span className="tab-count">{base.filter(t.test).length}</span>
            </button>
          ))}
        </div>
        <div className="filters">
          <input type="search" className="input" placeholder="Search points" aria-label="Search points"
                 value={filter.q} onChange={(e) => set({ q: e.target.value })} />
          <select className="input" aria-label="Department" value={filter.dept} onChange={(e) => set({ dept: e.target.value })}>
            <option value="">All departments</option>
            {departments.map((d) => <option key={d}>{d}</option>)}
          </select>
          <select className="input" aria-label="Location" value={filter.station} onChange={(e) => set({ station: e.target.value })}>
            <option value="">All locations</option>
            {stations.map((s) => <option key={s}>{s}</option>)}
          </select>
          {filtered && (
            <button type="button" className="btn btn-quiet" onClick={() => set({ dept: "", station: "", q: "" })}>
              Clear filters
            </button>
          )}
        </div>
      </div>

      <div className={`split${selected ? " has-selection" : ""}`}>
        <section className="panel list-panel" aria-label="Points">
          {list.length === 0 ? (
            <Empty title={emptyTitle}>{emptyHint}</Empty>
          ) : (
            <div className="rows">
              {list.map((t) => (
                <PointRow key={t.id} task={t} selected={t.id === selectedId} onClick={() => setSelectedId(t.id)} />
              ))}
            </div>
          )}
        </section>

        <section className="panel detail" aria-label="Point details" ref={detailRef}>
          {selected ? (
            <PointDetail key={selected.id} task={selected} onChanged={onChanged} notify={notify}
                         openInspection={openInspection} onBack={() => setSelectedId(null)} />
          ) : (
            <Empty title="Select a point">Its photos, AI check and history show here.</Empty>
          )}
        </section>
      </div>
    </div>
  );
}

// The four stops every point passes through, drawn as a short route line.
export function Journey({ task, fix }) {
  const closed = task.status === "closed";
  const waiting = task.status === "fix_submitted";
  const stops = [
    { label: "Observed", date: task.observation.created_at, state: "done" },
    { label: "With department", date: task.created_at, state: closed || waiting ? "done" : "now" },
    { label: "Fix submitted", date: closed || waiting ? fix?.created_at : null, state: closed ? "done" : waiting ? "now" : "next" },
    { label: "Closed", date: task.closed_at, state: closed ? "done" : "next" },
  ];
  return (
    <ol className="journey">
      {stops.map((s, i) => (
        <li key={s.label} className={`stop stop-${s.state}${stops[i + 1] && stops[i + 1].state !== "next" ? " stop-travelled" : ""}`}>
          <span className="stop-dot" aria-hidden="true" />
          <span className="stop-label">{s.label}</span>
          <span className="stop-date">{s.date ? fmtDate(s.date) : s.state === "now" ? "In progress" : ""}</span>
        </li>
      ))}
    </ol>
  );
}

export function AiCheck({ fix }) {
  const v = fix.verification || {};
  const meta = AI_RESULT[v.result];
  if (!meta) return null;
  const lines = [];
  if (v.same_location === true) lines.push(`The fix photo was taken ${fmtDistance(v.distance_m)} from the reported spot.`);
  if (v.same_location === false) lines.push(`The fix photo was taken ${fmtDistance(v.distance_m)} from the reported spot. The limit is 100 m.`);
  if (v.same_location == null) lines.push("The fix photo has no GPS location, so the spot could not be compared.");
  if (v.defects_remaining?.length) lines.push(`Still visible in the after photo: ${v.defects_remaining.join(", ")}.`);
  return (
    <div className={`aicheck aicheck-${meta.tone}`}>
      <div className="aicheck-head">
        <span>AI check</span>
        <Status tone={meta.tone}>{meta.label}</Status>
      </div>
      {lines.map((line) => <p key={line}>{line}</p>)}
    </div>
  );
}

function PointDetail({ task, onChanged, notify, openInspection, onBack }) {
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [zoom, setZoom] = useState(null);

  const fix = lastFix(task);
  const due = deadlineInfo(task);
  const obs = task.observation;
  const insp = task.inspection;
  const reviewable = task.status === "fix_submitted";
  const wasRejected = task.status === "open" && fix;

  async function decide(action) {
    setBusy(true);
    setError("");
    try {
      await api(`/tasks/${task.id}/${action}`, { method: "POST", body: { remark: action === "reject" ? reason.trim() : "" } });
      notify(action === "close"
        ? `Fix accepted. Point #${task.id} is closed.`
        : `Fix rejected. Point #${task.id} is back with ${task.department.name}.`);
      await onChanged();
      setRejecting(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="detail-body">
      <button type="button" className="btn btn-quiet detail-back" onClick={onBack}>
        Back to list
      </button>

      <div className="detail-top">
        <span className="detail-id">Point #{task.id}</span>
        <TaskStatus task={task} />
        {due.overdue && <Status tone="danger">Overdue</Status>}
        {task.escalation_level > 0 && <span className="tag">Escalation level {task.escalation_level}</span>}
      </div>
      <h2 className="detail-title">{obs.text}</h2>

      {/* The photo proof comes first: it is what the reviewer decides on. */}
      <div className="photos">
        <figure>
          <Photo photoKey={obs.photo_key} alt={`Before: ${obs.text}`} onOpen={setZoom} emptyText="No photo was taken" />
          <figcaption>Before, {fmtDate(obs.created_at)}</figcaption>
        </figure>
        <figure>
          <Photo photoKey={fix?.photo_key} alt={`After: ${fix?.remark || obs.text}`} onOpen={setZoom}
                 emptyText={fix ? "Fix sent without a photo" : "No fix submitted yet"} />
          <figcaption>
            {fix ? `${wasRejected ? "Rejected fix" : "After"}, ${fmtDate(fix.created_at)}` : "After"}
          </figcaption>
        </figure>
      </div>

      {fix && !wasRejected && <AiCheck fix={fix} />}

      <Journey task={task} fix={fix} />

      <dl className="facts">
        <div><dt>Location</dt><dd>{task.station}</dd></div>
        <div><dt>Department</dt><dd>{task.department.name}</dd></div>
        <div>
          <dt>Observed</dt>
          <dd>{fmtDate(obs.created_at)}{insp && ` by ${insp.officer.full_name}`}</dd>
        </div>
        <div>
          <dt>{task.status === "closed" ? "Closed" : "Deadline"}</dt>
          <dd className={due.overdue ? "is-overdue" : ""}>
            {task.status === "closed" ? fmtDate(task.closed_at) : `${fmtDate(task.deadline)} (${due.text.toLowerCase()})`}
          </dd>
        </div>
      </dl>

      <div className="history">
        <h3>History</h3>
        {task.updates.length === 0 ? (
          <p className="quiet">No update from {task.department.name} yet.</p>
        ) : (
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
        )}
        {insp && (
          <button type="button" className="btn btn-quiet" onClick={() => openInspection(insp.id)}>
            Open the {inspectionTitle(insp).toLowerCase()} note
          </button>
        )}
      </div>

      {reviewable && (
        <div className="actionbar">
          {error && <p className="form-error" role="alert">{error}</p>}
          {rejecting ? (
            <>
              <label className="field">
                <span>Reason for rejecting (the department sees this)</span>
                <textarea rows="2" value={reason} onChange={(e) => setReason(e.target.value)} autoFocus
                          placeholder="For example: water is still standing near the drain" />
              </label>
              <div className="actionbar-buttons">
                <button type="button" className="btn btn-danger" disabled={busy} onClick={() => decide("reject")}>
                  Reject fix
                </button>
                <button type="button" className="btn btn-plain" disabled={busy} onClick={() => setRejecting(false)}>
                  Cancel
                </button>
              </div>
            </>
          ) : (
            <div className="actionbar-buttons">
              <button type="button" className="btn btn-primary" disabled={busy} onClick={() => decide("close")}>
                Accept fix
              </button>
              <button type="button" className="btn btn-plain" disabled={busy} onClick={() => setRejecting(true)}>
                Reject fix
              </button>
              <span className="actionbar-note">Accepting closes the point.</span>
            </div>
          )}
        </div>
      )}

      <Lightbox image={zoom} onClose={() => setZoom(null)} />
    </div>
  );
}
