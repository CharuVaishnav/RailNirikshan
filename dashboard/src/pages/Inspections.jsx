import { useEffect, useMemo, useRef } from "react";
import { ChecklistSummary, Empty, PdfButton, Photo, Status, TaskStatus } from "../components/ui.jsx";
import { fmtDate, inspectionTitle, plural } from "../format.js";

const isWide = () => window.matchMedia("(min-width: 1000px)").matches;

// Turn the plain-text note into a heading, numbered points and paragraphs.
// A point may end with its department in square brackets: "Lights not working. [Electrical]"
function parseNote(text) {
  const lines = text.split("\n").map((l) => l.trim()).filter(Boolean);
  const [heading, ...rest] = lines;
  const blocks = [];
  for (const line of rest) {
    const numbered = line.match(/^\d+[.)]\s+(.*)$/);
    if (!numbered) {
      blocks.push({ type: "text", text: line });
      continue;
    }
    const withDept = numbered[1].match(/^(.*?)\s*\[([^\]]+)\]$/);
    const item = withDept ? { text: withDept[1], dept: withDept[2] } : { text: numbered[1] };
    const last = blocks[blocks.length - 1];
    if (last?.type === "list") last.items.push(item);
    else blocks.push({ type: "list", items: [item] });
  }
  return { heading, blocks };
}

// The note as a sheet of paper: heading, numbered points with their department, any extra text.
export function NoteSheet({ text }) {
  const note = parseNote(text);
  return (
    <article className="sheet">
      <h3>{note.heading}</h3>
      {note.blocks.map((b, i) =>
        b.type === "list" ? (
          <ol key={i}>
            {b.items.map((item, j) => (
              <li key={j}>
                {item.text}
                {item.dept && <span className="tag">{item.dept}</span>}
              </li>
            ))}
          </ol>
        ) : (
          <p key={i}>{b.text}</p>
        )
      )}
    </article>
  );
}

export function progress(insp, taskByObservation) {
  const tasks = insp.observations.map((o) => taskByObservation.get(o.id)).filter(Boolean);
  return {
    total: tasks.length,
    closed: tasks.filter((t) => t.status === "closed").length,
    review: tasks.filter((t) => t.status === "fix_submitted").length,
    open: tasks.filter((t) => t.status === "open").length,
  };
}

export function Meter({ p }) {
  return (
    <span className="meter" aria-hidden="true">
      {p.closed > 0 && <span className="meter-clear" style={{ flexGrow: p.closed }} />}
      {p.review > 0 && <span className="meter-caution" style={{ flexGrow: p.review }} />}
      {p.open > 0 && <span className="meter-idle" style={{ flexGrow: p.open }} />}
    </span>
  );
}

export default function Inspections({ inspections, tasks, selectedId, setSelectedId, openPoints }) {
  const taskByObservation = useMemo(() => new Map(tasks.map((t) => [t.observation.id, t])), [tasks]);

  useEffect(() => {
    if (inspections.some((i) => i.id === selectedId)) return;
    const next = isWide() && inspections.length ? inspections[0].id : null;
    if (next !== selectedId) setSelectedId(next);
  }, [inspections, selectedId, setSelectedId]);

  // Bring the chosen inspection into view in the list and start its details from the top.
  const detailRef = useRef(null);
  useEffect(() => {
    document.querySelector(".list-panel .row.is-selected")?.scrollIntoView({ block: "nearest" });
    detailRef.current?.scrollTo(0, 0);
    if (!isWide() && selectedId != null) window.scrollTo(0, 0); // on a phone the details replace the list
  }, [selectedId]);

  const selected = inspections.find((i) => i.id === selectedId) || null;

  return (
    <div className="stack">
      <div className="page-head">
        <h1>Inspections</h1>
        <p>Each inspection note and the points it raised.</p>
      </div>

      <div className={`split${selected ? " has-selection" : ""}`}>
        <section className="panel list-panel" aria-label="Inspections">
          {inspections.length === 0 ? (
            <Empty title="No inspections yet">Inspections recorded in the mobile app appear here.</Empty>
          ) : (
            <div className="rows">
              {inspections.map((insp) => {
                const p = progress(insp, taskByObservation);
                return (
                  <button type="button" key={insp.id} className={`row${insp.id === selectedId ? " is-selected" : ""}`}
                          aria-current={insp.id === selectedId ? "true" : undefined} onClick={() => setSelectedId(insp.id)}>
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
                          <Status tone="idle">Draft</Status>
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

        <section className="panel detail" aria-label="Inspection details" ref={detailRef}>
          {selected ? (
            <InspectionDetail insp={selected} taskByObservation={taskByObservation} openPoints={openPoints}
                              onBack={() => setSelectedId(null)} />
          ) : (
            <Empty title="Select an inspection">Its note and points show here.</Empty>
          )}
        </section>
      </div>
    </div>
  );
}

function InspectionDetail({ insp, taskByObservation, openPoints, onBack }) {
  const approved = insp.status === "approved";
  const p = progress(insp, taskByObservation);

  return (
    <div className="detail-body">
      <button type="button" className="btn btn-quiet detail-back" onClick={onBack}>
        Back to list
      </button>

      <div className="detail-top">
        <span className="detail-id">{inspectionTitle(insp)}</span>
        <Status tone={approved ? "clear" : "idle"}>{approved ? "Note issued" : "Draft, not issued yet"}</Status>
      </div>
      <h2 className="detail-title">{insp.location.name}</h2>

      <dl className="facts">
        <div><dt>Inspected</dt><dd>{fmtDate(insp.created_at)}</dd></div>
        <div><dt>Officer</dt><dd>{insp.officer.full_name}</dd></div>
        <div><dt>Division</dt><dd>{insp.location.division}</dd></div>
        <div>
          <dt>Points</dt>
          <dd>
            {approved
              ? `${p.total} raised, ${p.closed} closed, ${p.review} to review, ${p.open} open`
              : `${insp.observations.length} recorded so far`}
          </dd>
        </div>
      </dl>

      <ChecklistSummary inspection={insp} />

      {insp.note_text ? (
        <>
          <NoteSheet text={insp.note_text} />
          <PdfButton inspection={insp} />
        </>
      ) : (
        <p className="quiet sheet-missing">The officer has not generated the inspection note yet.</p>
      )}

      <div className="history">
        <h3>Points raised</h3>
        <div className="rows rows-inset">
          {insp.observations.map((o) => {
            const task = taskByObservation.get(o.id);
            const inner = (
              <>
                <Photo photoKey={o.photo_key} alt="" className="row-thumb" emptyText="" />
                <span className="row-main">
                  <span className="row-title">{o.text}</span>
                  <span className="row-meta">
                    {task && <span className="row-id">#{task.id}</span>}
                    <span className="tag">{o.suggested_department?.name || "Department not chosen"}</span>
                  </span>
                </span>
                <span className="row-side">
                  {task ? <TaskStatus task={task} /> : <Status tone="idle">Not issued</Status>}
                </span>
              </>
            );
            return task ? (
              <button type="button" key={o.id} className="row" onClick={() => openPoints({ selectId: task.id })}>
                {inner}
              </button>
            ) : (
              <div key={o.id} className="row row-static">{inner}</div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
