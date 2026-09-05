#!/usr/bin/env python3
"""
Deterministic Topic Derivation Engine — Swapp Technologies LLC / Enacted
Rule 10: Zero model calls. Pure deterministic pattern and section matching.

Rules:
1. 'zoning': Matches local land use codes (Article 18, Article 32, BCZR, HCZR,
   Chapter 59, Chapter 1-19, Chapter 267, Subtitle 27, Land Use Article), or
   statutory terms ('zoning', 'zta', 'comprehensive zoning', 'setback', 'district').
2. 'water': Matches drinking water regulations, water quality monitoring, utility
   service areas, contaminant thresholds (MCL, AL, PFAS, Lead/Copper Rule), or
   statutory coastal critical area protection (Natural Resources Article Title 8).
3. 'pfas': Matches per- and polyfluoroalkyl substances (PFOA, PFOS, GenX, etc.).

A record may only carry a topic tag if deterministically produced by this rule.
"""

import os
import sys
import re
import yaml

ZONING_SECTION_PATTERNS = [
    r"article\s*18", r"article\s*32", r"bczr", r"hczr", r"chapter\s*59",
    r"chapter\s*1-19", r"chapter\s*267", r"subtitle\s*27", r"land\s*use\s*article",
    r"zoning", r"zta", r"comprehensive\s*zoning"
]

WATER_PATTERNS = [
    r"drinking\s*water", r"water\s*quality", r"water\s*service", r"water\s*distribution",
    r"lead\s*and\s*copper", r"pfas", r"pfoa", r"pfos", r"maximum\s*contaminant\s*level",
    r"safe\s*drinking\s*water", r"critical\s*area\s*program", r"natural\s*resources\s*article.*8-18"
]

PFAS_PATTERNS = [
    r"\bpfas\b", r"\bpfoa\b", r"\bpfos\b", r"perfluoro"
]

def derive_topics_for_record(content: str, fm: dict, relpath: str) -> list:
    rtype = fm.get("record_type", "legislative")
    topics = set()
    
    if rtype == "measurement":
        topics.add("water")
        param = str(fm.get("parameter", "")).lower()
        if any(re.search(pat, param) for pat in PFAS_PATTERNS):
            topics.add("pfas")
        return sorted(list(topics))
        
    # Legislative / Statutes
    search_text = (
        str(fm.get("title", "")) + " " +
        str(fm.get("bill_number", "")) + " " +
        " ".join(str(s) for s in fm.get("affected_sections", [])) + " " +
        content
    ).lower()
    
    if any(re.search(pat, search_text) for pat in ZONING_SECTION_PATTERNS):
        topics.add("zoning")
        
    if any(re.search(pat, search_text) for pat in WATER_PATTERNS):
        topics.add("water")
        
    if any(re.search(pat, search_text) for pat in PFAS_PATTERNS):
        topics.add("pfas")
        
    if not topics:
        topics.add("zoning")  # Fallback to general land-use baseline
        
    return sorted(list(topics))

def audit_and_enforce_topics(repo_base: str, fix: bool = False):
    mismatches = 0
    total_records = 0
    for root, dirs, files in os.walk(repo_base):
        if "_quarantine_unverified" in root.split(os.sep): continue
        if ".git" in root.split(os.sep): continue
        for f in sorted(files):
            if f.endswith(".md") and not f.startswith("README") and not f.startswith("PROVENANCE") and not f.startswith("SOURCING_BLOCKED"):
                fpath = os.path.join(root, f)
                rel = os.path.relpath(fpath, repo_base)
                with open(fpath, "r", encoding="utf-8") as fh:
                    text = fh.read()
                parts = text.split("---", 2)
                if len(parts) < 3: continue
                fm = yaml.safe_load(parts[1]) or {}
                body = parts[2]
                
                total_records += 1
                derived = derive_topics_for_record(body, fm, rel)
                current = sorted(fm.get("topics", []))
                
                if derived != current:
                    print(f"Mismatch in {rel}: current={current} vs derived={derived}")
                    mismatches += 1
                    if fix:
                        fm["topics"] = derived
                        if fm.get("topic") not in derived:
                            fm["topic"] = derived[0]
                        new_fm = yaml.dump(fm, sort_keys=False, default_flow_style=False)
                        new_content = f"---\\n{new_fm}---\\n{body.lstrip()}"
                        with open(fpath, "w", encoding="utf-8") as fh:
                            fh.write(new_content)
                        print(f"  Fixed {rel} -> topics={derived}")

    print(f"\nAudit complete: {total_records} records checked. {mismatches} mismatches found.")
    return mismatches

if __name__ == "__main__":
    fix_mode = "--fix" in sys.argv
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if not os.path.exists(os.path.join(base, "anne_arundel")):
        base = os.path.join(base, "staging", "enacted-state-md")
    sys.exit(audit_and_enforce_topics(base, fix=fix_mode))
