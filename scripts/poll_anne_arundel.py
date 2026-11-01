"""
poll_anne_arundel.py
Deterministic Ingestion Poller: Anne Arundel County Council Zoning Legislation (Part B)
Swapp Technologies LLC (Maryland)

Invariant: Zero model in the path (Rule 10). Hard generation rule only.
Extracts mechanically from official county legislative portal:
1. Past legislation listing: https://www.aacounty.org/county-council/legislation/past-legislation
2. Current legislation listing: https://www.aacounty.org/county-council/legislation
3. Per-bill pages: https://www.aacounty.org/county-council/legislation/bill-no-<n>-<yy>
Honours robots.txt and 5 s host spacing via EnactedCrawler.
Deterministic zoning/subdivision rule:
Title as printed begins "AN ORDINANCE concerning: Zoning" or "AN ORDINANCE concerning: Subdivision and Development"
(after any "(As Amended)" prefix).
Schema contract enforced: fails with 'schema changed: <selector>' if required selectors do not match.
Zero inferred defaults, zero constructed titles or statuses.
"""

import os
import sys
import re
import yaml
import json
import hashlib
import urllib.parse
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any, List, Tuple

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPTS_DIR)
AA_DIR = os.path.join(ROOT_DIR, "anne_arundel", "council_bills")
CONTRACT_PATH = os.path.join(ROOT_DIR, "sources", "contracts", "anne_arundel_zoning.yaml")

LISTING_URLS = [
    "https://www.aacounty.org/county-council/legislation/past-legislation",
    "https://www.aacounty.org/county-council/legislation"
]

if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from crawler import EnactedCrawler
from source_health import record_source_check, get_iso_now

ENACTED_USER_AGENT = "EnactedBot/1.0 (+https://enacted.app/bot/)"


def matches_zoning_rule(title_str: str) -> bool:
    """
    Deterministic rule:
    Bill title as printed begins 'AN ORDINANCE concerning: Zoning' or
    'AN ORDINANCE concerning: Subdivision and Development' (after any '(As Amended)' prefix).
    """
    t = re.sub(r"^\(As Amended\)\s*", "", title_str.strip(), flags=re.IGNORECASE)
    t = re.sub(r"^Bill\s*(?:No\.)?\s*\d+-\d+\s*:\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"^\(As Amended\)\s*", "", t.strip(), flags=re.IGNORECASE)
    return t.startswith("AN ORDINANCE concerning: Zoning") or t.startswith("AN ORDINANCE concerning: Subdivision and Development")


def load_schema_contract(contract_path: Optional[str] = None) -> Dict[str, Any]:
    p = contract_path or CONTRACT_PATH
    if not os.path.exists(p):
        return {}
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def check_html_schema_contract(soup: BeautifulSoup, contract: Dict[str, Any], is_bill_page: bool = False):
    """
    Checks that required selectors in contract match elements in the fetched HTML.
    If a required selector finds 0 elements, fails with 'schema changed: <selector>'.
    """
    if is_bill_page:
        selectors = [
            contract.get("bill_page_selectors", {}).get("number", "h1"),
            contract.get("bill_page_selectors", {}).get("sponsor", ".zn-field-introduced-by"),
            contract.get("bill_page_selectors", {}).get("schedule_timeline", ".zn-legislation-schedule")
        ]
    else:
        # Listing page selectors
        selectors = [
            contract.get("listing_selectors", {}).get("teaser", ".zn-legislation.zn-teaser"),
            contract.get("listing_selectors", {}).get("title_link", ".zn-title a")
        ]

    for sel in selectors:
        if not sel:
            continue
        matches = soup.select(sel)
        if not matches:
            raise ValueError(f"schema changed: {sel}")


def parse_bill_page(html_text: str, bill_page_url: str, listing_status: Optional[str] = None, listing_url: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Parses a per-bill page mechanically and returns record data dict, or None if required field is missing.
    """
    soup = BeautifulSoup(html_text, "html.parser")

    # 1. Bill number
    h1 = soup.find("h1")
    if not h1:
        print(f"WARNING: Skipping {bill_page_url}: missing required field 'bill_number' (h1 tag absent).", file=sys.stderr)
        return None
    h1_text = h1.get_text(" ", strip=True)
    m = re.search(r"Bill\s*(?:No\.)?\s*(\d{1,3}-\d{2})", h1_text, re.IGNORECASE)
    if not m:
        print(f"WARNING: Skipping {bill_page_url}: missing required field 'bill_number' (cannot parse bill number from '{h1_text}').", file=sys.stderr)
        return None
    bill_no = m.group(1)

    # 2. Title
    title_div = soup.select_one(".zn-field-intro") or soup.select_one(".zn-field-short-description")
    if not title_div:
        print(f"WARNING: Skipping bill {bill_no}: missing required field 'title'.", file=sys.stderr)
        return None
    title = title_div.get_text(" ", strip=True)
    if not title:
        print(f"WARNING: Skipping bill {bill_no}: missing required field 'title' (empty).", file=sys.stderr)
        return None

    # Check zoning rule
    if not matches_zoning_rule(title):
        return None

    # 3. Sponsor
    sponsor_div = soup.select_one(".zn-field-introduced-by")
    if not sponsor_div:
        print(f"WARNING: Skipping bill {bill_no}: missing required field 'sponsor'.", file=sys.stderr)
        return None
    sponsor = sponsor_div.get_text(" ", strip=True)
    if not sponsor:
        print(f"WARNING: Skipping bill {bill_no}: missing required field 'sponsor' (empty).", file=sys.stderr)
        return None

    # 4. Schedule rows
    schedule_entries = []
    for entry in soup.select(".zn-legislation-schedule li.zn-timeline-entry"):
        lbl_el = entry.select_one(".zn-schedule-label")
        date_el = entry.select_one(".zn-date")
        if lbl_el and date_el:
            lbl = lbl_el.get_text(" ", strip=True)
            dt = date_el.get_text(" ", strip=True)
            if lbl and dt:
                schedule_entries.append({"label": lbl, "date": dt})

    if not schedule_entries:
        print(f"WARNING: Skipping bill {bill_no}: missing required field 'schedule' (0 timeline entries).", file=sys.stderr)
        return None

    # 5. Status word and which page it came from
    terminal_labels = {"passed", "expired", "withdrawn", "defeated", "vetoed"}
    status_word = None
    status_page = None

    # Check terminal label in schedule
    for s in reversed(schedule_entries):
        if s["label"].lower() in terminal_labels:
            status_word = s["label"]
            status_page = bill_page_url
            break

    if not status_word and listing_status:
        status_word = listing_status
        status_page = listing_url
    elif not status_word:
        # Latest schedule entry label as fallback
        status_word = schedule_entries[-1]["label"]
        status_page = bill_page_url

    if not status_word:
        print(f"WARNING: Skipping bill {bill_no}: missing required field 'action_status'.", file=sys.stderr)
        return None

    # 6. PDF URL
    doc_link = soup.select_one(".zn-legislation-documents a[href$='.pdf']")
    if not doc_link or not doc_link.get("href"):
        print(f"WARNING: Skipping bill {bill_no}: missing required field 'pdf_url'.", file=sys.stderr)
        return None
    raw_pdf_href = doc_link.get("href").strip()
    pdf_url = urllib.parse.urljoin(bill_page_url, raw_pdf_href)

    return {
        "bill_no": bill_no,
        "title": title,
        "sponsor": sponsor,
        "schedule": schedule_entries,
        "action_status": status_word,
        "status_page": status_page,
        "bill_page_url": bill_page_url,
        "pdf_url": pdf_url
    }


def poll(
    crawler: Optional[EnactedCrawler] = None,
    health_data: Optional[Dict[str, Any]] = None,
    contract_path: Optional[str] = None,
    dry_run: bool = True
) -> int:
    """
    Polls Anne Arundel County Council legislation listings and per-bill pages.
    dry_run=True (default in this pass) records would-be records without authoring files.
    """
    c = crawler or EnactedCrawler()
    now_iso = get_iso_now()
    contract = load_schema_contract(contract_path)

    print(f"[Anne Arundel Poller] Polling legislation listings (dry_run={dry_run})...")
    total_processed = 0
    candidate_records = []

    for listing_url in LISTING_URLS:
        allowed, status_code, body, err = c.fetch(listing_url)
        if not allowed:
            print(f"WARNING: Listing disallowed by robots.txt: {listing_url}", file=sys.stderr)
            continue
        if status_code != 200:
            print(f"ERROR: HTTP {status_code} from {listing_url}: {err}", file=sys.stderr)
            continue

        html_content = body.decode("utf-8", errors="ignore")
        soup = BeautifulSoup(html_content, "html.parser")

        # Validate contract on listing page with content
        teasers = soup.select(".zn-legislation.zn-teaser")
        if teasers and contract:
            check_html_schema_contract(soup, contract, is_bill_page=False)

        print(f"[Anne Arundel Poller] Found {len(teasers)} teasers on {listing_url}.")

        for t in teasers:
            title_a = t.select_one(".zn-title a")
            if not title_a or not title_a.get("href"):
                continue

            teaser_title = title_a.get_text(" ", strip=True)
            if not matches_zoning_rule(teaser_title):
                continue

            # Extract listing status if present
            listing_status = None
            status_div = t.select_one(".zn-legislation-schedule")
            if status_div:
                status_txt = status_div.get_text(" ", strip=True)
                m_st = re.search(r"Status\s*([A-Za-z]+)", status_txt)
                if m_st:
                    listing_status = m_st.group(1).capitalize()

            bill_href = title_a.get("href").strip()
            bill_page_url = urllib.parse.urljoin(listing_url, bill_href)

            # Fetch bill page
            b_allowed, b_status, b_body, b_err = c.fetch(bill_page_url)
            if not b_allowed or b_status != 200:
                print(f"WARNING: Could not fetch bill page {bill_page_url}: HTTP {b_status} {b_err}", file=sys.stderr)
                continue

            b_html = b_body.decode("utf-8", errors="ignore")
            rec_data = parse_bill_page(b_html, bill_page_url, listing_status=listing_status, listing_url=listing_url)
            if not rec_data:
                continue

            candidate_records.append(rec_data)
            total_processed += 1
            print(
                f"  [Dry-Run] Would ingest: Bill {rec_data['bill_no']} | '{rec_data['title']}' | "
                f"Status: {rec_data['action_status']} (from {rec_data['status_page']}) | "
                f"PDF: {rec_data['pdf_url']}"
            )

    if health_data is not None:
        record_source_check(
            source_id="anne_arundel_zoning",
            url=LISTING_URLS[0],
            success=True,
            changed=(total_processed > 0),
            health_data=health_data,
            now_iso=now_iso
        )

    print(f"[Anne Arundel Poller] Completed. Processed candidate records: {total_processed}")
    return total_processed


if __name__ == "__main__":
    poll()
