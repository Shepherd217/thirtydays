"""
Supabase REST API client — replaces pg8000 direct Postgres connections.

Tables this app uses: users, grants, filings, notifications_log
All access is via the Supabase REST API (PostgREST) which handles IP allowlisting automatically.

Row Level Security (RLS) must be configured in Supabase for these tables:
  - users:   user can only see/edit own row (auth.uid() = id)
  - grants:  user can only see/edit own grants (auth.uid() = user_id)
  - filings: user can only see/edit own filings (via grants join)
  - notifications_log: user can only see/edit own logs
"""
import os
import requests

SUPABASE_URL = "https://qhmqijufbrsbwizzakjs.supabase.co"
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY', '')
HEADERS = {
    "apikey": SUPABASE_ANON_KEY,
    "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}


def _url(table):
    return f"{SUPABASE_URL}/rest/v1/{table}"


def _headers(extra=None):
    h = dict(HEADERS)
    if extra:
        h.update(extra)
    return h


# ── Query helpers ─────────────────────────────────────────────────────────────

def sb_select(table, params=None):
    """SELECT rows from table. params: dict of filters e.g. {'email': 'eq.test@x.com'}"""
    if not SUPABASE_ANON_KEY:
        return []
    try:
        r = requests.get(_url(table), headers=_headers(), params=params or {}, timeout=10)
        if r.status_code == 200:
            return r.json()
        # 406 = no rows matched filters, not an error
        if r.status_code == 406:
            return []
        print(f"[Supabase REST] GET {table} → {r.status_code}: {r.text[:200]}")
        return []
    except Exception as e:
        print(f"[Supabase REST] GET {table} error: {e}")
        return []


def sb_insert(table, data):
    """INSERT row into table. Returns the inserted row dict, or None on failure."""
    if not SUPABASE_ANON_KEY:
        return None
    try:
        r = requests.post(
            _url(table),
            headers=_headers({"Prefer": "return=representation"}),
            json=data,
            timeout=10,
        )
        if r.status_code in (200, 201, 204):
            result = r.json()
            if isinstance(result, list) and len(result) > 0:
                return result[0]
            return result if isinstance(result, dict) else None
        print(f"[Supabase REST] POST {table} → {r.status_code}: {r.text[:300]}")
        return None
    except Exception as e:
        print(f"[Supabase REST] POST {table} error: {e}")
        return None


def sb_update(table, filters, data):
    """UPDATE rows in table matching filters dict. Returns True on success."""
    if not SUPABASE_ANON_KEY:
        return False
    try:
        # Build filter string: "col1=eq.val1&col2=eq.val2"
        params = "&".join(f"{col}=eq.{val}" for col, val in filters.items())
        r = requests.patch(
            f"{_url(table)}?{params}",
            headers=_headers(),
            json=data,
            timeout=10,
        )
        if r.status_code in (200, 204, 206):
            return True
        print(f"[Supabase REST] PATCH {table} → {r.status_code}: {r.text[:200]}")
        return False
    except Exception as e:
        print(f"[Supabase REST] PATCH {table} error: {e}")
        return False


# ── App-level query wrappers (mimic the old pg8000 query_db interface) ─────────

def get_user_by_email(email):
    rows = sb_select("users", {"email": f"eq.{email}"})
    return rows[0] if rows else None


def get_user_by_id(user_id):
    rows = sb_select("users", {"id": f"eq.{user_id}"})
    return rows[0] if rows else None


def create_user(email):
    return sb_insert("users", {"email": email})


def get_user_grants(user_id):
    return sb_select("grants", {"user_id": f"eq.{user_id}", "order": "grant_date.desc"})


def get_grant_by_id(grant_id):
    rows = sb_select("grants", {"id": f"eq.{grant_id}"})
    return rows[0] if rows else None


def create_grant(user_id, grant_date, shares, strike_price, fm_value, grant_type, state, company):
    return sb_insert("grants", {
        "user_id": user_id,
        "grant_date": grant_date,
        "shares": shares,
        "strike_price": strike_price,
        "fair_market_value": fm_value,
        "grant_type": grant_type or "ISO",
        "state": state or "",
        "company_name": company or "",
    })


def update_grant(grant_id, data):
    return sb_update("grants", {"id": f"eq.{grant_id}"}, data)


def get_filing(grant_id):
    rows = sb_select("filings", {"grant_id": f"eq.{grant_id}"})
    return rows[0] if rows else None


def create_filing(grant_id):
    return sb_insert("filings", {"grant_id": grant_id, "status": "pending"})


def update_filing(grant_id, data):
    return sb_update("filings", {"grant_id": f"eq.{grant_id}"}, data)


def get_calendar_credentials(user_id):
    rows = sb_select("users", {"id": f"eq.{user_id}"})
    if not rows or not rows[0].get("calendar_token"):
        return None
    import json
    return json.loads(rows[0]["calendar_token"])


def update_user(user_id, data):
    return sb_update("users", {"id": f"eq.{user_id}"}, data)


def log_notification(user_id, grant_id, notification_type):
    sb_insert("notifications_log", {
        "user_id": user_id,
        "grant_id": grant_id,
        "notification_type": notification_type,
    })


def get_pending_grants_with_users():
    """Used by milestone checker — get all pending grants with user info."""
    if not SUPABASE_ANON_KEY:
        return []
    try:
        r = requests.get(
            f"{_url('grants')}",
            headers=_headers(),
            params={
                "select": "*,users:user_id(email,notification_email,notification_days,id)",
                "filings.status": "eq.pending",
                "or": "(filings.status.is.null,filings.status.eq.pending)",
            },
            timeout=10,
        )
        if r.status_code == 200:
            return r.json()
        return []
    except Exception as e:
        print(f"[Supabase REST] get_pending_grants error: {e}")
        return []