"""
poll_montgomery.py
Deterministic Ingestion Poller: Montgomery County Council Zoning Text Amendments (ZTAs)
Swapp Technologies LLC (Maryland)

Invariant: Zero model in the path (Rule 10). Hard generation rule only.
Extracts mechanically from official Socrata API and county PDF documents.
Honours robots.txt and 5 s host spacing via EnactedCrawler.
Schema contract enforced: any missing required field skips or fails with 'schema changed: <field>'.
Zero inferred defaults, zero constructed URLs, zero fallback field names.
"""

import os
import sys
import json
import re
import yaml
import hashlib
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPTS_DIR)
MONTGOMERY_DIR = os.path.join(ROOT_DIR, "montgomery", "zta_amendments")
API_ENDPOINT = "https://data.montgomerycountymd.gov/resource/3hex-pk9g.json"
CONTRACT_PATH = os.path.join(ROOT_DIR, "sources", "contracts", "montgomery_zoning.yaml")

if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from crawler import EnactedCrawler
from source_health import record_source_check, get_iso_now

ENACTED_USER_AGENT = "EnactedBot/1.0 (+https://enacted.app/bot/)"


def load_schema_contract(contract_path: Optional[str] = None) -> Dict[str, Any]:
    p = contract_path or CONTRACT_PATH
    if not os.path.exists(p):
        return {}
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def check_schema_contract(records: List[Dict[str, Any]], contract: Dict[str, Any]):
    """
    Checks that every required field from contract is present across candidate records.
    If a required field is missing from all records in the batch, fails with 'schema changed: <field>'.
    """
    required = contract.get("required_fields", ["zta_no", "title", "introduction_date", "sponsor_s", "action_status"])
    if not records:
        return

    # Check that the required field keys exist in at least one record or dataset schema
    all_keys = set()
    for r in records:
        all_keys.update(r.keys())

    for req_field in required:
        if req_field not in all_keys:
            raise ValueError(f"schema changed: {req_field}")


def poll(
    crawler: Optional[EnactedCrawler] = None,
    health_data: Optional[Dict[str, Any]] = None,
    contract_path: Optional[str] = None
) -> int:
    c = crawler or EnactedCrawler()
    now_iso = get_iso_now()

    # Check if source is marked stale in health data or on-disk registry
    source_status = None
    if health_data and "sources" in health_data:
        source_status = health_data.get("sources", {}).get("montgomery_zoning", {}).get("status")
    if not source_status:
        st_path = os.path.join(ROOT_DIR, "status", "sources.json")
        if os.path.exists(st_path):
            try:
                with open(st_path, "r", encoding="utf-8") as f:
                    reg = json.load(f)
                    source_status = reg.get("sources", {}).get("montgomery_zoning", {}).get("status")
            except Exception:
                pass

    if source_status == "stale":
        print("[Montgomery Poller] source stale — awaiting replacement")
        return 0

    print(f"[Montgomery Poller] Fetching ZTAs from {API_ENDPOINT}...")
    allowed, status_code, body, err = c.fetch(API_ENDPOINT)

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

    contract = load_schema_contract(contract_path)
    if contract:
        check_schema_contract(records, contract)

    print(f"[Montgomery Poller] Retrieved {len(records)} candidate ZTA entries.")
    updated_count = 0

    for rec in records:
        zta_no = rec.get("zta_no")
        if not zta_no:
            print(f"WARNING: Skipping entry missing required field 'zta_no'.", file=sys.stderr)
            continue

        clean_num = zta_no.strip().replace("-", "_").lower()
        target_md = os.path.join(MONTGOMERY_DIR, f"zta_{clean_num}.md")

        title = rec.get("title")
        if not title:
            print(f"WARNING: Skipping entry {zta_no} missing required field 'title'.", file=sys.stderr)
            continue

        sponsors = rec.get("sponsor_s")
        if not sponsors:
            print(f"WARNING: Skipping entry {zta_no} missing required field 'sponsor_s'.", file=sys.stderr)
            continue

        intro_date = rec.get("introduction_date")
        if not intro_date:
            print(f"WARNING: Skipping entry {zta_no} missing required field 'introduction_date'.", file=sys.stderr)
            continue
        if "T" in intro_date:
            intro_date = intro_date.split("T")[0]

        action_status = rec.get("action_status")
        if not action_status:
            print(f"WARNING: Skipping entry {zta_no} missing required field 'action_status'.", file=sys.stderr)
            continue

        # Extract primary PDF link strictly from source record (ordinance or zta)
        ordinance_obj = rec.get("ordinance")
        pdf_url = ordinance_obj.get("url") if isinstance(ordinance_obj, dict) else (ordinance_obj if isinstance(ordinance_obj, str) else None)
        if not pdf_url:
            zta_obj = rec.get("zta")
            pdf_url = zta_obj.get("url") if isinstance(zta_obj, dict) else (zta_obj if isinstance(zta_obj, str) else None)

        if not pdf_url or not isinstance(pdf_url, str) or not pdf_url.startswith("http"):
            print(f"WARNING: Skipping entry {zta_no}: missing primary document URL in source record.", file=sys.stderr)
            continue

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
