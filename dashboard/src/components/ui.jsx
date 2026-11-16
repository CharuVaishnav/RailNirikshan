// Small building blocks shared by all pages.
import { useEffect, useState } from "react";
import { photoUrl } from "../api.js";
import { checklistResult } from "../checklists/index.js";
import { TASK_STATUS, deadlineInfo } from "../format.js";

// A status is always a signal lamp plus a written label, never colour alone.
export function Status({ tone = "idle", children }) {
  return (
    <span className="status">
      <span className={`lamp lamp-${tone}`} aria-hidden="true" />
      {children}
    </span>
  );
}

export function TaskStatus({ task }) {
  const s = TASK_STATUS[task.status] || { label: task.status, tone: "idle" };
  return <Status tone={s.tone}>{s.label}</Status>;
}

// Loads a protected photo. With onOpen it becomes a button that enlarges the photo.
export function Photo({ photoKey, alt, onOpen, className = "", emptyText = "No photo" }) {
  const [src, setSrc] = useState(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let live = true;
    setSrc(null);
    setFailed(false);
    if (photoKey) {
      photoUrl(photoKey).then((url) => {
        if (!live) return;
        if (url) setSrc(url);
        else setFailed(true);
      });
    }
    return () => {
      live = false;
    };
  }, [photoKey]);

  if (!photoKey || failed) {
    return <span className={`photo photo-empty ${className}`}>{failed ? "Photo not available" : emptyText}</span>;
  }
  if (!src) return <span className={`photo photo-empty ${className}`} aria-busy="true" />;
  if (onOpen) {
    return (
      <button type="button" className={`photo photo-button ${className}`}
              onClick={() => onOpen({ src, alt })} aria-label={`Enlarge photo: ${alt}`}>
        <img src={src} alt={alt} />
      </button>
    );
  }
  return (
    <span className={`photo ${className}`}>
      <img src={src} alt={alt} />
    </span>
  );
}

export function Lightbox({ image, onClose }) {
  useEffect(() => {
    if (!image) return undefined;
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [image, onClose]);

  if (!image) return null;
  return (
    <div className="lightbox" role="dialog" aria-modal="true" aria-label={image.alt} onClick={onClose}>
      <figure onClick={(e) => e.stopPropagation()}>
        <img src={image.src} alt={image.alt} />
        <figcaption>
          <span>{image.alt}</span>
          <button type="button" className="btn btn-light" onClick={onClose} autoFocus>
            Close
          </button>
        </figcaption>
      </figure>
    </div>
  );
}

// What the officer ticked in the checklist: how many items were OK, and which were not.
export function ChecklistSummary({ inspection }) {
  const result = checklistResult(inspection);
  if (!result) return null;
  return (
    <div className="checksum">
      <p>
        <strong>Checklist:</strong> {result.ok} of {result.total} items OK
        {result.notOk.length > 0 && `, ${result.notOk.length} not OK`}
      </p>
      {result.notOk.length > 0 && (
        <ul>
          {result.notOk.map((label) => (
            <li key={label}>
              <span className="lamp lamp-danger" aria-hidden="true" />
              {label}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function Empty({ title, children }) {
  return (
    <div className="empty">
      <strong>{title}</strong>
      {children && <p>{children}</p>}
    </div>
  );
}

// One compliance point as a list row. Used on the overview and in the points list.
export function PointRow({ task, selected = false, onClick, thumb = true }) {
  const due = deadlineInfo(task);
  return (
    <button type="button" className={`row${selected ? " is-selected" : ""}`} onClick={onClick}
            aria-current={selected ? "true" : undefined}>
      {thumb && <Photo photoKey={task.observation.photo_key} alt="" className="row-thumb" emptyText="" />}
      <span className="row-main">
        <span className="row-title">{task.observation.text}</span>
        <span className="row-meta">
          <span className="row-id">#{task.id}</span>
          <span className="row-place">{task.station}</span>
          <span className="tag">{task.department.name}</span>
        </span>
      </span>
      <span className="row-side">
        <TaskStatus task={task} />
        <span className={`due${due.overdue ? " is-overdue" : ""}`}>
          {due.text}
          {task.escalation_level > 0 && task.status !== "closed" && `, level ${task.escalation_level}`}
        </span>
      </span>
    </button>
  );
}
