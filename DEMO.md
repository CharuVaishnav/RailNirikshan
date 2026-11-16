# RailNirikshan demo guide (practical)

Everything runs on the laptop, free, no internet needed except for the map tiles (OpenStreetMap).

All demo users have the password `demo123`: `officer`, `senior`, `admin`, `staff_elec`, `staff_engg`,
`staff_comm`, `staff_mech`, `staff_snt`, `staff_med`, `staff_sec`.

## 1. Before the practical (once, about 1 minute)

Open PowerShell in the project folder and load fresh demo data:

```powershell
cd backend
.venv\Scripts\python -m app.demo_seed --reset
```

Expected output: `Demo data ready: 10 inspections, 28 observations with photos.`
`--reset` wipes all inspections and tasks and creates them again with dates relative to today, so
run it again any time you have clicked around and want a clean start. Users and stations are kept.

Optional check that the backend is healthy: `.venv\Scripts\python -m pytest -q` should say `4 passed`.

## 2. Start everything (two PowerShell windows)

Window 1, backend (leave it running):

```powershell
cd backend
.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Window 2, dashboard (leave it running):

```powershell
cd dashboard
npm run dev
```

Minimise both windows. You never show them, but they must stay open: the dashboard gets all its data from the backend.

Open one browser tab: http://localhost:5173

If a port is "already in use", an old copy is still running. Close the old window or restart the laptop.

## 3. The demo script (screens only, about 4 minutes)

The whole demo happens in one browser tab. You sign in three times, once as each kind of user, and follow
one inspection point from the officer to the staff to the senior officer. No terminal or API page is shown.

Have two photos ready to upload. The demo photos work:
`backend\uploads\demo_01_before.jpg` and `backend\uploads\demo_01_after.jpg` (or use any two photos on the laptop).

If the browser asks to use your location, click **Allow** each time. The officer and staff screens attach GPS to
each photo. If you block it, everything still works, but the AI check will say "Needs a manual check".

### Part A: Inspecting officer (about 1.5 minutes)

1. Open http://localhost:5173. Username `officer`, password `demo123`, **Sign in**.
   Say: "This is the officer's view. It is one narrow column because officers use it on a phone."
2. **My inspections** shows 10 inspections. Click **New inspection** to show the form: choose a location, the
   inspection type, and the checklist (untick an item to mark it Not OK). Click **Back**; you will use the draft instead.
3. Click the first row, **Jaipur Junction** (Draft). The top shows the checklist result (11 of 12 items OK, the
   lighting item not OK). It already has two observations, each with a department suggested by AI (Electrical,
   Engineering). "The officer can change the department if the AI is wrong, or remove a wrong observation."
4. In **Add an observation**, type `Two lights not working on platform 3`, click **Add photo** and choose
   `demo_01_before.jpg`, then **Add observation**. A message says "Observation added. AI suggests Electrical."
5. Scroll to **Inspection note** and click **Generate inspection note**. The numbered note appears with the
   department after each point. "The officer can edit it before approving."
6. Click **Approve and send to departments**. The message says "Inspection approved. 3 points sent to departments."
   and the screen now shows the issued note and the three points, each Open with a 7-day deadline.
7. Click **Log out**.

### Part B: Department staff (about 1 minute)

1. Username `staff_elec`, password `demo123`, **Sign in**. The screen is **Electrical tasks**:
   "Staff only see their own department's points." The **To do** tab shows 4 points, including the two new ones
   from Jaipur Junction.
2. Click **Two lights not working on platform 3**. Show the route line (the point is "With department"),
   the before photo and the deadline.
3. In **Send your fix**, type `Replaced both LED fittings`, click **Add after-photo** and choose `demo_01_after.jpg`,
   then **Send fix for review**. The point moves to "Fix to review" and shows the AI check result.
4. Click **Log out**.

### Part C: Senior officer (about 1.5 minutes)

1. Username `senior`, password `demo123`, **Sign in**. The headline says **"7 fixes are waiting for your review"**
   and the strip shows **To review 7, Open 16, Overdue 6, Closed 6**. Point at the department chart and the map:
   "Every point from every inspection, by department and by location."
2. Click **Review fixes**. Click the last row, **Two lights not working on platform 3**: the before photo from the
   officer, the after photo from staff, and the AI check. Click **Accept fix**. "Fix accepted. Point #29 is closed."
3. Click the row "Road surface cracked and waterlogged near gate lodge wall". **AI check: Doubtful**, because the fix
   photo was taken 1.1 km from the spot. Click **Reject fix**, type a reason such as `Send a photo from the gate`,
   click **Reject fix** again. The point goes back to the department at escalation level 1.
4. Click the **Inspections** tab and then **Jaipur Junction** (16 Nov): the note the officer approved a minute ago,
   with its three points and their current status.
   Finish: "One point, three users, and nothing is closed without photo proof."

If you are short on time, stop after Part C step 2: the loop from officer to staff to senior officer is complete there.

## 4. What is real and what is a placeholder (if asked in the viva)

| Part | Today |
|---|---|
| Login, roles, inspections, tasks, accept/reject, escalation, dashboard | Working |
| Department routing | Working baseline: keyword rules (`backend/app/services/ai.py`); trained classifier planned for sprint 5 (04 – 24 Jan 2027) |
| Inspection note | Working template; local LLM (Ollama, Qwen 2.5 3B) planned for sprint 5 (04 – 24 Jan 2027) |
| Fix check | GPS distance check works; before/after image comparison planned for sprint 5 (04 – 24 Jan 2027) |
| Photo defect detection (YOLOv8) | Not trained yet (sprint 4, 14 Dec 2026 – 03 Jan 2027); the API returns no defects |
| Demo photos | Generated placeholder images, clearly labelled, not real station photos |
| Officer and staff screens | Working in the browser, laid out for a phone. Photo upload and GPS work; offline mode and voice notes are not built yet |
| Flutter app | The starter Flutter code is still in `mobile/` but is not used; Flutter is not installed on this laptop |

## 5. Dashboard code map (for the viva)

All dashboard code is in `dashboard/src/`:

| File | What it does |
|---|---|
| `App.jsx` | Top bar with the three tabs, loads the data once, decides which page shows |
| `pages/Overview.jsx` | Headline, summary strip, department chart, map, longest overdue, latest inspections |
| `pages/Points.jsx` | Compliance points: status tabs, search and filters, list on the left, details with Accept / Reject on the right |
| `pages/Inspections.jsx` | Inspection list, the inspection note and the points it raised |
| `pages/Login.jsx` | Sign-in page (the role from the login decides which screens open) |
| `pages/field/FieldApp.jsx` | Frame for the officer and staff screens: top bar, messages |
| `pages/field/Officer.jsx` | Officer: my inspections, new inspection with checklist, observations, generate note, approve |
| `pages/field/Staff.jsx` | Staff: department task list, task details, send fix with after-photo |
| `pages/field/parts.jsx` | Shared by both: photo chooser, GPS line, screen heading |
| `device.js` | GPS position and shrinking photos before upload |
| `checklists/*.json` | Draft checklists for station, LC gate and coach (copied from `mobile/assets/checklists`) |
| `components/ui.jsx` | Small shared pieces: status lamp, photo, photo zoom, list row |
| `components/StationMap.jsx` | The Leaflet / OpenStreetMap map |
| `format.js` | Dates, wording such as "3 days overdue", and joining tasks to their inspection |
| `api.js` | Calls to the backend with the login token |
| `styles.css` | All colours, fonts and layout |

The dashboard reads three backend endpoints (`/dashboard/summary`, `/tasks`, `/inspections`) and calls
`/tasks/{id}/close` or `/tasks/{id}/reject` for Accept and Reject. The officer screens call `/inspections` (create,
add observation, change department, generate note, approve) and the staff screens call `/tasks/{id}/fix`.
The backend was not changed for any of these screens.

## 6. If something goes wrong

- Dashboard jumps back to the sign-in page: the session ended, sign in again (tokens last 12 hours).
- Dashboard shows a red "Could not reach the server" bar: the backend window was closed. Start it again and click **Try again**.
- Dashboard is empty: run the `--reset` command in section 1 and refresh.
- `/docs` call returns 401 or 403: the token expired or you are logged in as the wrong user; repeat steps 1–2 of section 7.
- Map is grey: no internet for the map tiles. Everything else still works.

## 7. Optional: record an inspection through the API page

Only if asked. Do this after the main demo; it adds one inspection and two open points to the dashboard.

1. Open http://localhost:8000/docs. Open **POST /auth/login** → **Try it out** → body:
   `{"username": "officer", "password": "demo123"}` → **Execute**. Copy the `access_token` value (without quotes).
2. Click **Authorize** (top right), paste the token, **Authorize**, **Close**.
3. **POST /inspections** → Try it out → body `{"location_id": 1, "inspection_type": "station", "checklist": {}}` → Execute.
   Note the `id` in the response (it will be **11** after a fresh reset). "New inspection at Jaipur Junction."
4. **POST /inspections/{inspection_id}/observations** → Try it out → `inspection_id` = 11,
   `text` = `Two lights not working on platform 3`, `photo` = choose `backend\uploads\demo_01_before.jpg`
   (or any photo) → Execute.
   Show `"suggested_department": {"code": "ELEC", "name": "Electrical"}` in the response:
   "The AI suggested the department from the text."
5. Same call again with `text` = `Garbage near waiting hall` (no photo) → it suggests **Commercial**.
6. **POST /inspections/{inspection_id}/generate-note** → `inspection_id` = 11 → Execute.
   Show `note_text`: a numbered inspection note with the department after each point.
7. **POST /inspections/{inspection_id}/approve** → 11 → Execute. Status becomes `approved`:
   "On approval, each point becomes a task for its department with a 7-day deadline."
8. Refresh the dashboard: **Inspections** goes up by 1 and **Open** by 2.

## 8. Testing on a real phone (officer and staff screens)

A phone browser only allows the camera and GPS on an `https://` address, so there is a separate start command
for phone testing. The phone and the laptop must be on the same Wi-Fi.

1. Window 1, backend, as in section 2.
2. Window 2, instead of `npm run dev`:

   ```powershell
   cd dashboard
   npm run dev:phone
   ```

   It prints two addresses. Note the **Network** one, for example `https://192.168.0.8:5173/`
   (the number is your laptop's Wi-Fi address and can change from day to day).
3. On the phone, open that Network address in Chrome.
4. Chrome warns that the connection is not private, because the certificate is made by your own laptop.
   Tap **Advanced**, then **Proceed**. This is expected, and safe only on your own Wi-Fi for testing.
5. Sign in as `officer` / `demo123`. When asked, allow **Camera** and **Location**.
6. Record an inspection: **Add photo** now opens the camera, and the line under it should say
   "Your location will be attached".

If the page does not open on the phone:

- Windows may ask whether Node.js can accept connections. Choose **Allow** for private networks.
  If you missed the question, open *Windows Security > Firewall & network protection > Allow an app through
  firewall* and tick Node.js for Private.
- Check that the phone is on the same Wi-Fi as the laptop, not on mobile data.
- College or hostel Wi-Fi often blocks devices from seeing each other. Use your phone's hotspot for the laptop,
  or a home router.

For the practical itself keep using `npm run dev` on the laptop: the phone mode is for testing the camera and GPS.
