import os
import sys
import re
import json
import yaml
from datetime import datetime, timezone, timedelta
from xml.sax.saxutils import escape

# Ensure UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if os.path.exists(os.path.join(ROOT_DIR, "anne_arundel")):
    REPO_BASE = ROOT_DIR
    FEEDS_DIR = os.path.join(ROOT_DIR, "feeds")
elif os.path.exists(os.path.join(ROOT_DIR, "staging", "enacted-state-md", "anne_arundel")):
    REPO_BASE = os.path.join(ROOT_DIR, "staging", "enacted-state-md")
    FEEDS_DIR = os.path.join(REPO_BASE, "feeds")
else:
    cand = os.path.abspath(os.path.join(ROOT_DIR, "..", "staging", "enacted-state-md"))
    if os.path.exists(os.path.join(cand, "anne_arundel")):
        REPO_BASE = cand
        FEEDS_DIR = os.path.join(REPO_BASE, "feeds")
    else:
        REPO_BASE = os.path.join(ROOT_DIR, "staging", "enacted-state-md")
        FEEDS_DIR = os.path.join(REPO_BASE, "feeds")

FREE_TIER_DELAY_DAYS = int(os.environ.get("FREE_TIER_DELAY_DAYS", 0))
FEED_BASE_URL = os.environ.get("FEED_BASE_URL", "https://<org>.github.io/enacted-state-md/")

POSTURE_LINE = "Records what changed in enacted land-use law and public water quality. Does not advise, approve, determine, or certify anything."

BANNED_PHRASES = [
    "guarantee", "verified", "certified", "approved", "determination",
    "by-right", "may now", "advise", "score", "grade", "safe", "unsafe",
    "risk", "healthy", "contaminated"
]

JURISDICTION_DISPLAY_NAMES = {
    "anne_arundel": "Anne Arundel County",
    "baltimore_city": "City of Baltimore",
    "baltimore_county": "Baltimore County",
    "frederick": "Frederick County",
    "howard": "Howard County",
    "montgomery": "Montgomery County",
    "prince_georges": "Prince George's County",
    "statewide": "State of Maryland",
    "wssc": "WSSC Water (Montgomery & Prince George's)"
}

JURISDICTION_HOMEPAGES = {
    "anne_arundel": "https://www.aacounty.org",
    "baltimore_city": "https://baltimore.legistar.com",
    "baltimore_county": "https://countycouncil.baltimorecountymd.gov",
    "frederick": "https://frederickcountymd.gov",
    "howard": "https://apps.howardcountymd.gov/olis",
    "montgomery": "https://www.montgomerycountymd.gov/council",
    "prince_georges": "https://princegeorgescountymd.legistar.com",
    "statewide": "https://mgaleg.maryland.gov",
    "wssc": "https://www.wsscwater.com"
}

TOPIC_DISPLAY_NAMES = {
    "zoning": "Land-Use & Zoning",
    "water": "Water Quality & Resources",
    "pfas": "PFAS Forever Chemicals",
    "data-center": "Data Centers"
}

def normalize_rfc3339(d_str: str) -> str:
    if not d_str or str(d_str).lower() in ["none", "n/a", "[pending verification]"]:
        return None
    d_str = str(d_str).strip()
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})", d_str)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}T00:00:00Z"
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})", d_str)
    if m:
        return f"{int(m.group(3)):04d}-{int(m.group(1)):02d}-{int(m.group(2)):02d}T00:00:00Z"
    if "T" in d_str:
        clean = d_str.split(".")[0].rstrip("Z")
        return f"{clean}Z"
    return None

def parse_date_to_dt(rfc_str: str) -> datetime:
    return datetime.strptime(rfc_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)

def extract_dates(fm: dict):
    date_fields = [
        "effective_date", "effective_date_base", "effective_date_overridden_amendments",
        "enacted_date", "adopted_date", "passed_date", "executive_action_date",
        "veto_override_date", "withdrawn_date", "public_hearing_date", "introduced_date"
    ]
    found = []
    for k in date_fields:
        v = fm.get(k)
        norm = normalize_rfc3339(v)
        if norm:
            found.append((k, norm))
    return found

def build_summary_line(fm: dict) -> str:
    status = fm.get("action_status", "Active")
    role_parts = []
    
    intro = fm.get("introduced_date")
    if intro and status in ["Introduced", "Worksession", "Withdrawn", "Pending Committee Review (Public Hearing Held)"]:
        d_norm = normalize_rfc3339(intro)
        if d_norm: role_parts.append(f"Introduced {d_norm[:10]}")
            
    hearing = fm.get("public_hearing_date") or fm.get("hearing_date")
    if hearing and status in ["Introduced", "Worksession", "Pending Committee Review (Public Hearing Held)"]:
        d_norm = normalize_rfc3339(hearing)
        if d_norm: role_parts.append(f"Hearing {d_norm[:10]}")
            
    passed = fm.get("passed_date") or fm.get("adopted_date")
    if passed and (status == "Enacted" or "Passed" in status):
        d_norm = normalize_rfc3339(passed)
        if d_norm: role_parts.append(f"Passed {d_norm[:10]}")
            
    signed = fm.get("enacted_date") or fm.get("executive_action_date")
    if signed and (status == "Enacted" or "Passed" in status) and status != "Passed (Veto Overridden)":
        d_norm = normalize_rfc3339(signed)
        if d_norm: role_parts.append(f"Signed {d_norm[:10]}")
            
    override = fm.get("veto_override_date")
    if override and "Veto Overridden" in status:
        d_norm = normalize_rfc3339(override)
        if d_norm: role_parts.append(f"Override {d_norm[:10]}")
            
    withdrawn = fm.get("withdrawn_date")
    if withdrawn and status == "Withdrawn":
        d_norm = normalize_rfc3339(withdrawn)
        if d_norm: role_parts.append(f"Withdrawn {d_norm[:10]}")
            
    eff = fm.get("effective_date") or fm.get("effective_date_base")
    if eff and (status == "Enacted" or "Passed" in status):
        d_norm = normalize_rfc3339(eff)
        if d_norm: role_parts.append(f"Effective {d_norm[:10]}")
            
    if role_parts:
        summary_line = f"{status}. " + " · ".join(role_parts)
    else:
        summary_line = f"{status}."
        
    if "§" in summary_line or summary_line.startswith("+") or summary_line.startswith("-") or summary_line.startswith("["):
        raise ValueError(f"Summary contains prohibited statutory diff/markers: {summary_line}")
        
    return summary_line

def check_banned_phrases(text: str, context: str):
    t_lower = text.lower()
    for bp in BANNED_PHRASES:
        pattern = r"\b" + re.escape(bp) + r"\b"
        if re.search(pattern, t_lower):
            raise ValueError(f"Banned phrase '{bp}' detected in {context}: '{text}'")

def load_all_verified_items(repo_base: str):
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=FREE_TIER_DELAY_DAYS) if FREE_TIER_DELAY_DAYS > 0 else None
    
    all_items = []
    target_jurs = [
        "anne_arundel", "baltimore_city", "baltimore_county", "frederick",
        "howard", "montgomery", "prince_georges"
    ]
    
    # 1. County-level Legislative records
    for jur in target_jurs:
        jur_dir = os.path.join(repo_base, jur)
        if not os.path.isdir(jur_dir):
            continue
            
        candidate_files = []
        cb_dir = os.path.join(jur_dir, "council_bills")
        zta_dir = os.path.join(jur_dir, "zta_amendments")
        
        if os.path.isdir(cb_dir):
            for f in sorted(os.listdir(cb_dir)):
                if f.endswith(".md"): candidate_files.append(os.path.join(cb_dir, f))
        if os.path.isdir(zta_dir):
            for f in sorted(os.listdir(zta_dir)):
                if f.endswith(".md"): candidate_files.append(os.path.join(zta_dir, f))
                
        for fpath in candidate_files:
            with open(fpath, "r", encoding="utf-8") as fh:
                content = fh.read()
            parts = content.split("---", 2)
            if len(parts) < 3: continue
            fm = yaml.safe_load(parts[1]) or {}
            
            sha = fm.get("source_sha256")
            fetched_at = fm.get("source_fetched_at")
            primary_url = fm.get("primary_source_url")
            if not sha or not fetched_at or not primary_url: continue
            
            file_stem = os.path.splitext(os.path.basename(fpath))[0]
            stable_id = f"{jur}/{file_stem}"
            jur_display = JURISDICTION_DISPLAY_NAMES.get(jur, jur.replace("_", " ").title())
            
            bnum = fm.get("bill_number") or fm.get("zta_number") or fm.get("ordinance_number") or file_stem
            rec_title = fm.get("title") or bnum
            item_title = f"{jur_display}: {bnum} — {rec_title}"
            category = fm.get("action_status", "Active")
            summary = build_summary_line(fm)
            
            dates = extract_dates(fm)
            if dates:
                updated = max([d[1] for d in dates])
                published = min([d[1] for d in dates])
            else:
                updated = normalize_rfc3339(fetched_at) or now.strftime("%Y-%m-%dT%H:%M:%SZ")
                published = updated
                
            if cutoff and parse_date_to_dt(updated) > cutoff: continue
            check_banned_phrases(item_title, f"{stable_id} title")
            check_banned_phrases(summary, f"{stable_id} summary")
            
            item = {
                "id": stable_id,
                "title": item_title,
                "updated": updated,
                "published": published,
                "link": primary_url,
                "summary": summary,
                "category": category,
                "jurisdiction": jur,
                "jurisdictions": [jur],
                "topic": fm.get("topic", "zoning"),
                "topics": fm.get("topics", ["zoning"]),
                "record_type": fm.get("record_type", "legislative"),
                "source_file": fpath,
                "source_sha256": sha,
                "source_fetched_at": fetched_at
            }
            all_items.append(item)

    # 2. Measurement records under water/measurements/<system_slug>/
    meas_dir = os.path.join(repo_base, "water", "measurements")
    if os.path.isdir(meas_dir):
        for root, dirs, files in os.walk(meas_dir):
            for f in sorted(files):
                if not f.endswith(".md"): continue
                fpath = os.path.join(root, f)
                with open(fpath, "r", encoding="utf-8") as fh:
                    content = fh.read()
                parts = content.split("---", 2)
                if len(parts) < 3: continue
                fm = yaml.safe_load(parts[1]) or {}
                
                sha = fm.get("source_sha256")
                fetched_at = fm.get("source_fetched_at")
                primary_url = fm.get("primary_source_url")
                if not sha or not fetched_at or not primary_url: continue
                
                sys_slug = os.path.basename(root)
                file_stem = os.path.splitext(f)[0]
                stable_id = f"water/measurements/{sys_slug}/{file_stem}"
                
                system_name = fm.get("system", sys_slug)
                agency = fm.get("source_agency", "Agency")
                param = fm.get("parameter", file_stem)
                val = fm.get("value", "")
                unit = fm.get("unit", "")
                pub_date = str(fm.get("published_date", ""))
                
                # Jurisdictions attribution (supports multi-county systems like WSSC)
                jurs = fm.get("jurisdictions")
                if not jurs:
                    primary_jur = fm.get("jurisdiction_key", "statewide")
                    jurs = [primary_jur]
                
                jur_display_parts = [JURISDICTION_DISPLAY_NAMES.get(j, j.replace("_", " ").title()) for j in jurs]
                jur_display = " & ".join(jur_display_parts) if len(jur_display_parts) > 1 else jur_display_parts[0]
                
                if unit and unit != "status":
                    item_title = f"{system_name}: {param} — {val} {unit} (Reported {pub_date})"
                else:
                    item_title = f"{system_name}: {param} — {val} (Reported {pub_date})"
                category = "Measurement"
                
                # Rule: A measurement item may never render value-vs-limit without the compliance date beside it.
                gov_limit = fm.get("governing_limit", {})
                limit_val = gov_limit.get("value", "")
                limit_unit = gov_limit.get("unit", "")
                limit_cit = gov_limit.get("citation", "")
                comp_date = gov_limit.get("compliance_date", "")
                basis = gov_limit.get("basis", "")
                limit_status = gov_limit.get("limit_status", "")
                
                if not comp_date and limit_val:
                    raise ValueError(f"Measurement record {stable_id} missing required compliance_date beside governing limit!")
                    
                limit_notes = []
                if comp_date:
                    limit_notes.append(f"compliance date: {comp_date}")
                if basis:
                    limit_notes.append(f"basis: {basis}")
                if limit_status and limit_status != "In force":
                    limit_notes.append(f"status: {limit_status}")
                    
                limit_notes_str = "; ".join(limit_notes)
                if limit_notes_str:
                    limit_clause = f"Governing requirement: {limit_val} {limit_unit} ({limit_cit}; {limit_notes_str})"
                else:
                    limit_clause = f"Governing requirement: {limit_val} {limit_unit} ({limit_cit})"
                    
                finding = fm.get("agency_finding")
                if finding:
                    summary = f"As reported by {agency} for {system_name}: {finding}. {limit_clause}."
                else:
                    summary = f"As reported by {agency} for {system_name}: {val} {unit}. {limit_clause}."
                    
                updated = normalize_rfc3339(pub_date) or normalize_rfc3339(fetched_at)
                published = updated
                
                if cutoff and parse_date_to_dt(updated) > cutoff: continue
                check_banned_phrases(item_title, f"{stable_id} title")
                check_banned_phrases(summary, f"{stable_id} summary")
                
                item = {
                    "id": stable_id,
                    "title": item_title,
                    "updated": updated,
                    "published": published,
                    "link": primary_url,
                    "summary": summary,
                    "category": category,
                    "jurisdiction": jurs[0],
                    "jurisdictions": jurs,
                    "system": system_name,
                    "topic": "water",
                    "topics": fm.get("topics", ["water"]),
                    "record_type": "measurement",
                    "source_file": fpath,
                    "source_sha256": sha,
                    "source_fetched_at": fetched_at
                }
                all_items.append(item)

    # 3. State Statutes
    statutes_dir = os.path.join(repo_base, "state_statutes")
    if os.path.isdir(statutes_dir):
        for sf in sorted(os.listdir(statutes_dir)):
            if not sf.endswith(".md"): continue
            spath = os.path.join(statutes_dir, sf)
            with open(spath, "r", encoding="utf-8") as sfh:
                content = sfh.read()
            parts = content.split("---", 2)
            if len(parts) < 3: continue
            fm = yaml.safe_load(parts[1]) or {}
            
            stitle = fm.get("statute_title", sf)
            surl = fm.get("primary_source_url", "https://mgaleg.maryland.gov")
            stem = os.path.splitext(sf)[0]
            stable_id = f"state_statutes/{stem}"
            
            topics = fm.get("topics", [fm.get("topic", "zoning")])
            summary = "Statewide statutory mandate covering land-use, coastal critical areas, and local authority."
            
            item = {
                "id": stable_id,
                "title": f"Maryland Annotated Code: {stitle}",
                "updated": "2026-01-01T00:00:00Z",
                "published": "2026-01-01T00:00:00Z",
                "link": surl,
                "summary": summary,
                "category": "State Statute",
                "jurisdiction": "statewide",
                "jurisdictions": ["statewide"],
                "topic": fm.get("topic", "zoning"),
                "topics": topics,
                "record_type": "legislative",
                "source_file": spath,
                "source_sha256": None,
                "source_fetched_at": None
            }
            all_items.append(item)

    return all_items

def render_atom_feed(feed_id: str, title: str, self_link: str, items: list, last_ingested: str) -> str:
    latest_updated = items[0]["updated"] if items else last_ingested
    entries_xml = []
    for it in items:
        entry = f"""  <entry>
    <id>{escape(it['id'])}</id>
    <title>{escape(it['title'])}</title>
    <updated>{escape(it['updated'])}</updated>
    <published>{escape(it['published'])}</published>
    <link rel="alternate" type="text/html" href="{escape(it['link'])}"/>
    <summary type="text">{escape(it['summary'])}</summary>
    <category term="{escape(it['category'])}"/>
  </entry>"""
        entries_xml.append(entry)
        
    entries_str = "\n".join(entries_xml)
    atom = f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <id>{escape(feed_id)}</id>
  <title>{escape(title)}</title>
  <subtitle>{escape(POSTURE_LINE)}</subtitle>
  <updated>{escape(latest_updated)}</updated>
  <link rel="self" href="{escape(self_link)}"/>
  <generator uri="{escape(FEED_BASE_URL)}">Enacted Syndication Engine</generator>
{entries_str}
</feed>
"""
    return atom

def render_json_feed(feed_title: str, home_page: str, feed_url: str, items: list, last_ingested: str) -> dict:
    feed_items = []
    for it in items:
        feed_items.append({
            "id": it["id"],
            "url": it["link"],
            "title": it["title"],
            "summary": it["summary"],
            "date_published": it["published"],
            "date_modified": it["updated"],
            "tags": [it["category"]] + it.get("topics", [])
        })
        
    feed_doc = {
        "version": "https://jsonfeed.org/version/1.1",
        "title": feed_title,
        "home_page_url": home_page,
        "feed_url": feed_url,
        "description": POSTURE_LINE,
        "_last_ingested": last_ingested,
        "items": feed_items
    }
    return feed_doc

def generate_all_feeds():
    print("===============================================================")
    print("  ENACTED / TOPOLOGY-AWARE SYNDICATION FEEDS GENERATOR")
    print("===============================================================\n")
    
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    all_items = load_all_verified_items(REPO_BASE)
    
    os.makedirs(FEEDS_DIR, exist_ok=True)
    emitted_files = []
    ACTIVE_TOPICS = ["zoning", "water"]
    
    # 1. Per-(Jurisdiction x Topic) Feeds: feeds/<jur>/<topic>.atom|json
    # Map items to (jur, topic) pairs, honoring multi-jurisdiction attribution
    jur_topic_map = {}
    for it in all_items:
        jurs = it.get("jurisdictions", [it["jurisdiction"]])
        for jur in jurs:
            if jur == "statewide": continue
            for top in it.get("topics", []):
                if top not in ACTIVE_TOPICS: continue
                key = (jur, top)
                if it not in jur_topic_map.setdefault(key, []):
                    jur_topic_map[key].append(it)
            
    for (jur, topic), items in sorted(jur_topic_map.items()):
        items.sort(key=lambda x: x["updated"], reverse=True)
        jur_dir = os.path.join(FEEDS_DIR, jur)
        os.makedirs(jur_dir, exist_ok=True)
        
        jur_display = JURISDICTION_DISPLAY_NAMES.get(jur, jur.replace("_", " ").title())
        topic_display = TOPIC_DISPLAY_NAMES.get(topic, topic.replace("_", " ").title())
        feed_title = f"Enacted — {jur_display} {topic_display} Feed"
        home_page = JURISDICTION_HOMEPAGES.get(jur, "https://mgaleg.maryland.gov")
        
        rel_atom = f"feeds/{jur}/{topic}.atom"
        rel_json = f"feeds/{jur}/{topic}.json"
        
        atom_path = os.path.join(jur_dir, f"{topic}.atom")
        json_path = os.path.join(jur_dir, f"{topic}.json")
        
        atom_content = render_atom_feed(
            feed_id=f"urn:enacted:feed:md:{jur}:{topic}",
            title=feed_title,
            self_link=rel_atom,
            items=items,
            last_ingested=now_iso
        )
        with open(atom_path, "w", encoding="utf-8") as f:
            f.write(atom_content)
        emitted_files.append((atom_path, len(items)))
        
        json_doc = render_json_feed(
            feed_title=feed_title,
            home_page=home_page,
            feed_url=rel_json,
            items=items,
            last_ingested=now_iso
        )
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_doc, f, indent=2)
        emitted_files.append((json_path, len(items)))
        
        print(f"  ✓ {jur.ljust(16)} × {topic.ljust(10)}: Emitted Atom & JSON ({len(items)} items)")

    # 2. Topic Aggregate Feeds: feeds/topics/<topic>.atom|json
    topics_dir = os.path.join(FEEDS_DIR, "topics")
    os.makedirs(topics_dir, exist_ok=True)
    
    for topic in ["zoning", "water"]:
        topic_items = []
        for it in all_items:
            if topic in it.get("topics", []) and it not in topic_items:
                topic_items.append(it)
        topic_items.sort(key=lambda x: x["updated"], reverse=True)
        
        topic_display = TOPIC_DISPLAY_NAMES.get(topic, topic.title())
        feed_title = f"Enacted — Maryland {topic_display} Topic Feed"
        rel_atom = f"feeds/topics/{topic}.atom"
        rel_json = f"feeds/topics/{topic}.json"
        
        atom_path = os.path.join(topics_dir, f"{topic}.atom")
        json_path = os.path.join(topics_dir, f"{topic}.json")
        
        atom_content = render_atom_feed(
            feed_id=f"urn:enacted:feed:md:topic:{topic}",
            title=feed_title,
            self_link=rel_atom,
            items=topic_items,
            last_ingested=now_iso
        )
        with open(atom_path, "w", encoding="utf-8") as f:
            f.write(atom_content)
        emitted_files.append((atom_path, len(topic_items)))
        
        json_doc = render_json_feed(
            feed_title=feed_title,
            home_page="https://mgaleg.maryland.gov",
            feed_url=rel_json,
            items=topic_items,
            last_ingested=now_iso
        )
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_doc, f, indent=2)
        emitted_files.append((json_path, len(topic_items)))
        
        print(f"  ✓ topic:{topic.ljust(10)} (Statewide) : Emitted Atom & JSON ({len(topic_items)} items)")

    # 3. Master Statewide Zoning Feed (Compatibility): feeds/zoning.atom|json
    zoning_all = [it for it in all_items if "zoning" in it.get("topics", []) and it["jurisdiction"] != "statewide"]
    zoning_all.sort(key=lambda x: x["updated"], reverse=True)
    
    state_atom_path = os.path.join(FEEDS_DIR, "zoning.atom")
    state_json_path = os.path.join(FEEDS_DIR, "zoning.json")
    
    state_atom = render_atom_feed(
        feed_id="urn:enacted:feed:md",
        title="Enacted — Maryland Statewide Land-Use & Zoning Feed",
        self_link="feeds/zoning.atom",
        items=zoning_all,
        last_ingested=now_iso
    )
    with open(state_atom_path, "w", encoding="utf-8") as f:
        f.write(state_atom)
    emitted_files.append((state_atom_path, len(zoning_all)))
    
    state_json = render_json_feed(
        feed_title="Enacted — Maryland Statewide Land-Use & Zoning Feed",
        home_page="https://mgaleg.maryland.gov",
        feed_url="feeds/zoning.json",
        items=zoning_all,
        last_ingested=now_iso
    )
    with open(state_json_path, "w", encoding="utf-8") as f:
        json.dump(state_json, f, indent=2)
    emitted_files.append((state_json_path, len(zoning_all)))
    print(f"  ✓ md (Statewide Aggregate) : Emitted Atom & JSON ({len(zoning_all)} items)")

    print(f"\nFeed generation complete. Total files written: {len(emitted_files)}")
    return emitted_files

if __name__ == "__main__":
    generate_all_feeds()
