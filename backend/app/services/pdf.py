"""Builds the inspection note as a PDF file, using the free fpdf2 library.

The PDF has the inspection details, the checklist result, the note as the officer approved it,
and every point with its department, status and the before / after photos.

Limit: the built-in PDF fonts only have Latin letters, so Hindi text is shown as "?" for now.
"""
import io
from datetime import datetime

from fpdf import FPDF
from fpdf.enums import XPos, YPos
from PIL import Image, ImageOps

NAVY = (27, 42, 74)
RED = (183, 49, 44)
INK = (30, 34, 42)
GREY = (95, 100, 110)
LINE = (205, 208, 214)

TYPE_NAMES = {"station": "Station inspection", "lc_gate": "Level crossing gate inspection",
              "coach": "Coach inspection"}
SWAPS = {"–": "-", "—": "-", "‘": "'", "’": "'", "“": '"', "”": '"',
         "•": "-", "…": "...", "₹": "Rs "}

PHOTO_W, PHOTO_H = 62, 46   # the box for one photo, in mm


def _plain(text) -> str:
    """Keep only what the built-in PDF fonts can print."""
    text = str(text or "")
    for symbol, simple in SWAPS.items():
        text = text.replace(symbol, simple)
    return text.encode("latin-1", "replace").decode("latin-1")


def _date(value: datetime | None, with_time: bool = False) -> str:
    if value is None:
        return "-"
    return value.strftime("%d %b %Y, %H:%M UTC" if with_time else "%d %b %Y")


def _label(item_id: str) -> str:
    return item_id.replace("_", " ").capitalize()


class NotePdf(FPDF):
    def __init__(self, title: str):
        super().__init__(format="A4")
        self.note_title = title
        self.set_margins(18, 16, 18)
        self.set_auto_page_break(True, margin=18)

    def header(self):
        self.set_fill_color(*NAVY)
        self.rect(0, 0, self.w, 12, style="F")
        self.set_xy(self.l_margin, 3)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 10)
        self.cell(0, 6, "RailNirikshan", new_x=XPos.LMARGIN, new_y=YPos.TOP)
        self.set_font("Helvetica", "", 9)
        self.cell(0, 6, _plain(self.note_title), align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_y(20)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*GREY)
        self.cell(0, 5, f"Generated on {_date(datetime.utcnow(), True)}", new_x=XPos.LMARGIN, new_y=YPos.TOP)
        self.cell(0, 5, f"Page {self.page_no()} of {{nb}}", align="R")

    # ---- small helpers -------------------------------------------------
    def heading(self, text: str):
        self.ln(3)
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(*NAVY)
        self.cell(0, 7, _plain(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(*LINE)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(2.5)

    def para(self, text: str, size: float = 10.5, style: str = "", colour=INK, height: float = 5.4):
        self.set_font("Helvetica", style, size)
        self.set_text_color(*colour)
        self.multi_cell(0, height, _plain(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def fact(self, label: str, value: str):
        self.set_font("Helvetica", "", 9.5)
        self.set_text_color(*GREY)
        self.cell(34, 6, _plain(label), new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*INK)
        self.multi_cell(0, 6, _plain(value), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def photo(self, data: bytes | None, x: float, y: float, caption: str) -> bool:
        """Draw one photo inside its box, keeping its shape. Returns False if it cannot be read."""
        if not data:
            return False
        try:
            img = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
            img.thumbnail((900, 900))   # a small JPEG keeps the PDF small
            jpeg = io.BytesIO()
            img.save(jpeg, "JPEG", quality=80)
            jpeg.seek(0)
        except Exception:               # not a real picture: leave it out, the note is still useful
            return False
        scale = min(PHOTO_W / img.width, PHOTO_H / img.height)
        w, h = img.width * scale, img.height * scale
        self.image(jpeg, x=x, y=y, w=w, h=h)
        self.set_xy(x, y + PHOTO_H + 0.5)
        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(*GREY)
        self.cell(PHOTO_W, 4.5, _plain(caption))
        return True


def _status_line(task, now: datetime) -> str:
    if task is None:
        return "Not sent to the department yet"
    if task.status == "closed":
        return f"Closed on {_date(task.closed_at)}"
    late = (now - task.deadline).days
    due = f"due {_date(task.deadline)}" + (f" ({late} days overdue)" if now > task.deadline else "")
    if task.status == "fix_submitted":
        return f"Fix sent by the department, waiting for review; {due}"
    level = f", escalation level {task.escalation_level}" if task.escalation_level else ""
    return f"Open, {due}{level}"


def build_note_pdf(insp, tasks_by_observation: dict, load_photo) -> bytes:
    """`tasks_by_observation` maps an observation id to its compliance task (if the note is issued).
    `load_photo(key)` returns the photo bytes or raises FileNotFoundError."""
    now = datetime.utcnow()
    issued = insp.status == "approved"
    kind = TYPE_NAMES.get(insp.inspection_type, _label(insp.inspection_type) + " inspection")

    def photo_bytes(key):
        if not key:
            return None
        try:
            return load_photo(key)
        except (FileNotFoundError, OSError):
            return None

    pdf = NotePdf(f"Inspection note no. {insp.id}")
    pdf.set_title(f"Inspection note {insp.id} - {_plain(insp.location.name)}")
    pdf.set_author("RailNirikshan")
    pdf.add_page()

    # ---- title and details ---------------------------------------------
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 9, "Inspection Note", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*INK)
    pdf.cell(0, 7, _plain(insp.location.name), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    if not issued:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*RED)
        pdf.cell(0, 6, "DRAFT - not approved, not sent to departments", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)

    officer = insp.officer.full_name + (f", {insp.officer.designation}" if insp.officer.designation else "")
    pdf.fact("Note number", str(insp.id))
    pdf.fact("Type", kind)
    pdf.fact("Division", insp.location.division)
    pdf.fact("Inspected on", _date(insp.created_at))
    pdf.fact("Inspected by", officer)
    pdf.fact("Issued on", _date(insp.approved_at) if issued else "Not issued")

    # ---- checklist -----------------------------------------------------
    checklist = insp.checklist or {}
    if checklist:
        not_ok = [_label(item) for item, ok in checklist.items() if not ok]
        pdf.heading("Checklist")
        pdf.para(f"{len(checklist) - len(not_ok)} of {len(checklist)} items were OK."
                 + (f" Not OK: {', '.join(not_ok)}." if not_ok else ""))

    # ---- the note as written -------------------------------------------
    pdf.heading("Note")
    if insp.note_text.strip():
        for line in insp.note_text.strip().split("\n"):
            if line.strip():
                pdf.para(line.strip())
                pdf.ln(1)
    else:
        pdf.para("The note has not been generated yet.", colour=GREY)

    # ---- every point with status and photos ----------------------------
    pdf.heading(f"Points and compliance ({len(insp.observations)})")
    if not insp.observations:
        pdf.para("No observations were recorded.", colour=GREY)
    for number, obs in enumerate(insp.observations, start=1):
        task = tasks_by_observation.get(obs.id)
        fix = None
        if task is not None:
            fix = next((u for u in reversed(task.updates) if u.photo_key), None)
        before, after = photo_bytes(obs.photo_key), photo_bytes(fix.photo_key if fix else None)
        if pdf.will_page_break(24 + (PHOTO_H + 8 if before or after else 0)):
            pdf.add_page()

        department = obs.suggested_department.name if obs.suggested_department else "Department not chosen"
        pdf.para(f"{number}. {obs.text}", size=10.5, style="B")
        point_id = f"Point #{task.id}   |   " if task is not None else ""
        pdf.para(f"{point_id}{department}   |   {_status_line(task, now)}", size=9.5, colour=GREY, height=5)
        if fix is not None and fix.remark:
            pdf.para(f"Department's reply: {fix.remark}", size=9.5, height=5)

        if before or after:
            y = pdf.get_y() + 1.5
            drawn = pdf.photo(before, pdf.l_margin, y, "Before (taken at inspection)")
            x_after = pdf.l_margin + (PHOTO_W + 6 if drawn else 0)
            drawn = pdf.photo(after, x_after, y, "After (sent by the department)") or drawn
            pdf.set_xy(pdf.l_margin, y + (PHOTO_H + 6 if drawn else 0))
        pdf.ln(3)

    # ---- signature -----------------------------------------------------
    if pdf.will_page_break(26):
        pdf.add_page()
    pdf.ln(10)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*INK)
    pdf.cell(0, 5, _plain(insp.officer.full_name), align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(*GREY)
    pdf.cell(0, 5, _plain(insp.officer.designation or "Inspecting Officer"), align="R",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    return bytes(pdf.output())
