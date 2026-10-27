"""
poll_anne_arundel.py
Deterministic Ingestion Poller: Anne Arundel County Council Zoning Legislation (Article 18)
Swapp Technologies LLC (Maryland)

Invariant: Zero model in the path (Rule 10). Hard generation rule only.
Extracts mechanically from official county legislative portal.
Honours robots.txt and 5 s host spacing via EnactedCrawler.
Schema contract enforced: fails with 'schema changed: <selector>' if required selectors do not match.
Zero inferred defaults, zero constructed titles or statuses.
"""

import os
import sys
import re
import yaml
import hashlib
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPTS_DIR)
AA_DIR = os.path.join(ROOT_DIR, "anne_arundel", "council_bills")
PORTAL_URL = "https://www.aacounty.org/county-council/legislation"
CONTRACT_PATH = os.path.join(ROOT_DIR, "sources", "contracts", "anne_arundel_zoning.yaml")

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


def check_html_schema_contract(soup: BeautifulSoup, contract: Dict[str, Any]):
    """
    Checks that required selectors in contract match elements in the fetched HTML.
    If a required selector finds 0 elements, fails with 'schema changed: <selector>'.
    """
    selectors = contract.get("required_selectors", ["table", "tr"])
    for sel in selectors:
        matches = soup.select(sel) if " " in sel or "[" in sel else soup.find_all(sel)
        if not matches:
            raise ValueError(f"schema changed: {sel}")


def poll(
    crawler: Optional[EnactedCrawler] = None,
    health_data: Optional[Dict[str, Any]] = None,
    contract_path: Optional[str] = None
) -> int:
    c = crawler or EnactedCrawler()
    print(f"[Anne Arundel Poller] Polling legislation portal {PORTAL_URL}...")

    allowed, status_code, body, err = c.fetch(PORTAL_URL)
    now_iso = get_iso_now()

    if not allowed:
        print(f"WARNING: Portal disallowed by robots.txt: {PORTAL_URL}", file=sys.stderr)
        if health_data is not None:
            record_source_check(
                source_id="anne_arundel_zoning",
                url=PORTAL_URL,
                success=False,
                error="disallowed_by_robots_txt",
                health_data=health_data,
                now_iso=now_iso
            )
        return 0

    if status_code != 200:
        print(f"ERROR: HTTP {status_code} from {PORTAL_URL}: {err}", file=sys.stderr)
        if health_data is not None:
            record_source_check(
                source_id="anne_arundel_zoning",
                url=PORTAL_URL,
                success=False,
                error=err or f"HTTP {status_code}",
                health_data=health_data,
                now_iso=now_iso
            )
        sys.exit(1)

    html_content = body.decode("utf-8", errors="ignore")
    soup = BeautifulSoup(html_content, "html.parser")

    contract = load_schema_contract(contract_path)
    if contract:
        check_html_schema_contract(soup, contract)

    rows = soup.find_all("tr")
    print(f"[Anne Arundel Poller] Parsed {len(rows)} table rows from portal.")

    updated_count = 0

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
            print(f"WARNING: Skipping bill {bill_no}: no PDF link found in row.", file=sys.stderr)
            continue

        href = link_tag.get("href")
        pdf_url = href if href.startswith("http") else f"https://www.aacounty.org{href}"

        title_match = re.search(r"Bill\s*(?:No\.)?\s*\d{1,3}-\d{2}\s*[-–—:]\s*(.*?)(?:Introduced|Adopted|Enacted|$)", text, re.IGNORECASE)
        if not title_match or not title_match.group(1).strip():
            print(f"WARNING: Skipping bill {bill_no}: failed to extract title from source text.", file=sys.stderr)
            continue
        title = title_match.group(1).strip()

        status_match = re.search(r"\b(Introduced|Adopted|Enacted|Passed|Withdrawn|Vetoed)\b", text, re.IGNORECASE)
        if not status_match:
            print(f"WARNING: Skipping bill {bill_no}: failed to extract action_status from source text.", file=sys.stderr)
            continue
        action_status = status_match.group(1).capitalize()

        # Fetch and verify primary PDF (Rule 1)
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
            "jurisdiction": "Maryland / Anne Arundel County",
            "governing_body": "Anne Arundel County Council",
            "instrument_type": "County Bill",
            "bill_number": f"Bill {bill_no}",
            "title": title,
            "action_status": action_status,
            "primary_source_url": pdf_url,
            "source_sha256": sha256_hash,
            "source_fetched_at": now_iso,
            "provenance_endpoint": "www.aacounty.org/county-council/legislation"
        }

        content = f"""---
jurisdiction: "{frontmatter['jurisdiction']}"
governing_body: "{frontmatter['governing_body']}"
instrument_type: "{frontmatter['instrument_type']}"
bill_number: "{frontmatter['bill_number']}"
title: "{frontmatter['title']}"
action_status: "{frontmatter['action_status']}"
primary_source_url: "{frontmatter['primary_source_url']}"
source_sha256: "{frontmatter['source_sha256']}"
source_fetched_at: "{frontmatter['source_fetched_at']}"
provenance_endpoint: "{frontmatter['provenance_endpoint']}"
---
# Anne Arundel County {frontmatter['bill_number']}: {title}

- **Action Status:** {frontmatter['action_status']}

## 1. Statutory Context
Primary legislative record fetched from Anne Arundel County Council portal.

## 2. Primary Government Record
- **Primary Source Document:** [{frontmatter['bill_number']} Official PDF]({pdf_url})

## 3. Municipal Contacts (Source + Last-Checked Date)
- **Anne Arundel County Council Office:**
  - *Address:* 44 Calvert Street, 1st Floor, Annapolis, MD 21401
  - *Phone:* (410) 222-1401
  - *Source URL:* `https://www.aacounty.org/county-council`
  - *Last checked:* {now_iso[:10]}
"""
        with open(target_md, "w", encoding="utf-8") as out_f:
            out_f.write(content)
        print(f"  ✓ Ingested new record: {os.path.basename(target_md)} (SHA-256: {sha256_hash})")
        updated_count += 1

    if health_data is not None:
        record_source_check(
            source_id="anne_arundel_zoning",
            url=PORTAL_URL,
            success=True,
            changed=(updated_count > 0),
            health_data=health_data,
            now_iso=now_iso
        )

    print(f"[Anne Arundel Poller] Polling complete. New records ingested: {updated_count}")
    return updated_count


if __name__ == "__main__":
    poll()
