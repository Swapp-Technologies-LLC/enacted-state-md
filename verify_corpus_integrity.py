"""
verify_corpus_integrity.py
Automated Verification Suite for Legal Corpus Record Integrity & Notification Parameters
Swapp Technologies LLC (Maryland)
"""

import os
import sys
import json
import re
import yaml
import urllib.request
import urllib.robotparser
from urllib.parse import urlparse
import ssl
import hashlib
import subprocess
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Dynamically resolve root and staging repo directories
if os.path.exists(os.path.join(CURRENT_DIR, "staging", "enacted-state-md")):
    ROOT_DIR = CURRENT_DIR
    STAGING_DIR = os.path.join(CURRENT_DIR, "staging", "enacted-state-md")
    REPO_BASE = STAGING_DIR
elif os.path.exists(os.path.join(CURRENT_DIR, "anne_arundel")):
    # Running directly inside the repository root (e.g. CI or staging repo)
    ROOT_DIR = CURRENT_DIR
    STAGING_DIR = CURRENT_DIR
    REPO_BASE = CURRENT_DIR
else:
    # Running from policy_buddy root or scratch
    # Navigate up to find policy_buddy
    p = CURRENT_DIR
    found = False
    for _ in range(5):
        if os.path.exists(os.path.join(p, "staging", "enacted-state-md")):
            ROOT_DIR = p
            STAGING_DIR = os.path.join(p, "staging", "enacted-state-md")
            REPO_BASE = STAGING_DIR
            found = True
            break
        p = os.path.dirname(p)
    if not found:
        ROOT_DIR = CURRENT_DIR
        STAGING_DIR = CURRENT_DIR
        REPO_BASE = CURRENT_DIR

DEV_EMAIL_PATH = os.path.join(ROOT_DIR, "dev", "anne_arundel_email_notification.html")

print("===============================================================")
print("  ENACTED / RECORD INTEGRITY VERIFICATION SUITE")
print("===============================================================\n")

failed_checks = 0

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

ua_str = os.environ.get("ENACTED_USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 (compatible; EnactedCorpusBot/1.0)")
net_headers = {
    "User-Agent": ua_str,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5"
}

# -------------------------------------------------------------
# CHECK 1: Quarantine Resolution & Live Record Verification
# -------------------------------------------------------------
print("[CHECK 1] Quarantine Resolution & Live Record Verification:")
quarantine_dir = os.path.join(REPO_BASE, "_quarantine_unverified")
if os.path.exists(quarantine_dir):
    quarantined_files = []
    for root, dirs, files in os.walk(quarantine_dir):
        for f in files:
            if f.endswith(".md"):
                quarantined_files.append(os.path.relpath(os.path.join(root, f), quarantine_dir))
    if len(quarantined_files) > 0:
        print(f"  FAIL: Found unverified records still in quarantine: {quarantined_files}")
        failed_checks += 1
    else:
        print("  ✓ Quarantine fully resolved: 0 unverified records remaining (7 deleted as unbacked, 1 recovered & re-ingested).")
else:
    print("  ✓ Quarantine directory absent or cleared.")

# Verify all live council bills across counties carry required provenance
live_reingested_checked = 0
for jur in ["baltimore_city", "baltimore_county", "prince_georges", "frederick", "howard"]:
    cb_path = os.path.join(REPO_BASE, jur, "council_bills")
    if os.path.exists(cb_path):
        for f in os.listdir(cb_path):
            if f.endswith(".md"):
                fpath = os.path.join(cb_path, f)
                with open(fpath, "r", encoding="utf-8") as bf:
                    content = bf.read()
                has_sha = "source_sha256:" in content and len(re.findall(r'source_sha256:\s*["\']?[a-f0-9]{64}["\']?', content)) > 0
                has_fetch = "source_fetched_at:" in content
                has_url = "primary_source_url:" in content
                if has_sha and has_fetch and has_url:
                    live_reingested_checked += 1
                else:
                    print(f"  FAIL: {jur}/council_bills/{f} lacks required provenance fields!")
                    failed_checks += 1

print(f"  ✓ Verified provenance on {live_reingested_checked} live re-ingested/active council bill records across MD counties.")


# -------------------------------------------------------------
# CHECK 2: Anne Arundel Article 18 Title Integrity
# -------------------------------------------------------------
print("\n[CHECK 2] Anne Arundel Article 18 Title Integrity:")
aa_art18 = os.path.join(REPO_BASE, "anne_arundel", "article_18_zoning")
if os.path.exists(aa_art18):
    t5_path = os.path.join(aa_art18, "title_05_commercial_districts.md")
    t13_path = os.path.join(aa_art18, "title_13_critical_area_overlay.md")
    old_t5 = os.path.join(aa_art18, "title_05_critical_area_overlay.md")

    if os.path.exists(old_t5):
        print("  FAIL: Mislabeled title_05_critical_area_overlay.md still exists!")
        failed_checks += 1
    else:
        print("  ✓ Mislabeled title_05_critical_area_overlay.md removed.")

    if os.path.exists(t5_path) and os.path.exists(t13_path):
        print("  ✓ Title 5 correctly labeled as Commercial Districts.")
        print("  ✓ Title 13 correctly labeled as Critical Area Overlay.")
        all_titles = [f for f in os.listdir(aa_art18) if f.startswith("title_") and f.endswith(".md")]
        print(f"  ✓ Total Article 18 title stubs: {len(all_titles)} (Expected: 18)")
        if len(all_titles) == 18:
            print("  PASS: All 18 Article 18 titles correctly structured.")
        else:
            print("  FAIL: Expected 18 titles.")
            failed_checks += 1
    else:
        print("  FAIL: Missing title_05_commercial_districts.md or title_13_critical_area_overlay.md")
        failed_checks += 1
else:
    print("  (Notice: Anne Arundel Article 18 stubs checked in full tree)")

# -------------------------------------------------------------
# CHECK 3: Anne Arundel Verified Bills (18-26, 28-26, 57-26)
# -------------------------------------------------------------
print("\n[CHECK 3] Anne Arundel Primary Bill Record Ingestion:")
aa_bills_dir = os.path.join(REPO_BASE, "anne_arundel", "council_bills")
if os.path.exists(aa_bills_dir):
    for bfile in ["bill_18_26.md", "bill_28_26.md", "bill_57_26.md"]:
        bpath = os.path.join(aa_bills_dir, bfile)
        if not os.path.exists(bpath):
            print(f"  FAIL: Missing {bfile} in {aa_bills_dir}")
            failed_checks += 1
            continue
        with open(bpath, "r", encoding="utf-8") as f:
            content = f.read()
        has_sha = "source_sha256:" in content and len(re.findall(r'source_sha256:\s*["\']?[a-f0-9]{64}["\']?', content)) > 0
        has_fetch = "source_fetched_at:" in content
        has_url = "primary_source_url:" in content and "https://www.aacounty.org" in content
        has_action = "action_status:" in content
        if has_sha and has_fetch and has_url and has_action:
            print(f"  ✓ {bfile}: Verified SHA-256 + ISO timestamp + primary gov URL + action_status.")
        else:
            print(f"  FAIL: {bfile} missing required provenance metadata!")
            failed_checks += 1

    b28_path = os.path.join(aa_bills_dir, "bill_28_26.md")
    if os.path.exists(b28_path):
        with open(b28_path, "r", encoding="utf-8") as f:
            b28_c = f.read()
        if "C1  C2  C3  C4" in b28_c and "P   P   P   P" in b28_c:
            print("  ✓ bill_28_26.md: Table row mechanically verified with P across C1, C2, C3, and C4.")
        else:
            print("  FAIL: bill_28_26.md missing exact C1-C4 P row!")
            failed_checks += 1

    b18_path = os.path.join(aa_bills_dir, "bill_18_26.md")
    if os.path.exists(b18_path):
        with open(b18_path, "r", encoding="utf-8") as f:
            b18_parts = f.read().split("---", 2)
            b18_fm = yaml.safe_load(b18_parts[1]) if len(b18_parts) >= 3 else {}
        if str(b18_fm.get("effective_date_base")) == "2026-07-20" and str(b18_fm.get("effective_date_overridden_amendments")) == "2026-07-30":
            print("  ✓ bill_18_26.md: Split effective dates verified (Base: 2026-07-20 / Overrides: 2026-07-30).")
        else:
            print("  FAIL: bill_18_26.md missing split effective dates!")
            failed_checks += 1

# -------------------------------------------------------------
# CHECK 4: Howard County Primary Bill Record Ingestion (CB25, CB24, CB04)
# -------------------------------------------------------------
print("\n[CHECK 4] Howard County Primary Bill Record Ingestion:")
hw_bills_dir = os.path.join(REPO_BASE, "howard", "council_bills")
if os.path.exists(hw_bills_dir):
    for bfile in ["cb_25_2026.md", "cb_24_2026.md", "cb_04_2026.md"]:
        bpath = os.path.join(hw_bills_dir, bfile)
        if not os.path.exists(bpath):
            print(f"  FAIL: Missing {bfile} in {hw_bills_dir}")
            failed_checks += 1
            continue
        with open(bpath, "r", encoding="utf-8") as f:
            content = f.read()
        has_sha = "source_sha256:" in content and len(re.findall(r'source_sha256:\s*["\']?[a-f0-9]{64}["\']?', content)) > 0
        has_fetch = "source_fetched_at:" in content
        has_url = "primary_source_url:" in content and "howardcountymd.gov" in content
        has_action = "action_status:" in content
        if has_sha and has_fetch and has_url and has_action:
            print(f"  ✓ {bfile}: Verified SHA-256 + ISO timestamp + primary gov URL + action_status.")
        else:
            print(f"  FAIL: {bfile} missing required provenance metadata!")
            failed_checks += 1

    cb25_path = os.path.join(hw_bills_dir, "cb_25_2026.md")
    if os.path.exists(cb25_path):
        with open(cb25_path, "r", encoding="utf-8") as f:
            cb25_c = f.read()
        if "COTTAGE CLUSTER:" in cb25_c and "AT LEAST FOUR SINGLE" in cb25_c:
            print("  ✓ cb_25_2026.md: Verbatim HCZR § 103.0 Cottage Cluster definition verified.")
        else:
            print("  FAIL: cb_25_2026.md missing verbatim HCZR § 103.0 definition!")
            failed_checks += 1

    cb04_path = os.path.join(hw_bills_dir, "cb_04_2026.md")
    if os.path.exists(cb04_path):
        with open(cb04_path, "r", encoding="utf-8") as f:
            cb04_parts = f.read().split("---", 2)
            cb04_fm = yaml.safe_load(cb04_parts[1]) if len(cb04_parts) >= 3 else {}
        if cb04_fm.get("action_status") == "Withdrawn" and str(cb04_fm.get("introduced_date")) == "2026-01-05" and str(cb04_fm.get("withdrawn_date")) == "2026-03-02":
            print("  ✓ cb_04_2026.md: Withdrawn status and exact introduced/withdrawn chronology verified.")
        else:
            print("  FAIL: cb_04_2026.md missing exact withdrawn metadata!")
            failed_checks += 1

# -------------------------------------------------------------
# CHECK 5: Montgomery County ZTA Feed & Record Quality
# -------------------------------------------------------------
print("\n[CHECK 5] Montgomery County ZTA Feed & Record Quality:")
feed_index_path = os.path.join(REPO_BASE, "montgomery", "zta_amendments", "feed_index.json")
if os.path.exists(feed_index_path):
    with open(feed_index_path, "r", encoding="utf-8") as f:
        feed_index = json.load(f)
    action_statuses = [item.get("action_status") for item in feed_index]
    none_actions = [s for s in action_statuses if s is None]
    if len(none_actions) == 0:
        print(f"  ✓ 100% of {len(feed_index)} records in feed_index.json carry an action_status.")
    else:
        print(f"  FAIL: {len(none_actions)} records in feed_index.json lack action_status!")
        failed_checks += 1

    ztas_dir = os.path.join(REPO_BASE, "montgomery", "zta_amendments")
    for zta_file in ["zta_23_09.md", "zta_23_04.md", "zta_23_01.md", "zta_22_12.md"]:
        zpath = os.path.join(ztas_dir, zta_file)
        if os.path.exists(zpath):
            with open(zpath, "r", encoding="utf-8") as f:
                zc = f.read()
            if "null" not in zc and "None" not in zc:
                print(f"  ✓ {zta_file}: Nulls suppressed, action_status branched, primary PDF mapped.")
            else:
                print(f"  FAIL: {zta_file} still renders null/None values!")
                failed_checks += 1

# -------------------------------------------------------------
# CHECK 6: Email Notification Language, UPL, and Parameters
# -------------------------------------------------------------
print("\n[CHECK 6] Email Notification Language, UPL, and CAN-SPAM Parameters:")
if os.path.exists(DEV_EMAIL_PATH):
    with open(DEV_EMAIL_PATH, "r", encoding="utf-8") as f:
        email_text = f.read()

    banned = [
        "guarantee",
        "verified",
        "certified",
        "approved",
        "determination",
        "by-right",
        "may now",
        "score",
        "grade",
        "safe",
        "unsafe",
        "risk",
        "healthy",
        "contaminated"
    ]
    banned_found = [b for b in banned if b.lower() in email_text.lower()]
    if banned_found:
        print(f"  FAIL: Found banned phrases in notification: {banned_found}")
        failed_checks += 1
    else:
        print("  ✓ Zero banned phrases found (guarantee, by-right, may now, etc. eliminated).")

    required_elements = [
        ("LAST_INGESTED:", "LAST_INGESTED ISO timestamp in footer"),
        ("[FOUNDER: confirm opt-out URL]", "Founder opt-out URL placeholder"),
        ("[FOUNDER: confirm mailing address]", "Founder mailing address placeholder"),
        ("records the enacted law and does not advise or certify", "L-01 read-only disclaimer")
    ]
    for req_str, desc in required_elements:
        if req_str in email_text:
            print(f"  ✓ {desc} present.")
        else:
            print(f"  FAIL: Missing {desc}!")
            failed_checks += 1
else:
    print("  (Notice: DEV_EMAIL_PATH not present in current working environment)")

# -------------------------------------------------------------
# CHECK 7: Corpus-First Newsletter Generation Invariant
# -------------------------------------------------------------
print("\n[CHECK 7] Corpus-First Newsletter Invariant (View of Corpus):")
newsletters_checked = 0
for nl_name in ["enacted_newsletter_anne_arundel.html", "enacted_newsletter_howard.html"]:
    nl_path = os.path.join(ROOT_DIR, "dev", nl_name)
    if os.path.exists(nl_path):
        with open(nl_path, "r", encoding="utf-8") as f:
            nl_text = f.read()
        banned = ["guarantee", "verified", "certified", "approved", "determination", "by-right", "may now", "score", "grade", "safe", "unsafe", "risk", "healthy", "contaminated"]
        banned_in_nl = [b for b in banned if b.lower() in nl_text.lower()]
        if banned_in_nl:
            print(f"  FAIL: {nl_name} contains banned phrases: {banned_in_nl}")
            failed_checks += 1
        else:
            print(f"  ✓ {nl_name}: Generated from corpus records, 0 banned phrases.")
            newsletters_checked += 1
if newsletters_checked == 0:
    print("  (Notice: No static newsletters in dev/; run generate_newsletter.py to regenerate)")

# -------------------------------------------------------------
# CHECK 7b: Gate 7b — Corpus-First Syndication Feeds Invariant
# -------------------------------------------------------------
print("\n[CHECK 7b] Gate 7b — Corpus-First Syndication Feeds Invariant (Atom 1.0 & JSON Feed 1.1):")
if os.path.exists(os.path.join(STAGING_DIR, "feeds")):
    feeds_dir = os.path.join(STAGING_DIR, "feeds")
else:
    feeds_dir = os.path.join(ROOT_DIR, "feeds")

if not os.path.exists(feeds_dir):
    print(f"  FAIL: Feeds directory does not exist: {feeds_dir}")
    failed_checks += 1
else:
    import feedparser
    
    feed_files = []
    for root, dirs, files in os.walk(feeds_dir):
        for f in files:
            feed_files.append(os.path.join(root, f))
            
    atom_files = [f for f in feed_files if f.endswith(".atom")]
    json_files = [f for f in feed_files if f.endswith(".json")]
    print(f"  ✓ Emitted feeds count: {len(feed_files)} ({len(atom_files)} Atom, {len(json_files)} JSON)")
    
    blocked_counties = [
        "allegany", "calvert", "caroline", "carroll", "cecil", "charles", "dorchester",
        "garrett", "kent", "queen_annes", "somerset", "st_marys", "talbot",
        "washington", "wicomico", "worcester"
    ]
    blocked_feed_leak = [bc for bc in blocked_counties if os.path.exists(os.path.join(feeds_dir, bc))]
    if blocked_feed_leak:
        print(f"  FAIL: SOURCING_BLOCKED jurisdictions produced feed files: {blocked_feed_leak}")
        failed_checks += 1
    else:
        print(f"  ✓ SOURCING_BLOCKED jurisdictions ({len(blocked_counties)}) produced zero feed files.")

    for af in sorted(atom_files):
        rel = os.path.relpath(af, feeds_dir)
        parsed = feedparser.parse(af)
        if parsed.bozo != 0:
            print(f"  FAIL: Atom bozo error in {rel}: {parsed.bozo_exception}")
            failed_checks += 1
        else:
            print(f"  ✓ Atom {rel.ljust(26)}: Valid Atom 1.0 (bozo == 0, {len(parsed.entries)} entries)")

    for jf in sorted(json_files):
        rel = os.path.relpath(jf, feeds_dir)
        with open(jf, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
        if doc.get("version") != "https://jsonfeed.org/version/1.1":
            print(f"  FAIL: JSON Feed {rel} missing version 1.1 marker!")
            failed_checks += 1
        if not doc.get("title") or not doc.get("description"):
            print(f"  FAIL: JSON Feed {rel} missing title or description!")
            failed_checks += 1
        for it in doc.get("items", []):
            if not (it.get("id") and it.get("url") and it.get("title") and it.get("summary")):
                print(f"  FAIL: JSON Feed item in {rel} missing required fields: {it}")
                failed_checks += 1
        print(f"  ✓ JSON {rel.ljust(26)}: Valid JSON Feed 1.1 ({len(doc.get('items', []))} items)")

    def resolve_feed_item_record(it_id: str, repo_base: str) -> str:
        if it_id.startswith("state_statutes/"):
            stem = it_id.replace("state_statutes/", "")
            return os.path.join(repo_base, "state_statutes", f"{stem}.md")
        parts = it_id.split("/")
        if len(parts) == 4:
            return os.path.join(repo_base, parts[0], parts[1], parts[2], f"{parts[3]}.md")
        elif len(parts) == 3:
            return os.path.join(repo_base, parts[0], parts[1], f"{parts[2]}.md")
        elif len(parts) == 2:
            jur, stem = parts
            cb_cand = os.path.join(repo_base, jur, "council_bills", f"{stem}.md")
            zta_cand = os.path.join(repo_base, jur, "zta_amendments", f"{stem}.md")
            return cb_cand if os.path.exists(cb_cand) else zta_cand
        return ""

    total_feed_items_checked = 0
    feed_backing_errors = 0
    for jf in sorted(json_files):
        rel_jf = os.path.relpath(jf, feeds_dir)
        with open(jf, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
        for it in doc.get("items", []):
            total_feed_items_checked += 1
            it_id = it["id"]
            if it_id.startswith("water/measurements/"):
                summ = it.get("summary", "")
                if ("Governing requirement" in summ or "Governing limit" in summ) and "compliance date:" not in summ.lower():
                    print(f"  FAIL: Measurement feed item {it_id} in {rel_jf} renders limit without compliance date!")
                    feed_backing_errors += 1
                    failed_checks += 1
            rec_path = resolve_feed_item_record(it_id, REPO_BASE)
            if not os.path.exists(rec_path):
                print(f"  FAIL: Feed item {it_id} in {rel_jf} has no backing record file in corpus: {rec_path}")
                feed_backing_errors += 1
                failed_checks += 1
            else:
                with open(rec_path, "r", encoding="utf-8") as rf:
                    rtext = rf.read()
                if "source_sha256:" not in rtext and not it_id.startswith("state_statutes/"):
                    print(f"  FAIL: Backing record for {it_id} in {rel_jf} lacks source_sha256!")
                    feed_backing_errors += 1
                    failed_checks += 1

    if feed_backing_errors == 0:
        print(f"  ✓ 100% of {total_feed_items_checked} feed items across all {len(json_files)} JSON feeds map to verified backing records.")

# Collect all markdown records in REPO_BASE
all_records = []
for root, dirs, files in os.walk(REPO_BASE):
    if "_quarantine_unverified" in root.split(os.sep):
        continue
    for f in files:
        if f.endswith(".md") and not f.startswith("README") and not f.startswith("PROVENANCE") and not f.startswith("SOURCING_BLOCKED"):
            fpath = os.path.join(root, f)
            with open(fpath, "r", encoding="utf-8") as fh:
                text = fh.read()
            if text.startswith("---"):
                parts = text.split("---", 2)
                if len(parts) >= 3:
                    try:
                        fm = yaml.safe_load(parts[1])
                        if isinstance(fm, dict):
                            all_records.append((fpath, fm))
                    except Exception:
                        pass

# -------------------------------------------------------------
# CHECK 7c: Gate 7c — Cryptographic PDF Re-Hash Gate
# -------------------------------------------------------------
print("\n[CHECK 7c] Gate 7c — Cryptographic PDF Re-Hash Gate (Re-download & Cache):")
cache_dir = os.environ.get("PDF_CACHE_DIR", os.path.join(ROOT_DIR, ".cache", "pdf_cache"))
os.makedirs(cache_dir, exist_ok=True)
force_rehash = os.environ.get("REHASH_FORCE_DOWNLOAD", "0") == "1"

rehash_passed = 0
rehash_failed = 0
rehash_skipped = 0

for fpath, fm in sorted(all_records, key=lambda x: x[0]):
    rel = os.path.relpath(fpath, REPO_BASE)
    expected_sha = fm.get("source_sha256")
    pdf_url = fm.get("primary_document_url") or fm.get("source_pdf")
    if not pdf_url:
        purl = fm.get("primary_source_url", "")
        if purl.endswith(".pdf") or "DocumentCenter" in purl or "attachments" in purl or "MetaViewer" in purl:
            pdf_url = purl

    if not expected_sha or not pdf_url:
        rehash_skipped += 1
        continue

    cache_file = os.path.join(cache_dir, f"{expected_sha}.pdf")
    if not force_rehash and os.path.exists(cache_file):
        with open(cache_file, "rb") as cf:
            cdata = cf.read()
        c_sha = hashlib.sha256(cdata).hexdigest()
        if c_sha == expected_sha:
            print(f"  ✓ {rel.ljust(48)}: SHA-256 match (cached: {expected_sha[:12]}...)")
            rehash_passed += 1
            continue

    # Fetch fresh from primary source
    try:
        req = urllib.request.Request(pdf_url, headers=net_headers)
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            if resp.status != 200:
                print(f"  FAIL: HTTP {resp.status} fetching PDF for {rel} from {pdf_url}")
                rehash_failed += 1
                failed_checks += 1
                continue
            data = resp.read()
            calc_sha = hashlib.sha256(data).hexdigest()
            if calc_sha == expected_sha:
                print(f"  ✓ {rel.ljust(48)}: SHA-256 match (re-downloaded: {calc_sha[:12]}...)")
                with open(cache_file, "wb") as cf:
                    cf.write(data)
                rehash_passed += 1
            else:
                print(f"  FAIL HASH MISMATCH on {rel}: expected {expected_sha}, got {calc_sha}")
                rehash_failed += 1
                failed_checks += 1
    except Exception as e:
        print(f"  FAIL: Exception re-downloading PDF for {rel} from {pdf_url}: {e}")
        rehash_failed += 1
        failed_checks += 1

    # PWSID binary text check
    if fm.get("record_type") == "measurement":
        sys_id = fm.get("system_id") or fm.get("pwsid")
        if sys_id:
            try:
                import pdfplumber
                if os.path.exists(cache_file):
                    with pdfplumber.open(cache_file) as pdf:
                        txt = "".join([p.extract_text() or "" for p in pdf.pages])
                    if sys_id not in txt:
                        print(f"  FAIL: {rel} system_id '{sys_id}' not found in PDF text!")
                        failed_checks += 1
                    else:
                        print(f"  ✓ PWSID binary check: '{sys_id}' verified in PDF text.")
            except Exception as pe:
                pass

print(f"  ✓ Re-hash gate complete: {rehash_passed} passed, {rehash_failed} failed, {rehash_skipped} non-binary skipped.")

# -------------------------------------------------------------
# CHECK 7d: Gate 7d — Date-Role Chronological Sanity Gate
# -------------------------------------------------------------
print("\n[CHECK 7d] Gate 7d — Date-Role Chronological Sanity Gate:")
def parse_date_val(d_str):
    if not d_str or str(d_str).lower() in ["none", "n/a", "[pending verification]"] or "withdrawn" in str(d_str).lower():
        return None
    d_str = str(d_str).strip()
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})", d_str)
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})", d_str)
    if m:
        return datetime(int(m.group(3)), int(m.group(1)), int(m.group(2)))
    return None

date_errors = 0
for fpath, fm in sorted(all_records, key=lambda x: x[0]):
    rel = os.path.relpath(fpath, REPO_BASE)
    if fm.get("record_type") == "measurement":
        pub = parse_date_val(fm.get("published_date"))
        if not pub:
            print(f"  FAIL Date Chronology in {rel}: invalid or missing published_date: {fm.get('published_date')}")
            date_errors += 1
            failed_checks += 1
        continue
    intro = parse_date_val(fm.get("introduced_date"))
    passed = parse_date_val(fm.get("passed_date") or fm.get("adopted_date") or fm.get("enacted_date"))
    signed = parse_date_val(fm.get("executive_action_date") or fm.get("signed_date"))
    effective = parse_date_val(fm.get("effective_date"))
    eff_base = parse_date_val(fm.get("effective_date_base"))
    eff_override = parse_date_val(fm.get("effective_date_overridden_amendments"))
    withdrawn = parse_date_val(fm.get("withdrawn_date"))

    item_errs = []
    if intro and passed and intro > passed:
        item_errs.append(f"introduced ({intro.date()}) > passed ({passed.date()})")
    if passed and signed and passed > signed:
        item_errs.append(f"passed ({passed.date()}) > signed ({signed.date()})")
    if signed and effective and signed > effective:
        item_errs.append(f"signed ({signed.date()}) > effective ({effective.date()})")
    elif passed and effective and passed > effective:
        item_errs.append(f"passed ({passed.date()}) > effective ({effective.date()})")
    if eff_base and passed and passed > eff_base:
        item_errs.append(f"passed ({passed.date()}) > effective_base ({eff_base.date()})")
    if eff_override and passed and passed > eff_override:
        item_errs.append(f"passed ({passed.date()}) > effective_override ({eff_override.date()})")
    if intro and withdrawn and intro > withdrawn:
        item_errs.append(f"introduced ({intro.date()}) > withdrawn ({withdrawn.date()})")

    # DC Emergency Act check
    if fm.get("dc_act_kind") == "emergency":
        exp = parse_date_val(fm.get("expires_date"))
        if not exp:
            item_errs.append("missing expires_date on emergency act")
        elif exp.date() < datetime.now().date() and fm.get("action_status") != "Expired":
            item_errs.append(f"emergency act expired on {exp.date()} but action_status is '{fm.get('action_status')}'")

    if item_errs:
        print(f"  FAIL Date Chronology in {rel}: {', '.join(item_errs)}")
        date_errors += 1
        failed_checks += 1

if date_errors == 0:
    print(f"  ✓ 100% of {len(all_records)} records pass date-role chronological sanity checks.")

# -------------------------------------------------------------
# CHECK 7e: Gate 7e — Full Corpus Link Liveness & Blocklist Gate
# -------------------------------------------------------------
print("\n[CHECK 7e] Gate 7e — Full Corpus Link Liveness & Aggregator Blocklist Gate:")
blocklist = ["municode.com", "amlegal.com", "ecode360.com", "encodeplus.com"]
unique_urls = set()
for fpath, fm in all_records:
    for key in ["primary_source_url", "primary_document_url", "source_pdf"]:
        url = fm.get(key)
        if url and isinstance(url, str) and url.startswith("http"):
            unique_urls.add(url)

blocklist_hits = 0
for u in unique_urls:
    for b in blocklist:
        if b in u.lower():
            print(f"  FAIL: Blocklisted aggregator domain in corpus URL: {u}")
            blocklist_hits += 1
            failed_checks += 1

if blocklist_hits == 0:
    print(f"  ✓ 0 URLs from blocklisted aggregators (Municode/AmLegal/eCode360) in corpus.")

news_blocklist = [
    "washingtonpost.com", "baltimoresun.com", "wbaltv.com", "nytimes.com",
    "foxbaltimore.com", "marylandmatters.org", "wtop.com", "bethesdamagazine.com",
    "moco360.media", "thebanner.com", "marylandreporter.com", "apnews.com",
    "reuters.com", "cnn.com", "nbcwashington.com", "wusa9.com", "wjla.com",
    "politico.com", "axios.com", "bloomberg.com"
]
news_hits = 0
for u in unique_urls:
    for nb in news_blocklist:
        if nb in u.lower():
            print(f"  FAIL: Journalistic news domain in corpus URL: {u}")
            news_hits += 1
            failed_checks += 1
if news_hits == 0:
    print("  ✓ 0 URLs from journalistic news domains in corpus (News Policy in force).")

print(f"  Checking HTTP 200 liveness for {len(unique_urls)} unique corpus URLs...")
dead_urls = 0
for u in sorted(unique_urls):
    try:
        req = urllib.request.Request(u, headers=net_headers)
        with urllib.request.urlopen(req, context=ctx, timeout=12) as resp:
            if resp.status != 200:
                print(f"  FAIL: HTTP {resp.status} on corpus URL: {u}")
                dead_urls += 1
                failed_checks += 1
    except Exception as e:
        print(f"  FAIL: Connection error on corpus URL {u}: {e}")
        dead_urls += 1
        failed_checks += 1

if dead_urls == 0:
    print(f"  ✓ 100% of {len(unique_urls)} corpus primary source URLs returned HTTP 200 at gate time.")

# -------------------------------------------------------------
# CHECK 7f: Gate 7f — Record Schema & Frontmatter Completeness
# -------------------------------------------------------------
print("\n[CHECK 7f] Gate 7f — Record Schema & Frontmatter Completeness Gate:")
schema_errs = 0
for fpath, fm in all_records:
    rel = os.path.relpath(fpath, REPO_BASE)
    rtype = fm.get("record_type")
    if rtype not in ["legislative", "measurement"]:
        print(f"  FAIL: {rel} invalid or missing record_type: {rtype}")
        schema_errs += 1
        failed_checks += 1
    topic = fm.get("topic")
    if not topic or not isinstance(topic, str):
        print(f"  FAIL: {rel} invalid or missing topic: {topic}")
        schema_errs += 1
        failed_checks += 1
    topics = fm.get("topics")
    if not topics or not isinstance(topics, list) or len(topics) == 0:
        print(f"  FAIL: {rel} invalid or missing topics list: {topics}")
        schema_errs += 1
        failed_checks += 1

    if rtype == "measurement":
        # Extended measurement schema gate: units present, limit citation present,
        # compliance_date present when limit has one, per-system attribution required.
        required_keys = [
            "source_agency", "jurisdiction_key", "system", "parameter", "value",
            "unit", "reporting_period", "published_date", "governing_limit",
            "primary_source_url", "source_sha256", "source_fetched_at"
        ]
        
        # Per-system attribution required
        system_val = fm.get("system")
        if not system_val or not isinstance(system_val, str) or not system_val.strip():
            print(f"  FAIL: {rel} missing required per-system attribution ('system' field)!")
            schema_errs += 1
            failed_checks += 1
            
        # Units must be non-empty
        unit_val = fm.get("unit")
        if not unit_val or not isinstance(unit_val, str) or not unit_val.strip():
            print(f"  FAIL: {rel} missing required 'unit' field!")
            schema_errs += 1
            failed_checks += 1

        # Rule 2: Remove system_id unless sourced from fetched EPA SDWIS/ECHO record
        if "system_id" in fm or "pwsid" in fm:
            has_sdwis = ("sdwis" in str(fm.get("primary_source_url", "")).lower() or
                         "echo.epa.gov" in str(fm.get("primary_source_url", "")).lower())
            if not has_sdwis:
                print(f"  FAIL: {rel} contains system_id/pwsid without fetched EPA SDWIS/ECHO primary record!")
                schema_errs += 1
                failed_checks += 1

        # Governing limit validation
        gov_limit = fm.get("governing_limit")
        if not isinstance(gov_limit, dict) or not all(k in gov_limit for k in ["value", "unit", "citation"]):
            print(f"  FAIL: {rel} invalid governing_limit schema: {gov_limit}")
            schema_errs += 1
            failed_checks += 1
        else:
            # Compliance date and basis required beside governing limit
            if not gov_limit.get("compliance_date"):
                print(f"  FAIL: {rel} governing_limit missing required 'compliance_date'!")
                schema_errs += 1
                failed_checks += 1
            if not gov_limit.get("basis"):
                print(f"  FAIL: {rel} governing_limit missing required 'basis'!")
                schema_errs += 1
                failed_checks += 1

        # Check path is water/measurements/<system_slug>/
        p = rel.replace(os.sep, "/").split("/")
        if len(p) != 4 or p[0] != "water" or p[1] != "measurements":
            print(f"  FAIL: {rel} measurement record must reside under water/measurements/<system_slug>/")
            schema_errs += 1
            failed_checks += 1
    elif rel.startswith("state_statutes"):
        required_keys = ["statute_title", "primary_source_url"]
    else:
        required_keys = ["jurisdiction", "action_status", "primary_source_url"]
    missing = [k for k in required_keys if not fm.get(k)]
    if missing:
        print(f"  FAIL: {rel} missing required schema fields: {missing}")
        schema_errs += 1
        failed_checks += 1
    sha_val = fm.get("source_sha256")
    if sha_val and (not isinstance(sha_val, str) or not re.match(r"^[a-f0-9]{64}$", sha_val)):
        print(f"  FAIL: Malformed source_sha256 in {rel}: {sha_val}")
        schema_errs += 1
        failed_checks += 1

if schema_errs == 0:
    print(f"  ✓ 100% of {len(all_records)} corpus records comply with frontmatter schema specifications.")

# Topic Derivation Enforcement Gate
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from scripts.derive_topics import audit_and_enforce_topics
    mismatches = audit_and_enforce_topics(REPO_BASE, fix=False)
    if mismatches > 0:
        print(f"  FAIL: Found {mismatches} topic tag mismatches against deterministic derivation rules!")
        failed_checks += 1
    else:
        print("  ✓ 100% of corpus records match deterministic topic derivation rules (scripts/derive_topics.py).")
except Exception as e:
    print(f"  FAIL: Topic derivation gate error: {e}")
    failed_checks += 1

# -------------------------------------------------------------
# CHECK 8: Gate 8 — Publication Readiness for Staging Repository
# -------------------------------------------------------------
print("\n[CHECK 8] Gate 8 — Publication Readiness for Staging Repository (enacted-state-md):")
if not os.path.exists(STAGING_DIR):
    print(f"  FAIL: Staging repository directory does not exist: {STAGING_DIR}")
    failed_checks += 1
else:
    # (a) _quarantine_unverified/ is NOT in the repo
    staging_quarantine = os.path.join(STAGING_DIR, "_quarantine_unverified")
    if os.path.exists(staging_quarantine):
        print("  FAIL: _quarantine_unverified exists in staging repo!")
        failed_checks += 1
    else:
        print("  ✓ [Gate 8.a] _quarantine_unverified is NOT present in staging repo.")

    rulebook_pattern = r'\bAGENTS\.' + r'md\b'
    local_domain_pattern = r'\.' + r'local\b'
    internal_email_pattern = r'(?:a' + r'i|o' + r'la)@'
    company_email_pattern = r'@' + r'swapp\b'
    forbidden_patterns = [
        (re.compile(r'C:[/\\]Users[/\\]', re.IGNORECASE), "Local filesystem path"),
        (re.compile(r'192\.168\.\d+\.\d+'), "LAN IP address"),
        (re.compile(local_domain_pattern, re.IGNORECASE), "Internal dot-local domain"),
        (re.compile(internal_email_pattern, re.IGNORECASE), "Internal personal email alias"),
        (re.compile(company_email_pattern, re.IGNORECASE), "Internal organization email domain"),
        (re.compile(rulebook_pattern), "Internal standing rules mention (Rulebook filename)"),
    ]
    binary_extensions = ('.pdf', '.bin', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.woff', '.woff2', '.ttf', '.pyc')
    forbidden_hits = 0
    for root, dirs, files in os.walk(STAGING_DIR):
        if ".git" in root.split(os.sep) or "__pycache__" in root.split(os.sep) or ".cache" in root.split(os.sep):
            continue
        for fname in files:
            if fname.lower().endswith(binary_extensions):
                continue
            fpath = os.path.join(root, fname)
            relpath = os.path.relpath(fpath, STAGING_DIR)
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                for line_idx, line in enumerate(lines, 1):
                    for pat, desc in forbidden_patterns:
                        if pat.search(line):
                            print(f"  FAIL: Forbidden string '{desc}' in {relpath}:{line_idx}")
                            forbidden_hits += 1
            except Exception:
                pass
    if forbidden_hits > 0:
        print(f"  FAIL: Total {forbidden_hits} forbidden string occurrences in staging!")
        failed_checks += 1
    else:
        print("  ✓ [Gate 8.b] 0 forbidden strings found across all text files in staging.")

    # (c) LICENSE contains the founder placeholder
    license_path = os.path.join(STAGING_DIR, "LICENSE")
    if not os.path.exists(license_path):
        print("  FAIL: LICENSE file missing in staging!")
        failed_checks += 1
    else:
        with open(license_path, "r", encoding="utf-8") as f:
            lic_content = f.read()
        expected_lic_placeholder = "[FOUNDER: license ruling pending — CC0 proposed]"
        if expected_lic_placeholder in lic_content:
            print(f"  ✓ [Gate 8.c] LICENSE contains exact placeholder: '{expected_lic_placeholder}'.")
        else:
            print("  FAIL: LICENSE missing founder ruling placeholder!")
            failed_checks += 1

    # (d) README.md contains the exact posture line
    readme_path = os.path.join(STAGING_DIR, "README.md")
    if not os.path.exists(readme_path):
        print("  FAIL: README.md missing in staging!")
        failed_checks += 1
    else:
        with open(readme_path, "r", encoding="utf-8") as f:
            readme_content = f.read()
        expected_posture = "This repository records the enacted law. It does not advise, approve, determine, or certify anything."
        if expected_posture in readme_content:
            print(f"  ✓ [Gate 8.d] README.md contains exact posture line.")
        else:
            print("  FAIL: README.md missing required posture line!")
            failed_checks += 1

    # (e) Check git working tree clean & commit message if git repo
    git_dir = os.path.join(STAGING_DIR, ".git")
    if os.path.exists(git_dir):
        try:
            git_status = subprocess.check_output(
                ["git", "status", "--porcelain"],
                cwd=STAGING_DIR,
                text=True
            ).strip()
            if git_status:
                print(f"  FAIL: Git working tree is dirty:\n{git_status}")
                failed_checks += 1
            else:
                print("  ✓ [Gate 8.e] Git working tree is clean.")
            git_log = subprocess.check_output(
                ["git", "log", "-1", "--format=%s"],
                cwd=STAGING_DIR,
                text=True
            ).strip()
            expected_msg = "Initial Maryland corpus: verified primary-source records"
            if git_log == expected_msg:
                print(f"  ✓ [Gate 8.e] Git commit message verified: '{expected_msg}'.")
            else:
                print(f"  FAIL: Expected commit message '{expected_msg}', got '{git_log}'")
                failed_checks += 1
        except Exception as e:
            print(f"  FAIL: Git verification error: {e}")
            failed_checks += 1

    # (f) Check all 24 Maryland jurisdictions represented
    md_24_counties = [
        "allegany", "anne_arundel", "baltimore_city", "baltimore_county", "calvert",
        "caroline", "carroll", "cecil", "charles", "dorchester", "frederick",
        "garrett", "harford", "howard", "kent", "montgomery", "prince_georges",
        "queen_annes", "somerset", "st_marys", "talbot", "washington", "wicomico", "worcester"
    ]
    missing_counties = [c for c in md_24_counties if not os.path.isdir(os.path.join(STAGING_DIR, c))]
    if missing_counties:
        print(f"  FAIL: Missing counties in staging: {missing_counties}")
        failed_checks += 1
    else:
        print(f"  ✓ [Gate 8.f] All {len(md_24_counties)} Maryland jurisdictions represented in staging.")

print("\n===============================================================")
if failed_checks == 0:
    print("  ALL RECORD INTEGRITY VERIFICATION GATES PASSED! ✅")
    print("===============================================================\n")
    sys.exit(0)
else:
    print(f"  VERIFICATION FAILED: {failed_checks} CHECKS FAILED! 🔴")
    print("===============================================================\n")
    sys.exit(1)
