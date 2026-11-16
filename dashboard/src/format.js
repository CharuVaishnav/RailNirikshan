// Shared helpers: dates, wording and the small amount of data joining the dashboard needs.

const DAY = 86_400_000;

// The backend sends UTC times without a "Z", so add it before parsing.
export function parseUtc(value) {
  if (!value) return null;
  return new Date(/Z|[+-]\d\d:\d\d$/.test(value) ? value : `${value}Z`);
}

export function fmtDate(value) {
  const d = value instanceof Date ? value : parseUtc(value);
  return d ? d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }) : "";
}

export function fmtDateTime(value) {
  const d = value instanceof Date ? value : parseUtc(value);
  if (!d) return "";
  const time = d.toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit" });
  return `${fmtDate(d)}, ${time}`;
}

export function plural(n, one, many = `${one}s`) {
  return `${n} ${n === 1 ? one : many}`;
}

export function fmtDistance(metres) {
  if (metres == null) return "";
  return metres < 1000 ? `${Math.round(metres)} m` : `${(metres / 1000).toFixed(1)} km`;
}

// Signal-lamp tones: clear = green, caution = yellow, danger = red, idle = grey.
export const TASK_STATUS = {
  open: { label: "Open", tone: "idle" },
  fix_submitted: { label: "Fix to review", tone: "caution" },
  closed: { label: "Closed", tone: "clear" },
};

export const AI_RESULT = {
  looks_fixed: { label: "Looks fixed", tone: "clear" },
  doubtful: { label: "Doubtful", tone: "danger" },
  needs_review: { label: "Needs a manual check", tone: "caution" },
};

export const INSPECTION_TYPE = { station: "Station", lc_gate: "LC gate", coach: "Coach" };

export function inspectionTitle(insp) {
  return `${INSPECTION_TYPE[insp.inspection_type] || insp.inspection_type} inspection`;
}

// "3 days overdue", "Due in 4 days", "Closed 6 Nov 2026"
export function deadlineInfo(task, now = new Date()) {
  if (task.status === "closed") return { text: `Closed ${fmtDate(task.closed_at)}`, overdue: false };
  const deadline = parseUtc(task.deadline);
  // count calendar days, so a deadline at any time tomorrow reads "Due tomorrow"
  const startOfDay = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const days = Math.round((startOfDay(deadline) - startOfDay(now)) / DAY);
  if (deadline < now) return { text: `${plural(Math.max(1, -days), "day")} overdue`, overdue: true };
  if (days === 0) return { text: "Due today", overdue: false };
  if (days === 1) return { text: "Due tomorrow", overdue: false };
  return { text: `Due in ${days} days`, overdue: false };
}

// The latest update from staff that carries a fix (after-photo or AI check).
export function lastFix(task) {
  return [...task.updates].reverse().find((u) => u.photo_key || u.verification?.result) || null;
}

// A task from the API only knows its observation. Attach the inspection (and so the station)
// it came from, and work out whether it is past its deadline.
export function enrichTasks(tasks, inspections, now = new Date()) {
  const byObservation = new Map();
  for (const insp of inspections) {
    for (const o of insp.observations) byObservation.set(o.id, insp);
  }
  return tasks.map((t) => {
    const inspection = byObservation.get(t.observation.id) || null;
    return {
      ...t,
      inspection,
      station: inspection ? inspection.location.name : "Unknown station",
      overdue: t.status !== "closed" && parseUtc(t.deadline) < now,
    };
  });
}
