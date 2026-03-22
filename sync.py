#!/usr/bin/env python3
"""Fetch all Florida contacts from GHL and embed into index.html"""
import json, os, re, subprocess

API = "https://services.leadconnectorhq.com"
KEY = os.environ.get("GHL_KEY", "")
LOC = "i9NF6R1xk7vXmT8NUW3B"

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

def fetch_json(url):
    import subprocess as sp
    r = sp.run(['curl', '-s', url,
        '-H', f'Authorization: Bearer {KEY}',
        '-H', 'Version: 2021-07-28',
        '-H', 'Content-Type: application/json'
    ], capture_output=True, text=True)
    return json.loads(r.stdout)

# Fetch all contacts
all_contacts = []
url = f"{API}/contacts/?locationId={LOC}&limit=100"
page = 0
while url and page < 15:
    page += 1
    data = fetch_json(url)
    all_contacts.extend(data.get("contacts", []))
    url = data.get("meta", {}).get("nextPageUrl")
    print(f"Page {page}: {len(data.get('contacts', []))} contacts")

# Filter Florida
florida = [c for c in all_contacts if (c.get("state") or "").lower().strip() in ("florida", "fl")]
print(f"\nFlorida contacts: {len(florida)}")

# Fetch details
result = []
for i, c in enumerate(florida):
    cid = c["id"]
    try:
        full = fetch_json(f"{API}/contacts/{cid}").get("contact", c)
    except:
        full = c
    cf = {}
    for f in full.get("customFields", []):
        if f.get("id") in FIELD_MAP and f.get("value"):
            cf[FIELD_MAP[f["id"]]] = str(f["value"]).strip()
    tags = [t for t in (full.get("tags") or []) if t not in ("optiflow",)]
    result.append({
        "name": ((full.get("firstNameRaw") or full.get("firstName") or "") + " " + (full.get("lastNameRaw") or full.get("lastName") or "")).strip() or full.get("contactName", ""),
        "company": full.get("companyName", "") or "",
        "city": (full.get("city") or "").strip(),
        "phone": full.get("phone", "") or "",
        "email": full.get("email", "") or "",
        "website": full.get("website", "") or "",
        "tags": tags,
        "added": (full.get("dateAdded") or "")[:10],
        "ghlId": cid,
        "outreach": "",
        "stage": "",
        "cf": cf,
    })
    if (i + 1) % 10 == 0:
        print(f"  Fetched details: {i+1}/{len(florida)}")

print(f"Fetched details for all {len(result)} contacts")

# Embed into HTML
with open("index.html", "r") as f:
    html = f.read()

old_data = re.search(r"var floridaContacts = \[.*?\];", html, re.DOTALL)
if old_data:
    new_js = "var floridaContacts = " + json.dumps(result, ensure_ascii=False) + ";"
    html = html[:old_data.start()] + new_js + html[old_data.end():]
    with open("index.html", "w") as f:
        f.write(html)
    print(f"\nEmbedded {len(result)} contacts into index.html")
else:
    print("ERROR: Could not find floridaContacts in HTML")
    exit(1)
