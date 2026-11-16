"""Check for overdue points once: raise their escalation level and send reminder emails.

Run from the backend folder:  python -m app.escalate

Windows Task Scheduler can run this every hour (see README.md, "Free email alerts").
The rules are in services/escalation.py.
"""
from .database import SessionLocal, ensure_schema
from .services import escalation


def main() -> None:
    ensure_schema()
    db = SessionLocal()
    try:
        result = escalation.run(db)
    finally:
        db.close()
    print(f"{result['overdue']} open point(s) are overdue. Escalated now: {result['escalated']}. "
          f"Emails sent: {result['emails_sent']}"
          + ("." if result["email_on"] else " (email is switched off: set SMTP_USER in backend/.env)."))
    for p in result["points"]:
        print(f"  point #{p['id']}  {p['department']}  ->  level {p['level']}")


if __name__ == "__main__":
    main()
