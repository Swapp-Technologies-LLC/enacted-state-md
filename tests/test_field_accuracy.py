"""
tests/test_field_accuracy.py
Unit & Regression Tests for Field-Accuracy Verification Gate (ig17).
Swapp Technologies LLC (Maryland)
"""

import os
import sys
import json
import unittest
from pathlib import Path
from datetime import date

REPO_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_DIR))

from scripts.check_field_accuracy import (
    normalize_ws,
    generate_date_renderings,
    generate_identifier_renderings,
    extract_text_from_file,
    find_needle_in_pages,
    check_body_narratives,
    run_field_accuracy_check,
    DATE_RENDERINGS_LIST
)

class TestFieldAccuracy(unittest.TestCase):
    def setUp(self):
        self.pdf_cache = REPO_DIR / ".cache" / "pdf_cache"

    # 1. Found path on real saved source: Montgomery ZTA 23-09 (462401af5834...)
    def test_found_path_real_source(self):
        source_file = self.pdf_cache / "462401af5834c183176774eedc5f415d6ff4c790f8d9495f26ac523b069bdf63.pdf"
        self.assertTrue(source_file.exists(), f"Real fixture {source_file} must exist")
        pages = extract_text_from_file(str(source_file))
        self.assertGreater(len(pages), 0, "Source PDF must have extractable pages")

        # In Montgomery ZTA 23-09 source: "Zoning Text Amendment (ZTA) 23 -09"
        res = find_needle_in_pages(pages, ["ZTA 23-09", "ZTA 23 -09", "23-09"])
        self.assertIsNotNone(res)
        self.assertEqual(res["status"], "found")

    # 2. Not found path on real saved source
    def test_not_found_path_real_source(self):
        source_file = self.pdf_cache / "462401af5834c183176774eedc5f415d6ff4c790f8d9495f26ac523b069bdf63.pdf"
        pages = extract_text_from_file(str(source_file))
        # Invented phrase not present in the document
        res = find_needle_in_pages(pages, ["Invented Legislative Status Phrase 99-99"])
        self.assertIsNone(res, "Invented text must not be found")

    # 3. Source not available locally path
    def test_source_not_available_locally(self):
        missing_source = REPO_DIR / ".cache" / "nonexistent_source_hash_12345.pdf"
        pages = extract_text_from_file(str(missing_source))
        self.assertEqual(len(pages), 0, "Missing source must produce 0 pages")

    # 4. Colon-vs-hyphen title differs -> not found
    def test_colon_vs_hyphen_title_differs(self):
        source_file = self.pdf_cache / "462401af5834c183176774eedc5f415d6ff4c790f8d9495f26ac523b069bdf63.pdf"
        pages = extract_text_from_file(str(source_file))

        # Real source contains: "Farming - Incidental Outdoor Stays"
        # Recorded record title contains colon: "Farming: Incidental Outdoor Stays"
        record_title = "Farming: Incidental Outdoor Stays"
        res_colon = find_needle_in_pages(pages, [record_title])
        self.assertIsNone(res_colon, "Colon title must differ from hyphenated source title -> not found")

        # Hyphenated source title must match
        source_title = "Farming - Incidental Outdoor Stays"
        res_hyphen = find_needle_in_pages(pages, [source_title])
        self.assertIsNotNone(res_hyphen, "Hyphenated title must match source text -> found")

    # 5. ISO record date vs "March 2, 2026" verbal date in source -> found
    def test_iso_vs_verbal_date_renderings(self):
        # Real source: Anne Arundel Bill 18-26 (cd721c41f43e...)
        source_file = self.pdf_cache / "cd721c41f43e5e3ab7d07158caef884dc73db14dc93636b5966d24f64e098529.pdf"
        self.assertTrue(source_file.exists(), f"Real fixture {source_file} must exist")
        pages = extract_text_from_file(str(source_file))

        # Recorded date is ISO: "2026-03-02"
        # Source text carries: "March 2, 2026"
        candidates = generate_date_renderings("2026-03-02")
        self.assertIn("March 2, 2026", candidates)

        res = find_needle_in_pages(pages, candidates)
        self.assertIsNotNone(res, "ISO date 2026-03-02 must match 'March 2, 2026' in source")
        self.assertEqual(res["matched_string"], "March 2, 2026")

    # 6. Computed date absent from source -> not found
    def test_computed_date_absent_from_source(self):
        # Real source: Anne Arundel Bill 28-26 (ff38f058a6f7...)
        # Record carries enacted_date: '2026-05-07' (computed date absent from source text)
        source_file = self.pdf_cache / "ff38f058a6f7bfd3a120beed401433f4e094186c2e5d72f1fa5719397060aa61.pdf"
        self.assertTrue(source_file.exists(), f"Real fixture {source_file} must exist")
        pages = extract_text_from_file(str(source_file))

        candidates = generate_date_renderings("2026-05-07")
        res = find_needle_in_pages(pages, candidates)
        self.assertIsNone(res, "Computed date absent from source text must be not found")

    # 7. Narrative check detects editorial calculations & characterisations
    def test_narrative_sentence_detection(self):
        body = """
        ## 2. Legislative Chronology
        - **Passed:** June 1, 2026 (unanimously passed with adopted amendments 1, 2, 3)
        - **Effective:** July 20, 2026 (45 days from enactment following executive transmission)
        - **Review:** Not enacted as law.
        ```diff
        + Quoted statutory diff text should be ignored 45 days from enactment
        ```
        """
        findings = check_body_narratives(body)
        descs = [f["pattern_desc"] for f in findings]
        self.assertTrue(any("45 days from" in d for d in descs), "Must flag interval calculation")
        self.assertTrue(any("unanimously passed" in d for d in descs), "Must flag voting characterisation")
        self.assertTrue(any("not enacted as law" in d for d in descs), "Must flag status characterisation")

    # 8. Sidecar generation and schema integrity
    def test_sidecar_generation(self):
        exit_code = run_field_accuracy_check(str(REPO_DIR))
        self.assertEqual(exit_code, 0, "Field-accuracy audit must return 0 in report-only mode")

        sidecar_path = REPO_DIR / "verification" / "field_accuracy.json"
        self.assertTrue(sidecar_path.exists(), "Sidecar verification/field_accuracy.json must exist")

        with open(sidecar_path, "r", encoding="utf-8") as sf:
            data = json.load(sf)

        self.assertIn("repository", data)
        self.assertIn("records", data)
        self.assertGreater(len(data["records"]), 0)

if __name__ == "__main__":
    unittest.main()
