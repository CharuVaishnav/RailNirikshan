// Draft checklists for each inspection type (the JSON files are copied from mobile/assets/checklists).
import coach from "./coach.json";
import lcGate from "./lc_gate.json";
import station from "./station.json";

export const CHECKLISTS = { station, lc_gate: lcGate, coach };

// Summary of an inspection's checklist answers: { total, ok, notOk: [labels] }.
// Returns null when the inspection has no answers for the known checklist items.
export function checklistResult(inspection) {
  const items = CHECKLISTS[inspection.inspection_type]?.items || [];
  const answers = inspection.checklist || {};
  const answered = items.filter((item) => typeof answers[item.id] === "boolean");
  if (answered.length === 0) return null;
  const notOk = answered.filter((item) => answers[item.id] === false).map((item) => item.label);
  return { total: answered.length, ok: answered.length - notOk.length, notOk };
}
