import { useMemo, useState } from "react";
import { api } from "../api.js";
import StationMap from "../components/StationMap.jsx";
import { Empty, PointRow, Status } from "../components/ui.jsx";
import { fmtDate, inspectionTitle, parseUtc, plural } from "../format.js";

function Figure({ label, value, tone, onClick }) {
  const body = (
    <>
      <span className="figure-label">
        {tone && <span className={`lamp lamp-${tone}`} aria-hidden="true" />}
        {label}
      </span>
      <span className="figure-value">{value ?? "–"}</span>
    </>
  );
  return onClick ? (
    <button type="button" className="figure figure-link" onClick={onClick}>
      {body}
    </button>
  ) : (
    <div className="figure">{body}</div>
  );
}

export default function Overview({ data, openPoints, openInspection, onChanged, notify }) {
  const { summary, tasks, inspections } = data;
  const [checking, setChecking] = useState(false);
  const byStatus = summary.tasks_by_status || {};
  const review = byStatus.fix_submitted || 0;
  const open = byStatus.open || 0;
  const closed = byStatus.closed || 0;
  const overdue = summary.overdue || 0;

  // Pending points per department and per station, worked out from the task list.
  const { departments, stations } = useMemo(() => {
    const depts = new Map();
    const places = new Map();
    for (const t of tasks) {
      if (t.status === "closed") continue;
      const d = depts.get(t.department.name) || { name: t.department.name, pending: 0, overdue: 0 };
      d.pending += 1;
      if (t.overdue) d.overdue += 1;
      depts.set(d.name, d);
      if (t.inspection) {
        const loc = t.inspection.location;
        const p = places.get(loc.name) || { name: loc.name, latitude: loc.latitude, longitude: loc.longitude, pending: 0, overdue: 0 };
        p.pending += 1;
        if (t.overdue) p.overdue += 1;
        places.set(p.name, p);
      }
    }
    return {
      departments: [...depts.values()].sort((a, b) => b.pending - a.pending || a.name.localeCompare(b.name)),
      stations: [...places.values()],
    };
  }, [tasks]);

  const worstOverdue = useMemo(
    () => tasks.filter((t) => t.overdue).sort((a, b) => parseUtc(a.deadline) - parseUtc(b.deadline)).slice(0, 5),
    [tasks]
  );
  const latest = inspections.slice(0, 5); // the API returns newest first
  const maxPending = Math.max(1, ...departments.map((d) => d.pending));

  let headline = "Everything is up to date";
  let action = null;
  if (review > 0) {
    headline = `${plural(review, "fix is", "fixes are")} waiting for your review`;
    action = { label: review === 1 ? "Review fix" : "Review fixes", go: () => openPoints({ status: "review" }) };
  } else if (overdue > 0) {
    headline = `${plural(overdue, "point is", "points are")} past the deadline`;
    action = { label: "See overdue points", go: () => openPoints({ status: "overdue" }) };
  } else if (open > 0) {
    headline = `${plural(open, "point is", "points are")} with departments, none overdue`;
  }

  // Run the overdue check now. The same check runs by itself every hour (backend: python -m app.escalate).
  async function checkOverdue() {
    setChecking(true);
    try {
      const r = await api("/tasks/run-escalation", { method: "POST" });
      const emails = r.email_on ? `${plural(r.emails_sent, "reminder email")} sent` : "email reminders are switched off";
      notify(r.escalated > 0
        ? `${plural(r.escalated, "point")} moved to a higher escalation level; ${emails}.`
        : "No point is due for a higher escalation level yet.");
      if (r.escalated > 0) await onChanged();
    } catch (err) {
      notify(err.message);
    }
    setChecking(false);
  }

  const today = new Date().toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long", year: "numeric" });

  return (
    <div className="stack">
      <section className="lead">
        <div>
          <p className="lead-date">{today}</p>
          <h1>{headline}</h1>
        </div>
        {action && (
          <button type="button" className="btn btn-primary btn-large" onClick={action.go}>
            {action.label}
          </button>
        )}
      </section>

      <section className="figures" aria-label="Summary">
        <Figure label="To review" value={review} tone="caution" onClick={() => openPoints({ status: "review" })} />
        <Figure label="Open" value={open} tone="idle" onClick={() => openPoints({ status: "open" })} />
        <Figure label="Overdue" value={overdue} tone="danger" onClick={() => openPoints({ status: "overdue" })} />
        <Figure label="Closed" value={closed} tone="clear" onClick={() => openPoints({ status: "closed" })} />
        <Figure label="Avg. days to close" value={summary.avg_days_to_close} />
        <Figure label="Inspections" value={summary.inspections} onClick={() => openInspection()} />
      </section>

      <div className="cols">
        <section className="panel">
          <header className="panel-head">
            <h2>Pending by department</h2>
            <p>Select a department to see its points.</p>
          </header>
          {departments.length === 0 ? (
            <Empty title="Nothing pending">Every point has been closed.</Empty>
          ) : (
            <div className="bars">
              {departments.map((d) => (
                <button type="button" key={d.name} className="bar-row" onClick={() => openPoints({ dept: d.name })}
                        title={`${d.name}: ${d.pending} pending${d.overdue ? `, ${d.overdue} overdue` : ""}`}>
                  <span className="bar-label">{d.name}</span>
                  <span className="bar-area">
                    <span className="bar" style={{ flexBasis: `${(d.pending / maxPending) * 100}%` }} />
                    <span className="bar-value">{d.pending}</span>
                  </span>
                  <span className="bar-note">
                    {d.overdue > 0 && (
                      <>
                        <span className="lamp lamp-danger" aria-hidden="true" />
                        {d.overdue} overdue
                      </>
                    )}
                  </span>
                </button>
              ))}
            </div>
          )}
        </section>

        <section className="panel">
          <header className="panel-head">
            <h2>Pending by location</h2>
            <p>The number is pending points. A red dot means some are overdue.</p>
          </header>
          <StationMap stations={stations} onPick={(name) => openPoints({ station: name })} />
        </section>
      </div>

      <div className="cols">
        <section className="panel">
          <header className="panel-head panel-head-row">
            <h2>Longest overdue</h2>
            <span className="panel-head-actions">
              {overdue > 0 && (
                <button type="button" className="btn btn-quiet" onClick={checkOverdue} disabled={checking}
                        title="Raises the escalation level of overdue points that are due for it and emails the department. This also runs by itself every hour.">
                  {checking ? "Checking" : "Check overdue points"}
                </button>
              )}
              {overdue > worstOverdue.length && (
                <button type="button" className="btn btn-quiet" onClick={() => openPoints({ status: "overdue" })}>
                  See all {overdue}
                </button>
              )}
            </span>
          </header>
          {worstOverdue.length === 0 ? (
            <Empty title="No overdue points">Departments are within their deadlines.</Empty>
          ) : (
            <div className="rows">
              {worstOverdue.map((t) => (
                <PointRow key={t.id} task={t} thumb={false}
                          onClick={() => openPoints({ status: "overdue", selectId: t.id })} />
              ))}
            </div>
          )}
        </section>

        <section className="panel">
          <header className="panel-head panel-head-row">
            <h2>Latest inspections</h2>
            {inspections.length > latest.length && (
              <button type="button" className="btn btn-quiet" onClick={() => openInspection()}>
                See all {inspections.length}
              </button>
            )}
          </header>
          {latest.length === 0 ? (
            <Empty title="No inspections yet">Inspections recorded in the mobile app appear here.</Empty>
          ) : (
            <div className="rows">
              {latest.map((insp) => (
                <button type="button" key={insp.id} className="row" onClick={() => openInspection(insp.id)}>
                  <span className="row-main">
                    <span className="row-title">{insp.location.name}</span>
                    <span className="row-meta">
                      <span>{inspectionTitle(insp)}</span>
                      <span>{plural(insp.observations.length, "point")}</span>
                    </span>
                  </span>
                  <span className="row-side">
                    <Status tone={insp.status === "approved" ? "clear" : "idle"}>
                      {insp.status === "approved" ? "Note issued" : "Draft"}
                    </Status>
                    <span className="due">{fmtDate(insp.created_at)}</span>
                  </span>
                </button>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
