#!/usr/bin/env python3
"""
scripts/backfill_file_last_saved.py

Backfills file_last_saved: YYYY-MM-DD into every water measurement record
whose report prints no publication date, by reading the pinned PDF's metadata
(/ModDate, else /CreationDate) from .cache/pdf_cache/<sha256>.bin.
Prints record path + date.
Governed by Rule 10: Zero model calls. Pure deterministic code.
"""

import os
import sys
import re
import yaml
from pathlib import Path

REPO_MD = Path(__file__).resolve().parent.parent
ROOT_STAGING = REPO_MD.parent

SEARCH_CACHE_DIRS = [
    ROOT_STAGING / "enacted-state-md" / ".cache" / "pdf_cache",
    ROOT_STAGING / "enacted-state-dc" / ".cache" / "pdf_cache",
    ROOT_STAGING / "enacted-state-va" / ".cache" / "pdf_cache",
]

STATE_REPOS = [
    ROOT_STAGING / "enacted-state-md",
    ROOT_STAGING / "enacted-state-dc",
    ROOT_STAGING / "enacted-state-va",
]


def extract_saved_date_from_bin(pdf_path: Path) -> str:
    """Reads /ModDate or /CreationDate from raw bytes or pdfplumber."""
    try:
        import pdfplumber
        with pdfplumber.open(str(pdf_path)) as pdf:
            meta = pdf.metadata or {}
            mdate = meta.get("ModDate") or meta.get("CreationDate")
            if mdate:
                m = re.search(r"(\d{4})(\d{2})(\d{2})", mdate)
                if m:
                    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    except Exception:
        pass

    raw = pdf_path.read_bytes()
    m = re.search(rb'/ModDate\s*\(\s*(?:D:)?(\d{4})(\d{2})(\d{2})', raw)
    if not m:
        m = re.search(rb'/CreationDate\s*\(\s*(?:D:)?(\d{4})(\d{2})(\d{2})', raw)
    if m:
        return f"{m.group(1).decode()}-{m.group(2).decode()}-{m.group(3).decode()}"

    raise ValueError(f"Could not read /ModDate or /CreationDate from {pdf_path}")


def find_cached_pdf(sha256: str) -> Path:
    for cdir in SEARCH_CACHE_DIRS:
        p = cdir / f"{sha256}.bin"
        if p.is_file():
            return p
    raise FileNotFoundError(f"No cached PDF found for sha256: {sha256}")


def backfill_record(record_path: Path):
    text = record_path.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if len(parts) < 3:
        return

    fm = yaml.safe_load(parts[1]) or {}
    if fm.get("record_type") != "measurement":
        return

    pub = fm.get("published_date")
    if pub and str(pub).strip() != "" and str(pub).strip().lower() != "none" and not str(pub).startswith("["):
        # Record prints a publication date; skip
        return

    sha = fm.get("source_sha256")
    if not sha:
        raise ValueError(f"Record {record_path} has no source_sha256")

    cached_pdf = find_cached_pdf(sha)
    date_iso = extract_saved_date_from_bin(cached_pdf)

    # Insert or update file_last_saved in frontmatter
    # Keep frontmatter structure cleanly: insert right after source_fetched_at if present, or before contact/topic/---
    fm_lines = parts[1].splitlines()
    new_fm_lines = []
    inserted = False
    for line in fm_lines:
        if line.startswith("file_last_saved:"):
            new_fm_lines.append(f"file_last_saved: '{date_iso}'")
            inserted = True
            continue
        new_fm_lines.append(line)
        if line.startswith("source_fetched_at:"):
            new_fm_lines.append(f"file_last_saved: '{date_iso}'")
            inserted = True

    if not inserted:
        new_fm_lines.append(f"file_last_saved: '{date_iso}'")

    new_text = "---" + "\n".join(new_fm_lines) + "\n---" + parts[2]
    record_path.write_text(new_text, encoding="utf-8")
    print(f"{record_path} {date_iso}")


def main():
    for repo in STATE_REPOS:
        measurements_dir = repo / "water" / "measurements"
        if not measurements_dir.is_dir():
            continue
        for rpath in sorted(measurements_dir.glob("**/*.md")):
            backfill_record(rpath)


if __name__ == "__main__":
    main()
