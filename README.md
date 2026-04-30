# ThirtyDays — 83(b) Election Deadline Tracker

An MVP Flask app that helps startup employees never miss their 30-day 83(b) election deadline.

## What it does

- **Tracks equity grants** and counts down the 30-day IRS filing window
- **Shows tax savings** in real-time as you enter grant details
- **Guides step-by-step** through filing Form 8319 with the IRS
- **Protects users** with reminders at 28, 21, 14, 7, 3, and 1 days

## Quick Start

```bash
cd /home/kandi/thirtydays
pip install -r requirements.txt
python app.py
```

Then open **http://localhost:5000**

## Project Structure

```
thirtydays/
├── app.py              # Flask app, routes, database
├── requirements.txt    # Dependencies
├── thirtydays.db       # SQLite database (created on first run)
├── templates/
│   ├── landing.html    # Zero-friction email signup
│   ├── dashboard.html  # Grant tracking + countdown
│   ├── add_grant.html  # Grant entry form
│   └── filing.html     # Step-by-step filing walkthrough
└── static/             # (reserved for CSS/JS)
```

## User Flow

1. **Landing page** → enter email → immediately see the problem (30-day deadline)
2. **Add grant** → enter grant date, shares, strike price, FMV → see potential savings
3. **Dashboard** → giant countdown + checklist + savings amount
4. **Filing walkthrough** → download Form 8319, see where to mail, mark as filed

## What's Included

- SQLite database (auto-created)
- Email-based user identification (no passwords needed for MVP)
- Real-time savings calculator
- Filing status tracking
- Protected state ("You're Protected") celebration

## What to Add Next

- [ ] Google Calendar OAuth integration (add to calendar with one click)
- [ ] Email notification service (APScheduler + Flask-Mail)
- [ ] Carta/Pulley API integration (auto-import grants)
- [ ] SMS reminders for <7 days
- [ ] Pro/free tier gating
- [ ] Company admin dashboard

## Tech Stack

- Python 3.11 + Flask
- SQLite (zero config)
- Vanilla HTML/CSS/JS (no framework needed for MVP)
