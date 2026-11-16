# RailNirikshan

AI-powered smart inspection and compliance system for Indian Railways (final year project, proposed for NWR).

Officers record inspections on a phone with checklists, photos and GPS. The system suggests the department for
each point and writes the inspection note. Staff fix issues and upload photo proof, the system checks the fix,
and senior officers track everything on a dashboard.

## Project structure

```
RailNirikshan/
├── backend/      FastAPI server: login and roles, inspections, compliance tasks, escalation, dashboard (Python)
├── dashboard/    Web app for all three users: officer screens, staff screens, senior officer dashboard (React)
├── ml/           Scripts for the AI models: defect detection, speech, notes, routing, verification (Python)
├── mobile/       Starter Flutter app. Not used: the officer and staff screens are now in dashboard/
├── srs_diagrams/ Diagrams used in the SRS
├── DEMO.md       How to start everything and the click-by-click demo script
└── docker-compose.yml   optional PostgreSQL for deployment
```

The college documents (SRS, project abstract, functional requirements) are kept on the developer's laptop and
are not part of this repository.

## Cost: zero

Everything is free and open-source. Models are trained on the free GPU in Google Colab or Kaggle and run on a
normal CPU (no paid AI APIs). Data goes in SQLite (PostgreSQL when deployed), photos on the server disk, maps
from OpenStreetMap, and alerts by email instead of SMS.

## What you need installed

| Tool | Version | Used for |
|---|---|---|
| Python | 3.11 or later | backend and ML scripts |
| Node.js | 20 LTS or later | web app |
| Git | any | version control |
| Ollama | any recent | small local LLM for AI notes (from sprint 5) |
| PostgreSQL or Docker Desktop | 16 | database for deployment only (sprint 6) |

## Run it

### 1. Backend (first time)

```bash
cd backend
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt     # Linux/macOS: .venv/bin/python
copy .env.example .env                                       # Linux/macOS: cp
.venv\Scripts\python -m app.demo_seed --reset                # users, stations and realistic demo data
.venv\Scripts\python -m pytest -q                            # should say "3 passed"
```

Start it (every time):

```bash
.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

`python -m app.seed` loads only the departments, users and locations. `python -m app.demo_seed --reset` also
loads 10 demo inspections with photos and tasks in every state; run it again whenever you want a clean demo.

### 2. Web app

```bash
cd dashboard
npm install        # first time only
npm run dev
```

Open http://localhost:5173. The account you sign in with decides which screens open (password `demo123`):

| Username | Screens |
|---|---|
| `officer` | Inspecting officer: my inspections, new inspection with checklist, observations, note, approve |
| `staff_elec`, `staff_engg`, `staff_comm`, `staff_mech`, `staff_snt`, `staff_med`, `staff_sec` | Department staff: the department's points, send a fix with an after-photo |
| `senior` | Senior officer dashboard: overview, compliance points, inspections |
| `admin` | Same dashboard as the senior officer |

### 3. Test on a real phone

```bash
cd dashboard
npm run dev:phone
```

This serves the web app over HTTPS on the laptop's Wi-Fi address (a phone only allows camera and GPS on https).
Steps and troubleshooting are in section 8 of `DEMO.md`.

### 4. Local LLM for AI notes (sprint 5)

Install Ollama from ollama.com (free), then:

```bash
ollama pull qwen2.5:3b      # about 2 GB, runs on a normal CPU; on a slow laptop use qwen2.5:1.5b
```

Set `OLLAMA_URL=http://localhost:11434` in `backend/.env`. Until then, notes use a simple template.

### 5. Free email alerts (sprint 3)

In `backend/.env`, set `SMTP_USER` and `SMTP_PASSWORD` (for Gmail: turn on 2-step verification and create an
app password). Give staff users an email address, then call `POST /tasks/run-escalation` every hour
(Windows Task Scheduler or cron). Overdue points are escalated and the department staff get an email.

### 6. PostgreSQL for deployment (sprint 6)

SQLite is fine while building. For the field test, install PostgreSQL (or run `docker compose up -d db`), then in
`backend/.env` set:

```
DATABASE_URL=postgresql+psycopg://rail:rail@localhost:5432/railnirikshan
```

and run `python -m app.seed` again.

## What works today and what is planned

| Part | Status |
|---|---|
| Login with roles; officer, staff and senior officer screens | Working |
| Inspection with checklist, observations with photo and GPS, remove a wrong observation | Working |
| Department suggestion | Working with keyword rules (`backend/app/services/ai.py`); trained classifier in sprint 5 |
| Inspection note | Working with a template; local LLM in sprint 5 |
| Compliance tasks, fix with after-photo, accept / reject, escalation level | Working |
| Fix check | GPS distance works; before / after photo comparison in sprint 5 |
| Photo defect detection (YOLOv8) | Sprint 4; no trained model yet |
| Voice to text | Sprint 5 |
| Email alerts on a schedule, PDF export of the note | Sprint 3 |
| Admin screens for users, departments and locations | Not built; master data comes from the seed scripts |
| Offline mode, repeated-issue finder | Only if time permits |

## How the AI plugs in

All AI calls live in `backend/app/services/ai.py`. Each function already has a simple working version
(keyword routing, template notes, GPS-based fix check), so the app works end to end.
Build the real models in `ml/` and swap them in one at a time (see `ml/README.md`).

## Workflow

- Commit small changes and push to GitHub every day.
- Run `pytest -q` before merging, and tag each milestone.
- Follow the six sprints of the project plan (20 Oct 2026 to 15 Feb 2027).

## Important

- Never commit `.env`, real inspection data or photos from the railways.
- Remove names and personal details from any sample documents before using them for training.
