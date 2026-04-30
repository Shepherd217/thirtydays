# ThirtyDays — Product Specification

## 1. Concept & Vision

**What it is:** A deadline tracker specifically for IRS Form 83(b) elections — the filing that lets startup employees pay taxes at their grant price instead of the much higher vest price.

**The core insight:** Startup employees get equity grants with a 30-day IRS filing window. Miss it and every share that vests costs them tens or hundreds of thousands in extra taxes. This is a hard deadline with zero tolerance — yet there's no tool that tracks it. People discover it late, forget it, or don't know it exists.

**Emotional core:** Fear + relief. The fear of unknowingly losing hundreds of thousands of dollars. The relief of knowing you're protected.

**Product personality:** Calm authority. We know something you don't and we're going to tell you once and clearly. Not panic-inducing, not corporate. Direct, clear, trustworthy.

---

## 2. Design Language

### Aesthetic Direction
Dark, premium, finance-forward. Think Bloomberg Terminal meets Linear.app. The darkness signals seriousness and focus. The typography and spacing signal quality.

### Color Palette
| Role | Hex | Usage |
|------|-----|-------|
| Background | `#0a0f1e` | Page background |
| Card | `#111827` | Surface/cards |
| Border | `rgba(255,255,255,0.08)` | Subtle dividers |
| Text Primary | `#e8eaed` | Body text |
| Text Muted | `#718096` | Labels, secondary |
| Blue | `#63b3ed` | Primary CTA, links |
| Blue Dim | `rgba(99,179,237,0.15)` | Blue backgrounds |
| Green | `#68d391` | Success, savings, protected |
| Green Dim | `rgba(104,211,145,0.15)` | Green backgrounds |
| Red | `#fc8181` | Danger, <7 days, urgency |
| Red Dim | `rgba(252,129,129,0.15)` | Red backgrounds |
| Amber | `#f6ad55` | Warning, 7-14 days |
| Amber Dim | `rgba(246,173,85,0.15)` | Amber backgrounds |

**Urgency escalation:**
- `> 14 days` → Green (calm, safe)
- `7–14 days` → Amber (attention needed)
- `< 7 days` → Red (act now)

### Typography
- **Font:** Inter (Google Fonts)
- **Weights used:** 400, 500, 600, 700, 800
- **Scale:**
  - Hero headline: `clamp(36px, 8vw, 64px)` / 800 weight
  - Section heading: `28px` / 800
  - Card title: `18px` / 700
  - Body: `16px` / 400
  - Label: `13px` / 700 / uppercase / letter-spacing 0.5px
  - Micro: `12px`

### Spatial System
- Base unit: 8px
- Card padding: `28px–32px`
- Section spacing: `40px–60px`
- Border radius: cards `14–16px`, buttons `9–10px`, inputs `10px`

### Motion Philosophy
- **Entrance:** Form submission buttons lift `translateY(-2px)` with shadow on hover
- **State change:** Color transitions at `0.15s ease`
- **No gratuitous animation** — motion serves function, not decoration
- Tab title countdown — browser tab updates dynamically so users always see urgency

### Visual Assets
- **No external images** — emoji as icons for speed and simplicity: 📅 ⏰ 💰 🏆 📋 🔔 ✉️
- No stock photography, no illustrations
- All styles inline in templates (no external CSS files needed for MVP)

---

## 3. Layout & Structure

### Pages

#### A. Landing Page (`/`)
- **Hero:** Giant headline with "30 days" highlighted in gradient. Subtitle explains the stakes in one sentence.
- **Pain callout:** Red-bordered box with real numbers — "$370,000 extra taxes" on a $1M vest. This is the aha moment compressed into 3 lines.
- **Email form:** Single field, one CTA. One-field signup minimizes friction.
- **Social proof:** "2,847 startup employees" (placeholder number, updates with real count post-launch)
- **Feature grid:** 4 cards (30-day countdown, step-by-step filing, peace of mind, savings shown). 2×2 on desktop, 1-col on mobile.
- **Disclaimer:** "Not tax or legal advice" clearly stated.

#### B. Add Grant (`/grant/new`)
- **Headline:** "Add Your Equity Grant" with urgency for first-time users.
- **Form:** Clean single-column form with 2-column grid for related fields.
- **Live savings calculator:** As user types shares/strike/FMV, the savings estimate appears in a green box above the submit button. Real-time feedback = the aha moment.
- **State dropdown:** All 50 states for 83(b) state filing requirement.
- **Grant type:** ISO / NSO / RSU / Restricted Stock selector.
- **Skip link:** "Skip for now" for users who only want deadline tracking.

#### C. Dashboard (`/dashboard`)
- **Header:** Logo + user email + settings link.
- **Grant cards** (one per grant):
  - Color-coded top border (green/amber/red based on urgency)
  - Giant countdown number (80px font)
  - "days remaining" label + filing deadline date
  - Savings banner (green) showing potential savings
  - Meta grid: shares, strike price, FMV, grant date
  - Checklist: grant recorded → deadline calculated → [urgent warning if ≤14 days] → IRS filing → state filing → IRS confirmation
  - "Start filing walkthrough" CTA
- **Protected state** (for filed grants):
  - Celebration banner with trophy icon
  - "You're Fully Protected" in green
  - Savings amount shown as "secured" not "potential"
  - Filing details
- **Empty state:** Friendly prompt to add first grant.
- **Tab title update:** Browser tab shows `⚠️ 12d — Acme | ThirtyDays` so the deadline is visible even when tabbed away.

#### D. Filing Walkthrough (`/grant/<id>/filing`)
- **Persistent countdown banner** at top (large days remaining + savings amount)
- **5 steps** (non-blocking checklist style):
  1. Your numbers (pre-filled from grant data, Form 8319 preview)
  2. Download Form 8319 (direct IRS.gov link)
  3. Where to mail (IRS address, private delivery service note, certified mail warning)
  4. State filing (reminder if state selected)
  5. Mark as filed + add certified mail tracking
- **Protected state:** Large celebration screen when status = 'filed' or 'confirmed', shows savings amount as "secured"

#### E. Settings (`/settings`)
- Email notification toggle
- Notification day checkboxes (30, 21, 14, 7, 3, 1 days)
- Google Calendar connect/disconnect button
- Email digest toggle

#### F. Unsubscribed (`/unsubscribe`)
- Simple confirmation page. "You've been unsubscribed from all email reminders."

---

## 4. Features & Interactions

### Core Features

**1. Email signup (one field)**
- Landing page → enter email → user created in DB → redirect to add_grant
- If email already exists, redirect to dashboard (no duplicate user)
- No password, no email verification (MVP simplicity — trust the email)

**2. Grant entry with live savings preview**
- Required: grant date (starts 30-day countdown immediately)
- Optional: shares, strike price, FMV (for savings calculator)
- Grant type: ISO / NSO / RSU / Restricted Stock
- Company name (for display)
- State (for state filing reminder)
- Real-time savings preview as user types (JS calculation, same formula as backend)
- On submit: grant + pending filing record created

**3. Live countdown dashboard**
- Giant days-remaining number, color-coded by urgency
- Savings calculator (if data complete)
- Non-blocking checklist showing what's done and what remains
- Tab title countdown so urgency is visible without switching tabs

**4. Step-by-step filing walkthrough**
- Pre-filled form preview (user's numbers in Form 8319 format)
- Direct IRS Form 8319 download link
- Exact IRS mailing address (Austin's correct address for elections)
- Certified mail return receipt warning (critical — no IRS confirmation otherwise)
- State filing reminder
- Mark as filed button (updates DB status)
- Certified mail tracking number entry
- "You're Protected" celebration screen on completion

**5. Email milestone reminders**
- Milestone days: 30, 21, 14, 7, 3, 1
- Each email: urgency-appropriate subject, savings amount at stake, direct CTA
- Dark-themed HTML email template matching the app aesthetic
- Skip logic: doesn't email if already filed or if user has disabled notifications

**6. Google Calendar integration**
- OAuth2 connect button in settings
- On connect: creates calendar events at -7d, -3d, and deadline day
- Each event: summary with savings at stake, description with deadline details and filing link

**7. IRS confirmation tracking**
- Mark IRS confirmed button (6-8 weeks after filing)
- Certified mail tracking number stored and displayed

### Interaction Details

**Form submission:**
- Button lifts `translateY(-2px)` on hover with shadow
- Loading state on submit (button text changes)
- Flash messages (success in green, error in red, info in blue) above main content
- Errors: specific inline messages, not generic alerts

**Savings calculator edge cases:**
- RSU: show info box explaining 83(b) elections don't apply to RSUs
- Missing data: show "enter your numbers above" prompt in savings slot
- Zero savings (strike price = FMV): show "$0 potential savings — your strike price equals FMV"

**Email notifications:**
- Sent daily at 9am ET via APScheduler (local dev) or Vercel cron
- Vercel cron endpoint at `/api/cron/milestones` with Bearer token auth
- Milestone check: iterate all grants, check days_remaining against notification_days for each user

**Calendar events:**
- Created on grant creation if user has calendar connected
- Events at -7 days, -3 days, deadline day
- Event description includes all grant details + filing URL
- Small delay between inserts to avoid Google API rate limiting

### Error States
- Invalid email: "Please enter a valid email address"
- Missing grant date: "Grant date is required"
- User not found: redirect to landing with flash
- Grant not found / wrong user: 404 flash + redirect to dashboard
- Email send failure: logged to console, doesn't break the app

### Empty States
- Dashboard no grants: friendly empty state with "Add my first grant" CTA
- Savings not calculable: info box explaining what's needed

---

## 5. Component Inventory

### Email Input
- `type="email"`, `placeholder="your@email.com"`, `autocomplete="email"`
- Focus: blue border + subtle blue background
- Invalid: red border + error message above

### Primary Button (CTA)
- Background: `linear-gradient(135deg, #63b3ed, #4299e1)`
- Color: `#0a0f1e`
- Hover: `translateY(-2px)` + shadow `rgba(99,179,237,0.35)`
- Full-width on mobile, auto-width on desktop

### Grant Card
- Background: `#111827`
- Border: `rgba(255,255,255,0.08)`
- Top accent line (3px) color-coded by urgency (green/amber/red gradient)
- Border-radius: 16px

### Countdown Number
- 80px / 800 weight / color based on urgency
- Used in dashboard grant card hero section

### Savings Banner
- Background: `rgba(104,211,145,0.15)`
- Border: `rgba(104,211,145,0.25)`
- Label: green uppercase 12px
- Amount: 32px / 800 / green
- Note: 12px muted

### Checklist Item
- Circle icon: green (done), blue (pending), red (urgent)
- Content: label (15px) + sub-label (13px muted)
- Bottom border separating items

### Protected Banner
- Full-width green-bordered celebration block
- Trophy emoji (48px)
- "You're Fully Protected" in green 28px
- Filing details + savings amount as "secured"

### Flash Message
- Success: green-dim background, green text
- Error: red-dim background, red text  
- Info: blue-dim background, blue text

### Milestone Email Template
- Dark background matching app (`#0a0f1e`)
- Urgency color-coded accent line at top of card
- Days remaining badge
- Subject and body tone shift with urgency
- Single CTA button with urgency color
- Savings amount prominently displayed
- Unsubscribe link at bottom

---

## 6. Technical Approach

### Stack
- **Python 3.11 + Flask 3.0** — lightweight, easy deployment
- **SQLite** — zero-config, auto-created per-instance
- **APScheduler** — daily milestone email job (local dev)
- **Vercel** — serverless deployment with cron for emails
- **google-auth-oauthlib + google-api-python-client** — Calendar OAuth
- **Vanilla HTML/CSS/JS** — no framework needed for MVP scope

### Database Schema

**users**
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| email | TEXT UNIQUE | |
| created_at | TIMESTAMP | |
| calendar_connected | INTEGER | 0/1 |
| calendar_token | TEXT | JSON blob |
| notification_email | INTEGER | 0/1, default 1 |
| notification_days | TEXT | CSV: "30,21,14,7,3,1" |
| email_digest | INTEGER | 0/1 |
| last_milestone_sent | TEXT | |

**grants**
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| user_id | INTEGER FK | |
| grant_date | DATE | Required |
| shares | INTEGER | Optional |
| strike_price | REAL | Optional |
| fair_market_value | REAL | Optional |
| grant_type | TEXT | ISO/NSO/RSU/Restricted Stock |
| state | TEXT | 2-letter code |
| company_name | TEXT | |
| calendar_event_id | TEXT | Comma-separated event IDs |
| created_at | TIMESTAMP | |

**filings**
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| grant_id | INTEGER UNIQUE FK | |
| filed_date | DATE | |
| irs_submitted_date | DATE | |
| irs_confirmed_date | DATE | |
| state_filed | INTEGER | 0/1 |
| state_filed_date | DATE | |
| certified_mail_tracking | TEXT | |
| status | TEXT | pending/filed/confirmed |

**notifications_log**
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| user_id | INTEGER FK | |
| grant_id | INTEGER | |
| notification_type | TEXT | e.g., "milestone_day_14" |
| sent_at | TIMESTAMP | |

### Key Implementation Notes
- Email identification: user找到 by email param in URL (?email=user@example.com). No auth tokens for MVP. In production, this should use a signed token.
- RSU handling: calculate_savings() returns None for RSU. Templates show info box explaining RSUs don't qualify for 83(b).
- Savings formula (ISO/NSO): `shares × (FMV − strike_price) × 0.37` (max with 0 floor)
- Deadline calculation: `grant_date + 30 days` (calendar days, not business days — IRS is clear about this)
- Google Calendar: OAuth2 flow, offline access token stored as JSON in DB
- Milestone emails: APScheduler runs daily at 9am ET; Vercel cron hits `/api/cron/milestones` at 2pm UTC

### API Design
- `POST /signup` — create user, redirect to add_grant
- `GET /dashboard?email=X` — show user's grants
- `POST /grant/new?email=X` — create grant
- `GET /grant/<id>/filing?email=X` — filing walkthrough
- `POST /grant/<id>/filing?email=X` — mark filed / update tracking
- `GET /settings?email=X` — user preferences
- `POST /settings?email=X` — update preferences
- `GET /calendar/callback` — OAuth callback
- `GET /api/grants/<id>?email=X` — JSON grant data
- `GET /api/cron/milestones` — daily milestone check (Vercel)
- `GET /unsubscribe?email=X` — one-click unsubscribe

### Deployment
- Vercel serverless Flask with `vercel.json`
- Cron job: daily at 14:00 UTC (9am ET) → hits `/api/cron/milestones`
- Environment variables: SMTP_*, GOOGLE_CLIENT_ID/SECRET, SECRET_KEY, CRON_SECRET

---

## 7. Revenue Model

### Individual Tiers
| Tier | Price | Features |
|------|-------|----------|
| Free | $0 | 1 grant, basic reminders, filing walkthrough |
| Pro | $20/mo | Unlimited grants, Google Calendar sync, SMS reminders, filing status tracking |

### B2B
| Plan | Price | Features |
|------|-------|----------|
| Team | $10/employee/mo | All Pro features + admin dashboard, CSV export, company-wide deadline visibility |
| Enterprise | $30/employee/mo | API access, Carta/Pulley integration, SSO, dedicated support |

---

## 8. What's Next (Post-MVP)

- [ ] Pro/free tier gating (add_grant disabled for free users after 1 grant)
- [ ] SMS reminders (Twilio integration)
- [ ] Carta/Pulley API auto-import
- [ ] Signed authentication tokens (replace email-in-URL)
- [ ] Payment (Stripe) for Pro/Team tiers
- [ ] "IRS confirmed" automated check via certified mail tracking API
