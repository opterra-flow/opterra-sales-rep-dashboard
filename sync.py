#!/usr/bin/env python3
"""Fetch ALL contacts from GHL with state data and embed into index.html"""
import json, os, re, subprocess, time

API = "https://services.leadconnectorhq.com"
KEY = os.environ.get("GHL_KEY", "")
LOC = os.environ.get("GHL_LOCATION_ID", "i9NF6R1xk7vXmT8NUW3B")

FIELD_MAP = {
    "wap95mRbxqOLLgN4p90a":"business_segment","w0BJpuVi963KKQo9hoLn":"primary_service",
    "fMbniEKDtWpv0iTjHm12":"all_services","gztgSJnfW0y3EVpWi5QN":"pain_points",
    "JYje4syvoHhrwZl7soAR":"owner_title","Ym2RPGNnnbsCTMh1cSmx":"owner_credentials",
    "K5XqlEJdQSgw6qmmAHdh":"years_in_business","ysxkj83Q4uoZCf7ovB31":"team_size",
    "9ry2up0DA8kGj62rYiGs":"unique_differentiator","SDtrLvQ0MgjJCRxZFitn":"target_audience",
    "GEm6To648pXoZKGAhjEn":"specialties","NPsCC6osbYvqmHZFA2QM":"certifications",
    "eAqRmBDxJlWmvv9cdQ6s":"new_patient_offer","YWwvzqTMM8kG8mX0Cbsd":"google_rating",
    "UNmQis5xQxR1y2ocgkDl":"review_count","y47c7XwyyMQdzZVdWJSN":"tone_of_brand",
    "esqr5WZGWCpqhDZ3NtV0":"personalization_hooks","nlpRTzYDHUQUVhLvZSBS":"mission_statement",
}

# Normalize state names
STATE_MAP = {
    "georgia":"Georgia","ga":"Georgia","florida":"Florida","fl":"Florida",
    "texas":"Texas","tx":"Texas","new york":"New York","ny":"New York",
    "michigan":"Michigan","mi":"Michigan","illinois":"Illinois","il":"Illinois",
    "tennessee":"Tennessee","tn":"Tennessee","ohio":"Ohio","oh":"Ohio",
    "virginia":"Virginia","va":"Virginia","maryland":"Maryland","md":"Maryland",
    "california":"California","ca":"California","nc":"North Carolina",
    "north carolina":"North Carolina","pennsylvania":"Pennsylvania","pa":"Pennsylvania",
    "district of columbia":"District of Columbia","dc":"District of Columbia",
    "kentucky":"Kentucky","ky":"Kentucky","new jersey":"New Jersey","nj":"New Jersey",
    "alabama":"Alabama","al":"Alabama","louisiana":"Louisiana","la":"Louisiana",
    "indiana":"Indiana","in":"Indiana","minnesota":"Minnesota","mn":"Minnesota",
    "arizona":"Arizona","az":"Arizona","colorado":"Colorado","co":"Colorado",
    "west virginia":"West Virginia","wv":"West Virginia","iowa":"Iowa","ia":"Iowa",
    "washington":"Washington","wa":"Washington",
}

def fetch_json(url):
    r = subprocess.run(['curl', '-s', url,
        '-H', f'Authorization: Bearer {KEY}',
        '-H', 'Version: 2021-07-28',
        '-H', 'Content-Type: application/json'
    ], capture_output=True, text=True)
    return json.loads(r.stdout)

def parse_contact(c):
    cf = {}
    for f in c.get("customFields", []):
        if f.get("id") in FIELD_MAP and f.get("value"):
            cf[FIELD_MAP[f["id"]]] = str(f["value"]).strip()
    tags = [t for t in (c.get("tags") or []) if t not in ("optiflow",)]
    raw_state = (c.get("state") or "").strip()
    norm_state = STATE_MAP.get(raw_state.lower(), raw_state)
    return {
        "name": ((c.get("firstNameRaw") or c.get("firstName") or "") + " " + (c.get("lastNameRaw") or c.get("lastName") or "")).strip() or c.get("contactName", ""),
        "company": c.get("companyName", "") or "",
        "city": (c.get("city") or "").strip(),
        "state": norm_state,
        "phone": c.get("phone", "") or "",
        "email": c.get("email", "") or "",
        "website": c.get("website", "") or "",
        "tags": tags,
        "added": (c.get("dateAdded") or "")[:10],
        "ghlId": c.get("id", ""),
        "outreach": "",
        "stage": "",
        "cf": cf,
    }

# Fetch all contacts (list endpoint)
print("Fetching all contacts from GHL...")
all_raw = []
url = f"{API}/contacts/?locationId={LOC}&limit=100"
page = 0
while url and page < 15:
    page += 1
    data = fetch_json(url)
    contacts = data.get("contacts", [])
    all_raw.extend(contacts)
    url = data.get("meta", {}).get("nextPageUrl")
    print(f"  Page {page}: {len(contacts)} contacts (total: {len(all_raw)})")

# Filter to contacts that have a state
with_state = [c for c in all_raw if (c.get("state") or "").strip()]
print(f"\nContacts with state: {len(with_state)} / {len(all_raw)}")

# Fetch details for all contacts with state
result = []
for i, c in enumerate(with_state):
    cid = c["id"]
    try:
        full = fetch_json(f"{API}/contacts/{cid}").get("contact", c)
    except:
        full = c
    result.append(parse_contact(full))
    if (i + 1) % 25 == 0:
        print(f"  Details: {i+1}/{len(with_state)}")

# State breakdown
states = {}
for r in result:
    s = r["state"]
    states[s] = states.get(s, 0) + 1
print(f"\nTotal contacts with details: {len(result)}")
print("By state:")
for s, count in sorted(states.items(), key=lambda x: -x[1]):
    print(f"  {s}: {count}")

# Embed into HTML
with open("index.html", "r") as f:
    html = f.read()

# Replace the data — now it's allContacts instead of floridaContacts
old_data = re.search(r"var allContacts = \[.*?\];", html, re.DOTALL)
if not old_data:
    # Try old format
    old_data = re.search(r"var floridaContacts = \[.*?\];", html, re.DOTALL)

if old_data:
    new_js = "var allContacts = " + json.dumps(result, ensure_ascii=False) + ";"
    html = html[:old_data.start()] + new_js + html[old_data.end():]

    # Inject env vars
    html = html.replace("%%GHL_API_KEY%%", KEY)
    html = html.replace("%%GHL_LOCATION_ID%%", LOC)
    html = html.replace("%%GHL_PIPELINE_ID%%", os.environ.get("GHL_PIPELINE_ID", "BjOb6oh133vA1zjVZMjJ"))

    with open("index.html", "w") as f:
        f.write(html)
    print(f"\nEmbedded {len(result)} contacts into index.html")
    print("Injected env vars")
else:
    print("ERROR: Could not find contact data in HTML")
    exit(1)
