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
    measure_source_text,
    MIN_TOTAL_CHARS,
    MIN_CHARS_PER_PAGE,
    check_measurement_record,
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
        self.assertIn("extraction_thresholds", data)
        self.assertEqual(data["extraction_thresholds"]["min_total_chars"], 200)
        self.assertEqual(data["extraction_thresholds"]["min_chars_per_page"], 50.0)
        self.assertIn("summary", data)
        self.assertIn("source_files", data)


    # 9. Measurement check passes on fixed Crownsville and Glen Burnie records
    def test_measurement_fixed_records_pass(self):
        import yaml
        c_path = REPO_DIR / "water" / "measurements" / "aa_crownsville" / "lead_tap_2025.md"
        with open(c_path, "r", encoding="utf-8") as f:
            fm_c = yaml.safe_load(f.read().split("---")[1])
        passed_c, msg_c, res_c, _ = check_measurement_record(fm_c, str(c_path), str(REPO_DIR))
        self.assertTrue(passed_c, f"Fixed Crownsville must pass all gates: {msg_c}")
        self.assertEqual(res_c["reported_value"]["result"], "found")
        self.assertEqual(res_c["reported_value"]["column_header"], "Crownsville Zone")

        gb_path = REPO_DIR / "water" / "measurements" / "aa_glen_burnie" / "copper_tap_2025.md"
        with open(gb_path, "r", encoding="utf-8") as f:
            fm_gb = yaml.safe_load(f.read().split("---")[1])
        passed_gb, msg_gb, res_gb, _ = check_measurement_record(fm_gb, str(gb_path), str(REPO_DIR))
        self.assertTrue(passed_gb, f"Fixed Glen Burnie must pass all gates: {msg_gb}")
        self.assertEqual(res_gb["reported_value"]["result"], "found")
        self.assertEqual(res_gb["reported_value"]["column_header"], "Glen Burnie/Broadneck Zone")

    # 10. Measurement check fails on old wrong Crownsville (<2.0, Page 6)
    def test_measurement_old_wrong_crownsville_fails(self):
        import yaml
        c_path = REPO_DIR / "water" / "measurements" / "aa_crownsville" / "lead_tap_2025.md"
        with open(c_path, "r", encoding="utf-8") as f:
            fm_c = yaml.safe_load(f.read().split("---")[1])
        # Inject old wrong values
        fm_c_old = dict(fm_c)
        fm_c_old["value"] = "<2.0"
        fm_c_old["determination"] = dict(fm_c["determination"])
        fm_c_old["determination"]["source_page"] = "Page 6"
        passed, msg, res, fails = check_measurement_record(fm_c_old, str(c_path), str(REPO_DIR))
        self.assertFalse(passed, "Old wrong Crownsville must fail verification gate")
        self.assertTrue(any("reported_value '<2.0'" in f for f in fails), f"Must fail on reported_value: {fails}")
        self.assertIn(res["reported_value"]["result"], ["not found", "found on wrong page (13)"])

    # 11. Measurement check fails on old wrong Glen Burnie (0.07, Page 6, reporting_period 2023)
    def test_measurement_old_wrong_glen_burnie_fails(self):
        import yaml
        gb_path = REPO_DIR / "water" / "measurements" / "aa_glen_burnie" / "copper_tap_2025.md"
        with open(gb_path, "r", encoding="utf-8") as f:
            fm_gb = yaml.safe_load(f.read().split("---")[1])
        # Inject old wrong values
        fm_gb_old = dict(fm_gb)
        fm_gb_old["value"] = "0.07"
        fm_gb_old["reporting_period"] = "2023"
        fm_gb_old["determination"] = dict(fm_gb["determination"])
        fm_gb_old["determination"]["source_page"] = "Page 6"
        passed, msg, res, fails = check_measurement_record(fm_gb_old, str(gb_path), str(REPO_DIR))
        self.assertFalse(passed, "Old wrong Glen Burnie must fail verification gate")
        self.assertTrue(any("reported_value '0.07'" in f for f in fails), f"Must fail on reported_value: {fails}")

    # 12. Measurement numbering gate fails when source_page exceeds total pages
    def test_measurement_numbering_gate_exceeds_pages(self):
        import yaml
        c_path = REPO_DIR / "water" / "measurements" / "aa_crownsville" / "lead_tap_2025.md"
        with open(c_path, "r", encoding="utf-8") as f:
            fm = yaml.safe_load(f.read().split("---")[1])
        fm["determination"] = dict(fm["determination"])
        fm["determination"]["source_page"] = "Page 99"
        passed, msg, res, fails = check_measurement_record(fm, str(c_path), str(REPO_DIR))
        self.assertFalse(passed, "Exceeding page count must fail")
        self.assertTrue(any("exceeds PDF page count" in f for f in fails), f"Must fail with page count: {fails}")

    # 13. Sampling-year footnote gate fails when reporting_period mismatches footnote
    def test_sampling_year_footnote_mismatch_fails(self):
        import yaml
        gb_path = REPO_DIR / "water" / "measurements" / "aa_glen_burnie" / "copper_tap_2025.md"
        with open(gb_path, "r", encoding="utf-8") as f:
            fm = yaml.safe_load(f.read().split("---")[1])
        # Set reporting_period to 2023 when footnote 6 says "Sampled in 2024."
        fm["reporting_period"] = "2023"
        passed, msg, res, fails = check_measurement_record(fm, str(gb_path), str(REPO_DIR))
        self.assertFalse(passed, "Mismatched footnote year must fail")
        self.assertTrue(any("Footnote 6: Sampled in 2024" in f for f in fails), f"Must fail naming footnote text: {fails}")

    # 14. sites_above_al.quote not on cited page fails
    def test_sites_above_al_quote_not_on_page_fails(self):
        import yaml
        c_path = REPO_DIR / "water" / "measurements" / "aa_crownsville" / "lead_tap_2025.md"
        with open(c_path, "r", encoding="utf-8") as f:
            fm = yaml.safe_load(f.read().split("---")[1])
        fm["sites_above_al"] = dict(fm["sites_above_al"])
        fm["sites_above_al"]["quote"] = "99/10"
        passed, msg, res, fails = check_measurement_record(fm, str(c_path), str(REPO_DIR))
        self.assertFalse(passed, "Fake sites_above_al.quote must fail verification gate")
        self.assertTrue(any("sites_above_al.quote '99/10'" in f for f in fails), f"Must fail naming quote: {fails}")

    # 15. sites_above_al glyph flag vs numerator consistency fails in both directions
    def test_sites_above_al_numerator_glyph_consistency(self):
        import yaml
        # Direction 1: numerator is 0 but glyph: true -> must fail
        gb_path = REPO_DIR / "water" / "measurements" / "aa_glen_burnie" / "copper_tap_2025.md"
        with open(gb_path, "r", encoding="utf-8") as f:
            fm_gb = yaml.safe_load(f.read().split("---")[1])
        fm_gb["sites_above_al"] = dict(fm_gb["sites_above_al"])
        fm_gb["sites_above_al"]["glyph"] = True  # quote is "0/5"
        passed, msg, res, fails = check_measurement_record(fm_gb, str(gb_path), str(REPO_DIR))
        self.assertFalse(passed, "glyph: true with numerator 0 must fail")
        self.assertTrue(any("glyph: true but numerator is 0" in f for f in fails), f"Must fail with numerator message: {fails}")

        # Direction 2: numerator is >0 but glyph: false -> must fail
        cr_path = REPO_DIR / "water" / "measurements" / "aa_crownsville" / "lead_tap_2025.md"
        with open(cr_path, "r", encoding="utf-8") as f:
            fm_cr = yaml.safe_load(f.read().split("---")[1])
        fm_cr["sites_above_al"] = dict(fm_cr["sites_above_al"])
        fm_cr["sites_above_al"]["glyph"] = False  # quote is "1/10"
        passed, msg, res, fails = check_measurement_record(fm_cr, str(cr_path), str(REPO_DIR))
        self.assertFalse(passed, "glyph: false but numerator is > 0 must fail")
        self.assertTrue(any("glyph: false but numerator is > 0" in f for f in fails), f"Must fail with numerator message: {fails}")


    # Blank PDF without text layer yields 'source text not extractable'
    def test_unextractable_blank_pdf_yields_source_text_not_extractable(self):
        import tempfile
        import pypdf

        # Create a 1-page blank PDF fixture using pypdf.PdfWriter().add_blank_page(width=612, height=792)
        writer = pypdf.PdfWriter()
        writer.add_blank_page(width=612, height=792)
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
            temp_pdf_path = tf.name
            writer.write(tf)

        try:
            pages = extract_text_from_file(temp_pdf_path)
            self.assertEqual(len(pages), 1, "Blank PDF must have 1 page")
            tot_c, p_c, cpp, is_e = measure_source_text(pages)
            self.assertEqual(tot_c, 0, "Blank PDF fixture must yield 0 extractable characters")
            self.assertEqual(p_c, 1, "Blank PDF fixture must have page count 1")
            self.assertEqual(cpp, 0.0, "Blank PDF fixture must have 0.0 chars per page")
            self.assertFalse(is_e, "Blank PDF fixture must be marked unextractable (< 200 chars or < 50 cpp)")

            # In check_field_accuracy, fields evaluated against unextractable sources return 'source text not extractable'
            field_value = "2026-01-01"
            match = find_needle_in_pages(pages, [field_value])
            self.assertIsNone(match)
            res_status = "source text not extractable" if not is_e else "not found"
            self.assertEqual(res_status, "source text not extractable")
        finally:
            if os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)

    # Text fixture yields 'found' for present string and 'not found' for absent string
    def test_extractable_text_fixture_yields_found_and_not_found(self):
        source_file = self.pdf_cache / "462401af5834c183176774eedc5f415d6ff4c790f8d9495f26ac523b069bdf63.pdf"
        pages = extract_text_from_file(str(source_file))
        tot_c, p_c, cpp, is_e = measure_source_text(pages)
        self.assertTrue(is_e, "Text PDF fixture must be extractable")
        self.assertGreaterEqual(tot_c, MIN_TOTAL_CHARS)
        self.assertGreaterEqual(cpp, MIN_CHARS_PER_PAGE)

        # Present string -> found
        m_found = find_needle_in_pages(pages, ["ZTA 23-09"])
        self.assertIsNotNone(m_found, "Present string must be found in extractable source")
        status_found = "found" if m_found else ("source text not extractable" if not is_e else "not found")
        self.assertEqual(status_found, "found")

        # Absent string -> not found
        m_not = find_needle_in_pages(pages, ["Nonexistent Phrase Absent 99999"])
        self.assertIsNone(m_not, "Absent string must not be found in extractable source")
        status_not = "found" if m_not else ("source text not extractable" if not is_e else "not found")
        self.assertEqual(status_not, "not found")

if __name__ == "__main__":
    unittest.main()
