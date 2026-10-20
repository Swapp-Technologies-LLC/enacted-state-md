"""
poll_montgomery.py
Deterministic Ingestion Poller: Montgomery County Council Zoning Text Amendments (ZTAs)
Swapp Technologies LLC (Maryland)

Invariant: Zero model in the path (Rule 10). Hard generation rule only.
Extracts mechanically from official Socrata API and county PDF documents.
Honours robots.txt and 5 s host spacing via EnactedCrawler.
"""

import os
import sys
import json
import re
import hashlib
from datetime import datetime, timezone
from typing import Optional, Dict, Any

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPTS_DIR)
MONTGOMERY_DIR = os.path.join(ROOT_DIR, "montgomery", "zta_amendments")
API_ENDPOINT = "https://data.montgomerycountymd.gov/resource/3hex-pk9g.json?$order=intro_date%20DESC&$limit=25"

if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from crawler import EnactedCrawler
from source_health import record_source_check, get_iso_now

ENACTED_USER_AGENT = "EnactedBot/1.0 (+https://enacted.app/bot/)"


def poll(crawler: Optional[EnactedCrawler] = None, health_data: Optional[Dict[str, Any]] = None) -> int:
    c = crawler or EnactedCrawler()
    print(f"[Montgomery Poller] Fetching ZTAs from {API_ENDPOINT}...")

    allowed, status_code, body, err = c.fetch(API_ENDPOINT)
    now_iso = get_iso_now()

    if not allowed:
        print(f"WARNING: Socrata API disallowed by robots.txt: {API_ENDPOINT}", file=sys.stderr)
        if health_data is not None:
            record_source_check(
                source_id="montgomery_zoning",
                url=API_ENDPOINT,
                success=False,
                error="disallowed_by_robots_txt",
                health_data=health_data,
                now_iso=now_iso
            )
        return 0

    if status_code != 200:
        print(f"ERROR: HTTP {status_code} from {API_ENDPOINT}: {err}", file=sys.stderr)
        if health_data is not None:
            record_source_check(
                source_id="montgomery_zoning",
                url=API_ENDPOINT,
                success=False,
                error=err or f"HTTP {status_code}",
                health_data=health_data,
                now_iso=now_iso
            )
        sys.exit(1)

    try:
        records = json.loads(body.decode("utf-8"))
    except Exception as e:
        print(f"ERROR: Failed parsing Montgomery Socrata JSON: {e}", file=sys.stderr)
        if health_data is not None:
            record_source_check(
                source_id="montgomery_zoning",
                url=API_ENDPOINT,
                success=False,
                error=f"JSON parse error: {e}",
                health_data=health_data,
                now_iso=now_iso
            )
        sys.exit(1)

    print(f"[Montgomery Poller] Retrieved {len(records)} candidate ZTA entries.")
    updated_count = 0

    for rec in records:
        zta_no = rec.get("zta_number") or rec.get("zta_no")
        if not zta_no:
            print(f"WARNING: Skipping entry without zta_number in Socrata payload.", file=sys.stderr)
            continue

        clean_num = zta_no.strip().replace("-", "_").lower()
        target_md = os.path.join(MONTGOMERY_DIR, f"zta_{clean_num}.md")

        title = rec.get("plain_english_summary") or rec.get("title") or f"ZTA {zta_no}"
        sponsors = rec.get("lead_sponsors") or "[pending verification]"
        intro_date = rec.get("intro_date", "")
        if "T" in intro_date:
            intro_date = intro_date.split("T")[0]

        action_status = rec.get("council_action") or "Introduced"
        action_date = rec.get("action_date", "")
        if "T" in action_date:
            action_date = action_date.split("T")[0]

        pdf_url = rec.get("pdf_link", {}).get("url") if isinstance(rec.get("pdf_link"), dict) else rec.get("pdf_link")
        if not pdf_url:
            pdf_url = f"https://www.montgomerycountymd.gov/COUNCIL/Resources/Files/zta/{intro_date[:4] if intro_date else '2024'}/ZTA%20{zta_no}.pdf"

        if os.path.exists(target_md):
            continue

        # Verify primary source PDF before writing record (Rule 1)
        pdf_allowed, pdf_status, pdf_data, pdf_err = c.fetch(pdf_url)
        if not pdf_allowed:
            print(f"WARNING: Primary PDF disallowed by robots.txt at {pdf_url}. Skipping record creation.", file=sys.stderr)
            continue
        if pdf_status != 200:
            print(f"WARNING: Primary PDF returned HTTP {pdf_status} at {pdf_url}. Skipping record creation.", file=sys.stderr)
            continue
        if not pdf_data.startswith(b"%PDF-"):
            print(f"WARNING: Content at {pdf_url} is not a valid PDF. Skipping.", file=sys.stderr)
            continue

        sha256_hash = hashlib.sha256(pdf_data).hexdigest()

        frontmatter = {
            "jurisdiction": "Maryland / Montgomery County",
            "governing_body": "Montgomery County Council (sitting as District Council)",
            "instrument_type": "Zoning Text Amendment (ZTA)",
            "zta_number": zta_no,
            "title": title,
            "action_status": action_status,
            "introduced_date": intro_date,
            "lead_sponsors": sponsors,
            "primary_source_url": pdf_url,
            "source_sha256": sha256_hash,
            "source_fetched_at": now_iso,
            "provenance_endpoint": "data.montgomerycountymd.gov/resource/3hex-pk9g.json"
        }

        content = f"""---
jurisdiction: "{frontmatter['jurisdiction']}"
governing_body: "{frontmatter['governing_body']}"
instrument_type: "{frontmatter['instrument_type']}"
zta_number: "{frontmatter['zta_number']}"
title: "{frontmatter['title']}"
action_status: "{frontmatter['action_status']}"
introduced_date: "{frontmatter['introduced_date']}"
lead_sponsors: "{frontmatter['lead_sponsors']}"
primary_source_url: "{frontmatter['primary_source_url']}"
source_sha256: "{frontmatter['source_sha256']}"
source_fetched_at: "{frontmatter['source_fetched_at']}"
provenance_endpoint: "{frontmatter['provenance_endpoint']}"
---
# Montgomery County ZTA {zta_no}: {title}

- **Action Status:** {action_status}
- **Introduced:** {intro_date}
- **Lead Sponsor:** {sponsors}

## 1. Statutory Context
Primary legislative record fetched from Montgomery County open data.

## 2. Primary Government Record
- **Primary Source Document:** [{zta_no} Official PDF]({pdf_url})

## 3. Municipal Contacts (Source + Last-Checked Date)
- **Montgomery County Council Office:**
  - *Address:* 100 Maryland Avenue, Rockville, MD 20850
  - *Phone:* (240) 777-7900
  - *Source URL:* `https://www.montgomerycountymd.gov/council/`
  - *Last checked:* {now_iso[:10]}
"""
        with open(target_md, "w", encoding="utf-8") as out_f:
            out_f.write(content)
        print(f"  ✓ Ingested new record: {os.path.basename(target_md)} (SHA-256: {sha256_hash})")
        updated_count += 1

    if health_data is not None:
        record_source_check(
            source_id="montgomery_zoning",
            url=API_ENDPOINT,
            success=True,
            changed=(updated_count > 0),
            health_data=health_data,
            now_iso=now_iso
        )

    print(f"[Montgomery Poller] Polling complete. New records ingested: {updated_count}")
    return updated_count


if __name__ == "__main__":
    poll()
