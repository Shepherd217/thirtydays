# ThirtyDays - 83(b) Election Deadline Tracker
import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from datetime import datetime, timedelta, date
import supabase_rest as sb
from pathlib import Path
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading
import re

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-prod')
# Use /tmp for the database on Vercel serverless (ephemeral read-only filesystem)
# Fall back to instance/ for local development
import os as _os
_VERCEL = _os.environ.get('VERCEL', '')
_BASE = '/tmp' if _VERCEL == '1' else Path(__file__).parent
DATABASE = Path(_BASE) / 'instance' / 'thirtydays.db'
# Ensure the directory exists before SQLite tries to write
DATABASE.parent.mkdir(parents=True, exist_ok=True)

# ── Email config (set via environment variables) ──────────────────────────────
SMTP_HOST = os.environ.get('SMTP_HOST', '')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASS = os.environ.get('SMTP_PASS', '')
FROM_NAME = os.environ.get('FROM_NAME', 'ThirtyDays')
FROM_EMAIL = os.environ.get('FROM_EMAIL', 'hello@thirtydays.app')
CALENDAR_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
CALENDAR_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
# ── Database (Supabase REST API — no IP allowlisting needed) ─────────────────
# All DB ops go through the Supabase REST API (PostgREST) which is always accessible.
# Required env vars:
#   SUPABASE_ANON_KEY  — from Supabase Dashboard → Project Settings → API

# ── Supabase REST client (see supabase_rest.py) ───────────────────────────────
# Database init — tables must exist in Supabase first. Run supabase_schema.sql
# in Supabase SQL Editor if you see "relation does not exist" errors.

# ── Core calculations ─────────────────────────────────────────────────────────
def calculate_savings(grant):
    if not grant.get('shares') or not grant.get('strike_price') or not grant.get('fair_market_value'):
        return {'amount': None, 'reason': 'missing_data', 'message': None}
    if grant.get('grant_type') == 'RSU':
        return {'amount': 0, 'reason': 'rsus_not_eligible', 'message': "83(b) elections don't apply to RSUs — you pay taxes as shares vest at FMV, not at a strike price."}
    full_tax = grant['shares'] * grant['fair_market_value'] * 0.37
    election_tax = grant['shares'] * grant['strike_price'] * 0.37
    return {'amount': max(0, full_tax - election_tax), 'reason': None, 'message': None}

def days_remaining(grant_date_str):
    deadline = datetime.strptime(grant_date_str, '%Y-%m-%d').date() + timedelta(days=30)
    return max(0, (deadline - date.today()).days)

def filing_deadline_date(grant_date_str):
    return (datetime.strptime(grant_date_str, '%Y-%m-%d').date() + timedelta(days=30)).strftime('%B %d, %Y')

def format_savings(amount):
    if amount is None:
        return None
    if amount >= 1_000_000:
        return f"${amount/1_000_000:.1f}M"
    if amount >= 1_000:
        return f"${amount/1_000:.0f}K"
    return f"${amount:.0f}"

# ── Email sending ──────────────────────────────────────────────────────────────
def send_email(to_email, subject, html_body):
    if not SMTP_HOST or not SMTP_USER:
        print(f"[EMAIL STUB] To: {to_email}\nSubject: {subject}\n{html_body[:200]}...")
        return True
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = f"{FROM_NAME} <{FROM_EMAIL}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(html_body, 'html'))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

def build_milestone_email(grant, user, days_left, savings):
    savings_amount = savings.get('amount') if isinstance(savings, dict) else savings
    savings_str = format_savings(savings_amount) if savings_amount else "significant"
    company = grant.get('company_name', 'your company')

    # Tone shifts with urgency
    if days_left == 30:
        title = "Your 83(b) countdown starts today"
        sub = f"You just received equity at {company}. You have exactly 30 days to file your 83(b) election — or pay a steep price."
        cta = "Add your grant details →"
        cta_url = f"https://thirtydays.app/dashboard?email={user['email']}"
        urgency_color = "#68d391"
    elif days_left == 21:
        title = f"Day 21 — {savings_str} on the line"
        sub = f"Two-thirds of your window is gone. {days_left} days left to file your 83(b). Once that window closes, there's no recovery."
        cta = "File now — it takes 10 minutes →"
        cta_url = f"https://thirtydays.app/grant/{grant['id']}/filing?email={user['email']}"
        urgency_color = "#68d391"
    elif days_left == 14:
        title = f"{days_left} days left — half your window is gone"
        sub = f"{company}: {savings_str} in potential tax savings. The IRS doesn't care that you're busy. File within 14 days or pay the difference forever."
        cta = "Start your filing walkthrough →"
        cta_url = f"https://thirtydays.app/grant/{grant['id']}/filing?email={user['email']}"
        urgency_color = "#f6ad55"
    elif days_left == 7:
        title = f"1 week left. {savings_str} at stake."
        sub = f"Seven days. After that, {company} equity becomes a tax liability instead of an asset. This is your final week to file."
        cta = "File now — it's worth 10 minutes →"
        cta_url = f"https://thirtydays.app/grant/{grant['id']}/filing?email={user['email']}"
        urgency_color = "#fc8181"
    elif days_left == 3:
        title = f"⚠️ {days_left} days left. {savings_str}."
        sub = f"This is your last real warning. Three days from now, your {company} equity stops being an option and starts being ordinary income. File today."
        cta = "File now →"
        cta_url = f"https://thirtydays.app/grant/{grant['id']}/filing?email={user['email']}"
        urgency_color = "#fc8181"
    elif days_left == 1:
        title = f"🚨 LAST DAY. File your 83(b) election NOW."
        sub = f"Today is the last day to file for {company}. Tomorrow, this window closes forever. Every share you vest will be taxed as ordinary income — not at your strike price."
        cta = "File right now →"
        cta_url = f"https://thirtydays.app/grant/{grant['id']}/filing?email={user['email']}"
        urgency_color = "#fc8181"
    else:
        return None  # Skip if not a milestone day

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{subject}</title>
    </head>
    <body style="margin:0;padding:0;background:#0a0f1e;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#e8eaed;">
        <div style="max-width:560px;margin:0 auto;padding:40px 20px;">
            <div style="font-size:18px;font-weight:800;margin-bottom:32px;">
                Thirty<span style="color:{urgency_color}">Days</span>
            </div>

            <div style="background:#111827;border:1px solid rgba(255,255,255,0.08);border-radius:16px;overflow:hidden;margin-bottom:24px;">
                <div style="height:4px;background:{urgency_color};"></div>
                <div style="padding:28px 32px;">
                    <div style="font-size:14px;font-weight:600;color:{urgency_color};text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">
                        {days_left} days remaining
                    </div>
                    <h1 style="font-size:24px;font-weight:800;margin:0 0 12px;color:#fff;line-height:1.3;">{title}</h1>
                    <p style="font-size:16px;line-height:1.6;color:#a0aec0;margin:0 0 24px;">{sub}</p>
                    <a href="{cta_url}" style="display:inline-block;background:{urgency_color};color:#0a0f1e;font-weight:700;font-size:15px;padding:14px 24px;border-radius:8px;text-decoration:none;">
                        {cta}
                    </a>
                </div>
            </div>

            <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:12px;padding:20px;margin-bottom:20px;">
                <div style="font-size:12px;color:#718096;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px;">What you stand to save</div>
                <div style="font-size:28px;font-weight:800;color:{urgency_color};">{savings_str}</div>
                <div style="font-size:13px;color:#718096;margin-top:4px;">If you file within {days_left} days</div>
            </div>

            <p style="font-size:13px;color:#4a5568;line-height:1.5;">
                You're receiving this because you signed up at ThirtyDays. 
                <a href="{cta_url}" style="color:#4299e1;">View your dashboard</a> · 
                <a href="https://thirtydays.app/unsubscribe?email={user['email']}" style="color:#4299e1;">Unsubscribe</a>
            </p>
        </div>
    </body>
    </html>"""
    return subject, html

# ── Milestone email scheduler ─────────────────────────────────────────────────
def run_milestone_check():
    """Called daily by APScheduler or Vercel cron. Sends milestone emails for grants due."""
    with app.app_context():
        # Fetch all grants with user info — filter in Python to avoid complex PostgREST OR queries
        all_grants = sb.sb_select("grants", {"select": "*,users(id,email,notification_email,notification_days)"})
        if not all_grants:
            return

        for grant in all_grants:
            user = grant.get("users")
            if not user or not isinstance(user, dict):
                continue

            user_id = user.get("id")
            if not user_id:
                continue

            # Skip if filed — fetch filing status
            filing = sb.get_filing(grant.get("id"))
            if filing and filing.get("status") not in (None, "pending", ""):
                continue

            days_left = days_remaining(grant["grant_date"])
            savings = calculate_savings(grant)
            notification_days_str = user.get("notification_days", "30,21,14,7,3,1")
            notification_days = [int(d) for d in notification_days_str.split(",")]

            if days_left in notification_days and user.get("notification_email"):
                result = build_milestone_email(grant, user, days_left, savings)
                if result:
                    subject, html = result
                    sent = send_email(user["email"], subject, html)
                    if sent:
                        sb.log_notification(user_id, grant["id"], f"milestone_day_{days_left}")
                        print(f"[MILESTONE] Sent Day {days_left} email to {user['email']} ({grant.get('company_name', '')})")

# ── Google Calendar OAuth ──────────────────────────────────────────────────────
def get_google_auth_url(user_id):
    from google_auth_oauthlib.flow import Flow
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": CALENDAR_CLIENT_ID,
                "client_secret": CALENDAR_CLIENT_SECRET,
                "redirect_uris": [CALENDAR_REDIRECT_URI],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=CALENDAR_SCOPES,
    )
    flow.redirect_uri = CALENDAR_REDIRECT_URI
    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
    session['oauth_state'] = auth_url.split('state=')[1] if 'state=' in auth_url else ''
    session['oauth_user_id'] = user_id
    return auth_url

def create_calendar_event(user_id, grant):
    creds_data = sb.get_calendar_credentials(user_id)
    if not creds_data:
        return None

    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials.from_authorized_user_info(creds_data, CALENDAR_SCOPES)
    service = build('calendar', 'v3', credentials=creds)

    deadline = datetime.strptime(grant['grant_date'], '%Y-%m-%d') + timedelta(days=30)
    savings = calculate_savings(grant)
    savings_amount = savings.get('amount') if isinstance(savings, dict) else savings
    savings_str = format_savings(savings_amount) if savings_amount else "tax savings"
    company = grant.get('company_name', 'Your company')

    # Create reminder events at multiple intervals
    reminders = [
        (deadline - timedelta(days=7), "1 week", "#f6ad55"),
        (deadline - timedelta(days=3), "3 days", "#fc8181"),
        (deadline, "TODAY — deadline", "#fc8181"),
    ]

    created_ids = []
    for reminder_date, label, color in reminders:
        if reminder_date.date() <= date.today():
            continue
        # user_email loaded from grant's embedded user or passed in
        user_email = ''
        if isinstance(grant.get('users'), dict):
            user_email = grant['users'].get('email', '')
        if not user_email:
            user = sb.get_user_by_id(user_id)
            user_email = user.get('email', '') if user else ''
        event = {
            'summary': f'⏰ 83(b) Filing: {company} — {savings_str} at stake',
            'location': 'IRS Filing Required',
            'description': f'''83(b) Election Deadline Reminder

Company: {company}
Deadline: {filing_deadline_date(grant['grant_date'])}
Shares: {grant.get('shares', 'N/A'):,}
Strike: ${grant.get('strike_price', 0):.4f}
FMV: ${grant.get('fair_market_value', 0):.2f}
Potential savings: {savings_str}

⚠️ This is a HARD DEADLINE. No extensions. No exceptions.

File at: https://thirtydays.app/grant/{grant['id']}/filing?email={user_email}
''',
            'start': {
                'dateTime': f'{reminder_date.strftime("%Y-%m-%d")}T09:00:00',
                'timeZone': 'America/New_York',
            },
            'end': {
                'dateTime': f'{reminder_date.strftime("%Y-%m-%d")}T09:30:00',
                'timeZone': 'America/New_York',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 60 * 24},  # 1 day before
                    {'method': 'email', 'minutes': 60 * 24 * 3},  # 3 days before
                ],
            },
            'colorId': '11' if 'TODAY' in label else ('6' if '3 days' in label else '7'),
        }
        created_event = service.events().insert(calendarId='primary', body=event).execute()
        created_ids.append(created_event['id'])
        # Small delay to avoid rate limiting
        import time; time.sleep(0.3)

    return created_ids

# ── Routes ─────────────────────────────────────────────────────────────────────
@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/api/health')
def api_health():
    """Health check — if this returns 200, Flask is running."""
    return jsonify({
        'status': 'ok',
        'env': os.environ.get('FLASK_ENV', 'not set'),
        'vercel': os.environ.get('VERCEL', 'not set'),
        'db': 'supabase',
    })

@app.route('/signup', methods=['POST'])
def signup():
    email = request.form.get('email', '').strip().lower()
    if not email or '@' not in email:
        flash('Please enter a valid email address.', 'error')
        return redirect(url_for('landing'))
    existing = sb.get_user_by_email(email)
    if existing:
        return redirect(url_for('dashboard', email=email))
    new_user = sb.create_user(email)
    if not new_user:
        # Race condition: another request created the user first
        existing = sb.get_user_by_email(email)
        if existing:
            return redirect(url_for('dashboard', email=email))
        flash('Something went wrong. Please try again.', 'error')
        return redirect(url_for('landing'))
    return redirect(url_for('add_grant', email=email, first='1'))

@app.route('/dashboard')
def dashboard():
    email = request.args.get('email', '')
    if not email:
        return redirect(url_for('landing'))
    user = sb.get_user_by_email(email)
    if not user:
        flash('User not found. Please sign up.', 'error')
        return redirect(url_for('landing'))
    grants = sb.get_user_grants(user['id'])
    for g in grants:
        g['days_remaining'] = days_remaining(g['grant_date'])
        g['filing_deadline'] = filing_deadline_date(g['grant_date'])
        g['savings'] = calculate_savings(g)
        g['filing'] = sb.get_filing(g['id'])
    return render_template('dashboard.html', user=user, grants=grants, email=email)

@app.route('/grant/new', methods=['GET', 'POST'])
def add_grant():
    email = request.args.get('email', '') or (request.form.get('email') if request.method == 'POST' else '')
    first_time = request.args.get('first', '')
    user = sb.get_user_by_email(email)
    if not user:
        return redirect(url_for('landing'))

    if request.method == 'POST':
        grant_date_str = request.form.get('grant_date', '')
        shares = request.form.get('shares', type=int) or None
        strike_price = request.form.get('strike_price', type=float) or None
        fm_value = request.form.get('fair_market_value', type=float) or None
        grant_type = request.form.get('grant_type', 'ISO')
        state = request.form.get('state', '')
        company = request.form.get('company_name', '')
        add_to_calendar = request.form.get('add_to_calendar', '')

        if not grant_date_str:
            flash('Grant date is required.', 'error')
            return render_template('add_grant.html', email=email, first=first_time, values=request.form)

        grant = sb.create_grant(user['id'], grant_date_str, shares, strike_price, fm_value, grant_type, state, company)
        if not grant:
            flash('Failed to save grant. Please try again.', 'error')
            return render_template('add_grant.html', email=email, first=first_time, values=request.form)

        grant_id = grant['id']
        sb.create_filing(grant_id)

        # Auto-create calendar event if connected
        if user.get('calendar_connected'):
            grant_with_user = sb.get_grant_by_id(grant_id)
            if grant_with_user:
                try:
                    event_ids = create_calendar_event(user['id'], grant_with_user)
                    if event_ids:
                        sb.update_grant(grant_id, {'calendar_event_id': ','.join(event_ids)})
                except Exception as e:
                    print(f"Calendar event creation failed: {e}")

        flash(f'Grant added! You have {days_remaining(grant_date_str)} days to file your 83(b) election.', 'success')
        return redirect(url_for('dashboard', email=email))

    return render_template('add_grant.html', email=email, first=first_time, values={})

@app.route('/grant/<int:grant_id>/filing', methods=['GET', 'POST'])
def filing_walkthrough(grant_id):
    email = request.args.get('email', '')
    user = sb.get_user_by_email(email)
    if not user:
        return redirect(url_for('landing'))

    grant = sb.get_grant_by_id(grant_id)
    if not grant or grant.get('user_id') != user['id']:
        flash('Grant not found.', 'error')
        return redirect(url_for('dashboard', email=email))

    grant['days_remaining'] = days_remaining(grant['grant_date'])
    grant['filing_deadline'] = filing_deadline_date(grant['grant_date'])
    grant['savings'] = calculate_savings(grant)
    filing = sb.get_filing(grant_id)

    if request.method == 'POST':
        action = request.form.get('action', '')
        if action == 'mark_filed':
            sb.update_filing(grant_id, {'filed_date': 'now', 'irs_submitted_date': 'now', 'status': 'filed'})
            flash('83(b) filed! You are protected. Every share you earn is taxed at your grant price.', 'success')
            sb.log_notification(user['id'], grant_id, 'grant_filed')
        elif action == 'confirm_irs':
            sb.update_filing(grant_id, {'irs_confirmed_date': 'now', 'status': 'confirmed'})
            flash('IRS confirmation logged. You are fully protected.', 'success')
        elif action == 'update_tracking':
            tracking = request.form.get('certified_mail_tracking', '')
            sb.update_filing(grant_id, {'certified_mail_tracking': tracking})
            flash('Certified mail tracking saved.', 'success')
        return redirect(url_for('filing_walkthrough', grant_id=grant_id, email=email))

    filing = sb.get_filing(grant_id)
    return render_template('filing.html', grant=grant, filing=filing, email=email)

# ── Settings ──────────────────────────────────────────────────────────────────
@app.route('/settings', methods=['GET', 'POST'])
def settings():
    email = request.args.get('email', '') or (request.form.get('email') if request.method == 'POST' else '')
    user = sb.get_user_by_email(email)
    if not user:
        return redirect(url_for('landing'))

    if request.method == 'POST':
        notification_email = 1 if request.form.get('notification_email') else 0
        email_digest = 1 if request.form.get('email_digest') else 0
        notification_days = ','.join(request.form.getlist('notification_days'))
        if not notification_days:
            notification_days = '30,21,14,7,3,1'

        sb.update_user(user['id'], {
            'notification_email': notification_email,
            'email_digest': email_digest,
            'notification_days': notification_days,
        })
        flash('Preferences saved.', 'success')
        return redirect(url_for('settings', email=email))

    # Google Calendar OAuth URL
    calendar_auth_url = None
    if CALENDAR_CLIENT_ID and CALENDAR_CLIENT_SECRET:
        try:
            calendar_auth_url = get_google_auth_url(user['id'])
        except Exception as e:
            print(f"Calendar OAuth error: {e}")

    notification_day_options = [int(d) for d in user['notification_days'].split(',')]
    return render_template('settings.html',
        user=user, email=email, calendar_auth_url=calendar_auth_url,
        notification_day_options=notification_day_options)

# ── Calendar OAuth callback ────────────────────────────────────────────────────
@app.route('/calendar/callback')
def calendar_callback():
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')

    if error:
        flash(f'Google Calendar connection failed: {error}', 'error')
        return redirect(url_for('landing'))

    if not code:
        return redirect(url_for('landing'))

    from google_auth_oauthlib.flow import Flow
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": CALENDAR_CLIENT_ID,
                "client_secret": CALENDAR_CLIENT_SECRET,
                "redirect_uris": [CALENDAR_REDIRECT_URI],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=CALENDAR_SCOPES,
    )
    flow.redirect_uri = CALENDAR_REDIRECT_URI
    flow.fetch_token(code=code)
    credentials = flow.credentials

    import json
    creds_json = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes,
    }

    user_id = session.get('oauth_user_id', 0)
    sb.update_user(user_id, {
        'calendar_connected': True,
        'calendar_token': json.dumps(creds_json),
    })
    user = sb.get_user_by_id(user_id)
    flash('Google Calendar connected! Your deadlines will appear as events.', 'success')
    return redirect(url_for('dashboard', email=user.get('email', '') if user else ''))

# ── Unsubscribe ────────────────────────────────────────────────────────────────
@app.route('/unsubscribe')
def unsubscribe():
    email = request.args.get('email', '')
    if email:
        # Find user and update notification_email to 0
        user = sb.get_user_by_email(email)
        if user:
            sb.update_user(user['id'], {'notification_email': False})
    return render_template('unsubscribed.html')

# ── API ────────────────────────────────────────────────────────────────────────
@app.route('/api/grants/<int:grant_id>')
def api_grant(grant_id):
    email = request.args.get('email', '')
    user = sb.get_user_by_email(email)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    grant = sb.get_grant_by_id(grant_id)
    if not grant or grant.get('user_id') != user['id']:
        return jsonify({'error': 'Not found'}), 404
    grant['days_remaining'] = days_remaining(grant['grant_date'])
    grant['savings'] = calculate_savings(grant)
    grant['filing'] = sb.get_filing(grant_id)
    return jsonify(grant)

# ── Cron endpoint (Vercel serverless cron) ───────────────────────────────────
@app.route('/api/cron/milestones')
def cron_milestones():
    """Called daily by Vercel Cron at 2pm ET (14:00 UTC).
    Vercel cron requests include a shared secret in headers for verification."""
    # Optional: verify Vercel cron secret
    import hashlib
    secret = os.environ.get('CRON_SECRET', '')
    if secret:
        expected = 'Bearer ' + secret
        if request.headers.get('Authorization', '') != expected:
            return jsonify({'error': 'Unauthorized'}), 401

    with app.app_context():
        run_milestone_check()
    return jsonify({'status': 'ok', 'action': 'milestone_check_complete'})

# ── Startup ───────────────────────────────────────────────────────────────────
# ── Vercel serverless: only run scheduler if NOT on Vercel ──────────────────
scheduler = None
if os.environ.get('VERCEL') != '1':
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        scheduler = BackgroundScheduler()
        scheduler.add_job(func=run_milestone_check, trigger='cron', hour=9, minute=0, id='milestone_check')
    except ImportError:
        pass

if __name__ == '__main__':
    # No init_db() needed — Supabase creates tables via supabase_schema.sql
    if scheduler:
        scheduler.start()
        print("[ThirtyDays] Milestone scheduler started — running daily at 9am ET")
    else:
        print("[ThirtyDays] Serverless mode — milestone cron handled by Vercel")
    app.run(host='0.0.0.0', port=5000, debug=True)