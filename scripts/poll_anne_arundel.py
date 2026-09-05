"""
poll_anne_arundel.py
Deterministic Ingestion Poller: Anne Arundel County Council Zoning Legislation (Article 18)
Swapp Technologies LLC (Maryland)

Invariant: Zero model in the path (Rule 10). Hard generation rule only.
Extracts mechanically from official county legislative portal.
"""

import os
import sys
import re
import urllib.request
import ssl
import hashlib
from datetime import datetime, timezone
from bs4 import BeautifulSoup

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AA_DIR = os.path.join(ROOT_DIR, "anne_arundel", "council_bills")
PORTAL_URL = "https://www.aacounty.org/county-council/legislation"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

UA = os.environ.get("ENACTED_USER_AGENT", "EnactedCorpusBot/1.0 (+https://github.com/[FOUNDER: org]/enacted-state-md; contact: [FOUNDER: contact email])")
HEADERS = {"User-Agent": UA}

def poll():
    print(f"[Anne Arundel Poller] Polling legislation portal {PORTAL_URL}...")
    try:
        req = urllib.request.Request(PORTAL_URL, headers=HEADERS)
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            if resp.status != 200:
                print(f"ERROR: HTTP {resp.status} from {PORTAL_URL}", file=sys.stderr)
                sys.exit(1)
            html_content = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"ERROR: Failed fetching Anne Arundel portal ({PORTAL_URL}): {e}", file=sys.stderr)
        sys.exit(1)

    soup = BeautifulSoup(html_content, "html.parser")
    rows = soup.find_all("tr")
    print(f"[Anne Arundel Poller] Parsed {len(rows)} table rows from portal.")
    
    updated_count = 0
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for row in rows:
        text = row.get_text(" ", strip=True)
        if "zoning" not in text.lower() and "article 18" not in text.lower():
            continue
            
        m = re.search(r"Bill\s*(?:No\.)?\s*(\d{1,3}-\d{2})", text, re.IGNORECASE)
        if not m:
            continue
            
        bill_no = m.group(1)
        stem = f"bill_{bill_no.replace('-', '_')}"
        target_md = os.path.join(AA_DIR, f"{stem}.md")
        
        if os.path.exists(target_md):
            continue
            
        # Find PDF link in row
        link_tag = row.find("a", href=re.compile(r"\.pdf$", re.IGNORECASE))
        if not link_tag or not link_tag.get("href"):
            print(f"WARNING: Bill {bill_no} found without direct PDF link selector in portal row.", file=sys.stderr)
            continue
            
        pdf_href = link_tag.get("href")
        if pdf_href.startswith("/"):
            pdf_url = f"https://www.aacounty.org{pdf_href}"
        else:
            pdf_url = pdf_href

        # Fetch PDF under hard generation rule
        try:
            pdf_req = urllib.request.Request(pdf_url, headers=HEADERS)
            with urllib.request.urlopen(pdf_req, context=ctx, timeout=15) as presp:
                if presp.status != 200:
                    print(f"WARNING: Bill {bill_no} PDF returned HTTP {presp.status} at {pdf_url}", file=sys.stderr)
                    continue
                pdf_data = presp.read()
                if not pdf_data.startswith(b"%PDF-"):
                    print(f"WARNING: Content at {pdf_url} is not valid PDF", file=sys.stderr)
                    continue
                sha256_hash = hashlib.sha256(pdf_data).hexdigest()
        except Exception as pe:
            print(f"WARNING: Failed fetching PDF for Bill {bill_no}: {pe}", file=sys.stderr)
            continue

        frontmatter = f"""---
bill_number: "Bill No. {bill_no}"
legislative_body: "County Council of Anne Arundel County, Maryland"
title: "AN ORDINANCE concerning: Zoning"
action_status: "Introduced"
primary_source_url: "{pdf_url}"
source_sha256: "{sha256_hash}"
source_fetched_at: "{now_iso}"
jurisdiction: "Anne Arundel County, MD"
---
# Anne Arundel County Council Bill No. {bill_no}

- **Action Status:** Introduced
- **Primary Source Document:** [Bill {bill_no} PDF]({pdf_url})

## 1. Statutory Context
Mechanically ingested legislative record from Anne Arundel County Council portal.
"""
        with open(target_md, "w", encoding="utf-8") as out_f:
            out_f.write(frontmatter)
        print(f"  ✓ Ingested new record: {os.path.basename(target_md)} (SHA-256: {sha256_hash})")
        updated_count += 1

    print(f"[Anne Arundel Poller] Polling complete. New records ingested: {updated_count}")
    return updated_count

if __name__ == "__main__":
    poll()
