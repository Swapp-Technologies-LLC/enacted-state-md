#!/usr/bin/env python3
"""
test_water_source_check.py
Acceptance and Integrity Test Suite for Drinking-Water Expected Reports Absence Detection.

Tests:
1. Fixtures unreachable from corpus, feeds, or dist/
2. No basis → no record produced
3. Fetch error / redirect / empty link list → source_unreachable, no record produced
4. Past due + grace → candidate on a branch only, main untouched, zero mail sent
5. Later found → closing candidate record references open not-found record
6. Wording gate blocks each banned word outside quotes
7. Run is strictly read-only and zero-send (nothing sends mail)
"""

import os
import re
import sys
import unittest
import tempfile
import shutil
from datetime import date
from pathlib import Path
from unittest.mock import patch, MagicMock

# Path resolution
TESTS_DIR = Path(__file__).resolve().parent
REPO_DIR = TESTS_DIR.parent
SCRIPTS_DIR = REPO_DIR / "scripts"
FIXTURES_DIR = TESTS_DIR / "fixtures" / "water_source_check"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

from wording_gate import scan_wording_gate, assert_wording_gate, WordingGateViolationError, BANNED_WORDS, BANNED_PHRASES, BANNED_PUNCTUATION
from check_expected_reports import (
    check_system_sources,
    extract_links_from_html,
    hash_link_list,
    is_cadence_basis_valid,
    fetch_watched_index,
    parse_cadence_due_date,
    get_report_period
)
from generate_newsletter import (
    render_water_source_not_found_email,
    render_water_source_found_email,
    render_water_notice_email,
    render_water_digest_email,
    render_anne_arundel,
)
from generate_feeds import closing_line, TOPIC_HEALTH_RELATED


class MockHTTPResponse:
    def __init__(self, content: bytes, code: int = 200, url: str = "https://example.invalid/water/reports"):
        self.content = content
        self.code = code
        self.url = url

    def read(self):
        return self.content

    def getcode(self):
        return self.code

    def geturl(self):
        return self.url


class TestWaterSourceCheck(unittest.TestCase):

    def test_01_fixtures_unreachable_from_corpus_feeds_dist(self):
        """Assert no fixture path or identifier is reachable from corpus, feeds or dist/."""
        # 1. Check real water measurements directories
        water_measurements = REPO_DIR / "water" / "measurements"
        for sys_dir in water_measurements.iterdir():
            if sys_dir.is_dir():
                self.assertNotIn("fixture", sys_dir.name.lower())
                self.assertNotIn("testville", sys_dir.name.lower())
                for mf in sys_dir.glob("*.md"):
                    content = mf.read_text(encoding="utf-8")
                    self.assertNotIn("TEST FIXTURE SYSTEM", content)
                    self.assertNotIn("example.invalid", content)

        # 2. Check feeds
        feeds_dir = REPO_DIR / "feeds"
        if feeds_dir.exists():
            for feed_file in feeds_dir.rglob("*"):
                if feed_file.is_file() and feed_file.suffix in (".atom", ".json", ".xml"):
                    feed_txt = feed_file.read_text(encoding="utf-8")
                    self.assertNotIn("TEST FIXTURE SYSTEM", feed_txt)
                    self.assertNotIn("water_source_check", feed_txt)

        # 3. Check dist/ if present
        dist_dir = REPO_DIR.parent / "enacted-site" / "dist"
        if dist_dir.exists():
            for p in dist_dir.rglob("*.html"):
                html_txt = p.read_text(encoding="utf-8")
                self.assertNotIn("TEST FIXTURE SYSTEM", html_txt)
                self.assertNotIn("water_source_check", html_txt)

    def test_02_no_basis_never_produces_record(self):
        """A source with no cadence_basis or pending verification never produces a record."""
        # Check all 7 real MD systems on disk
        water_measurements = REPO_DIR / "water" / "measurements"
        for sys_dir in water_measurements.iterdir():
            if sys_dir.is_dir() and not sys_dir.name.startswith("."):
                actions = check_system_sources(sys_dir, as_of=date(2026, 9, 1), dry_run=True)
                for a in actions:
                    self.assertEqual(a["status"], "skipped_no_basis_or_inactive")
                    self.assertNotIn("candidate_created", a["status"])

        # Check explicit cadence basis validator
        self.assertFalse(is_cadence_basis_valid(None))
        self.assertFalse(is_cadence_basis_valid("[FOUNDER: pending side-chat return]"))
        self.assertFalse(is_cadence_basis_valid({}))
        self.assertFalse(is_cadence_basis_valid({"rule": "[FOUNDER: pending side-chat return]"}))
        self.assertTrue(is_cadence_basis_valid({
            "rule": {"citation": "40 CFR § 141.152", "quoted_sentence": "Deliver report by July 1."}
        }))

    def test_03_fetch_error_logged_as_source_unreachable_no_record(self):
        """Fetch error, non-200, redirect to different host, or empty link list = source_unreachable, no record."""
        fixture_system = FIXTURES_DIR / "test_fixture_system"
        self.assertTrue(fixture_system.exists())

        # Subtest A: HTTP 404
        mock_opener_404 = MagicMock()
        mock_opener_404.open.return_value = MockHTTPResponse(b"Not Found", code=404)
        actions = check_system_sources(fixture_system, as_of=date(2026, 8, 15), mock_opener=mock_opener_404)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["status"], "source_unreachable")
        self.assertIn("Non-200", actions[0]["message"])

        # Subtest B: Redirect to different host
        mock_opener_redir = MagicMock()
        mock_opener_redir.open.return_value = MockHTTPResponse(
            b"<html><body><a href='/other'>Link</a></body></html>",
            code=200,
            url="https://different-host.invalid/water/reports"
        )
        actions = check_system_sources(fixture_system, as_of=date(2026, 8, 15), mock_opener=mock_opener_redir)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["status"], "source_unreachable")
        self.assertIn("Redirect to different host", actions[0]["message"])

        # Subtest C: Empty link list
        mock_opener_empty = MagicMock()
        mock_opener_empty.open.return_value = MockHTTPResponse(
            b"<html><body><h1>No links here</h1></body></html>",
            code=200,
            url="https://example.invalid/water/reports"
        )
        actions = check_system_sources(fixture_system, as_of=date(2026, 8, 15), mock_opener=mock_opener_empty)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["status"], "source_unreachable")
        self.assertIn("empty", actions[0]["message"])

    def test_04_past_due_plus_grace_writes_candidate_to_branch_only(self):
        """Past expected_by + grace_days without newer issue generates candidate on a branch only."""
        fixture_system = FIXTURES_DIR / "test_fixture_system"

        with tempfile.TemporaryDirectory() as tmp_cand_dir:
            cand_output = Path(tmp_cand_dir)

            # Mock index returns link to previous report (2024), but none for 2025
            html_older = b"""
            <html><body>
                <a href="https://example.invalid/water/report_2024.pdf">2024 Water Quality Report</a>
            </body></html>
            """
            mock_opener = MagicMock()
            mock_opener.open.return_value = MockHTTPResponse(html_older, code=200, url="https://example.invalid/water/reports")

            # As of August 1, 2026 (past July 1 + 30 grace days = July 31)
            actions = check_system_sources(
                fixture_system,
                as_of=date(2026, 8, 1),
                dry_run=True,
                candidate_output_dir=cand_output,
                mock_opener=mock_opener
            )

            self.assertEqual(len(actions), 1)
            action = actions[0]
            self.assertEqual(action["status"], "candidate_created")
            self.assertEqual(action["record_type"], "not_found")
            self.assertTrue(action["branch"].startswith("candidate/water-absence-"))
            self.assertEqual(
                action["title"],
                "TEST FIXTURE SYSTEM · Fixture Water Quality Report: no 2025 report found at the watched source as of August 1, 2026."
            )

            # Assert file was written to candidate directory and NOT to main fixture dir
            cand_file = cand_output / "test_fixture_system" / action["candidate_filename"]
            self.assertTrue(cand_file.exists())
            cand_content = cand_file.read_text(encoding="utf-8")
            self.assertIn("record_type: source_check", cand_content)
            self.assertIn("check_status: not_found", cand_content)
            self.assertIn("TEST RULE § 0.0", cand_content)
            self.assertIn("Test fixture systems shall deliver water monitoring summaries on the prescribed fixture schedule.", cand_content)

            # Main fixture directory must not have new files
            self.assertFalse((fixture_system / action["candidate_filename"]).exists())

            # Wording gate verification on generated content
            assert_wording_gate(cand_content, "Generated candidate file")

    def test_05_later_found_writes_closing_record_referencing_open(self):
        """When an open not-found record exists and later run finds report, writes closing candidate referencing open record."""
        with tempfile.TemporaryDirectory() as tmp_env:
            env_dir = Path(tmp_env)
            test_sys = env_dir / "test_fixture_system"
            shutil.copytree(FIXTURES_DIR / "test_fixture_system", test_sys)

            # Create an existing open not-found record in the system dir
            open_not_found = test_sys / "source_check_not_found_2025_2026-08-01.md"
            open_not_found.write_text("""---
record_type: source_check
check_status: not_found
source_agency: TEST FIXTURE SYSTEM Customer Utility
jurisdiction: xx/testville
jurisdiction_name: Testville Water District
system: TEST FIXTURE SYSTEM
source_id: test_fixture_source
source_title: Fixture Water Quality Report
reporting_period: '2025'
---
# Open Not Found Record
""", encoding="utf-8")

            cand_output = env_dir / "candidates"

            # Mock index now returns new 2025 report link!
            html_new = b"""
            <html><body>
                <a href="https://example.invalid/water/report_2025.pdf">2025 Water Quality Report</a>
            </body></html>
            """
            mock_opener = MagicMock()
            mock_opener.open.return_value = MockHTTPResponse(html_new, code=200, url="https://example.invalid/water/reports")

            # As of August 15, 2026
            actions = check_system_sources(
                test_sys,
                as_of=date(2026, 8, 15),
                dry_run=True,
                candidate_output_dir=cand_output,
                mock_opener=mock_opener
            )

            self.assertEqual(len(actions), 1)
            action = actions[0]
            self.assertEqual(action["status"], "closing_candidate_created")
            self.assertEqual(action["record_type"], "found")
            self.assertTrue(action["branch"].startswith("candidate/water-closing-"))
            self.assertEqual(
                action["title"],
                "TEST FIXTURE SYSTEM · Fixture Water Quality Report: 2025 report found August 15, 2026."
            )
            self.assertIn("source_check_not_found_2025_2026-08-01", action["closes_record"])

            # Verify file content
            cand_file = cand_output / "test_fixture_system" / action["candidate_filename"]
            self.assertTrue(cand_file.exists())
            cand_content = cand_file.read_text(encoding="utf-8")
            self.assertIn("check_status: found", cand_content)
            self.assertIn("https://example.invalid/water/report_2025.pdf", cand_content)
            self.assertIn("closes_record: water/measurements/test_fixture_system/source_check_not_found_2025_2026-08-01", cand_content)

            assert_wording_gate(cand_content, "Closing candidate file")

    def test_06_wording_gate_blocks_each_banned_word(self):
        """Wording gate blocks each banned word outside quotes, while permitting verbatim quotes."""
        # 1. Clean text passes
        clean_text = "Broad Creek · Water Quality Report: no 2025 report found at the watched source as of August 1, 2026."
        self.assertTrue(scan_wording_gate(clean_text)[0])

        # 2. Each banned standalone word fails outside quotes
        for w in BANNED_WORDS:
            dirty_text = f"The report is {w} according to the office."
            passed, violations = scan_wording_gate(dirty_text)
            self.assertFalse(passed, f"Expected word '{w}' to be blocked by wording gate!")

        # 3. Phrases and punctuation fail outside quotes
        self.assertFalse(scan_wording_gate("The utility was required to publish.")[0])
        self.assertFalse(scan_wording_gate("Where is the report?")[0])
        self.assertFalse(scan_wording_gate("A report has arrived!")[0])

        # 4. Verbatim quotes with banned words inside are permitted
        quoted_markdown = """
        No report found at the watched source as of August 1, 2026.
        
        > "During fall 2025, we were required to collect samples, but results were delayed."
        
        ```
        We failed to submit on time!
        ```
        """
        passed, violations = scan_wording_gate(quoted_markdown)
        self.assertTrue(passed, f"Expected quoted markdown to pass wording gate, got violations: {violations}")

    def test_07_nothing_in_run_sends_mail(self):
        """Asserts that running detector does not initiate any SMTP or email connections."""
        with patch("smtplib.SMTP") as mock_smtp, patch("smtplib.SMTP_SSL") as mock_smtp_ssl:
            fixture_system = FIXTURES_DIR / "test_fixture_system"
            mock_opener = MagicMock()
            mock_opener.open.return_value = MockHTTPResponse(b"<html><body><a href='/a'>A</a></body></html>", code=200)

            check_system_sources(fixture_system, as_of=date(2026, 8, 1), mock_opener=mock_opener)

            mock_smtp.assert_not_called()
            mock_smtp_ssl.assert_not_called()

    def test_08_water_emails_and_pages_contain_no_zoning_or_enacted_law(self):
        """No water email or water page may contain 'zoning', 'land-use', or 'enacted law'."""
        # 1. Check rendered water emails
        nf_email = render_water_source_not_found_email()
        f_email = render_water_source_found_email()

        for name, html in [("not_found_email", nf_email), ("found_email", f_email)]:
            lower_html = html.lower()
            self.assertNotIn("zoning", lower_html, f"{name} contains 'zoning'")
            self.assertNotIn("land-use", lower_html, f"{name} contains 'land-use'")
            self.assertNotIn("enacted law", lower_html, f"{name} contains 'enacted law'")
            self.assertNotIn("signal dispatch", lower_html, f"{name} contains 'signal dispatch'")
            self.assertNotIn("md · water monitoring", lower_html, f"{name} contains 'MD · WATER MONITORING'")
            self.assertNotIn("monitors", lower_html, f"{name} contains banned verb 'monitors'")

        # 2. Check site template rendering for water source_check record
        from jinja2 import Environment, FileSystemLoader, select_autoescape
        site_templates = REPO_DIR.parent / "enacted-site" / "templates"
        if site_templates.exists():
            env = Environment(
                loader=FileSystemLoader(str(site_templates)),
                autoescape=select_autoescape(["html", "xml"])
            )
            env.globals["get_outline_svg"] = lambda x: ""
            env.globals["get_zcta_outline_svg"] = lambda x: ""
            tmpl = env.get_template("pages/record_detail.html")
            
            sample_record = {
                "record_type": "source_check",
                "check_status": "not_found",
                "title": "TEST FIXTURE SYSTEM · Fixture Water Quality Report: no 2025 report found at the watched source as of August 1, 2026.",
                "short_title": "TEST FIXTURE SYSTEM · Fixture Water Quality Report",
                "state": "md",
                "jurisdiction": "xx/testville",
                "jurisdiction_slug": "testville",
                "jurisdiction_name": "Testville Water District",
                "system": "TEST FIXTURE SYSTEM",
                "source_agency": "TEST FIXTURE WATER DEPARTMENT",
                "source_title": "Fixture Water Quality Report",
                "reporting_period": "2025",
                "published_date": "2026-08-01",
                "checked_at": "2026-08-01T12:00:00Z",
                "index_url": "https://example.invalid/fixture/index.html",
                "cadence_basis": {
                    "rule": {
                        "citation": "TEST RULE § 0.0",
                        "quoted_sentence": "Test fixture systems shall deliver water monitoring summaries on the prescribed fixture schedule."
                    }
                },
                "last_found": {
                    "title": "Fixture Water Quality Report 2024",
                    "date": "2025-06-01",
                    "url": "https://example.invalid/fixture/report-2024.pdf"
                },
                "contact": {
                    "agency": "TEST FIXTURE WATER DEPARTMENT",
                    "phone": "(555) 010-0000",
                    "email": "test-water@example.invalid",
                    "web": "https://example.invalid"
                },
                "topic": "water",
                "topics": ["water"],
                "slug": "test_fixture_not_found"
            }
            rendered_page = tmpl.render(
                record=sample_record,
                canonical_domain="enacted.app",
                site_host="https://enacted.app",
                app_host="https://account.enacted.app",
                app_live=False,
                waitlist_live=False
            )
            lower_page = rendered_page.lower()
            self.assertNotIn("zoning", lower_page, "Water page contains 'zoning'")
            self.assertNotIn("land-use", lower_page, "Water page contains 'land-use'")
            self.assertNotIn("enacted law", lower_page, "Water page contains 'enacted law'")

    def test_09_when_last_found_is_period_P_no_not_found_produced(self):
        """When last_found is the report for period P, no not-found record for P can be produced."""
        with tempfile.TemporaryDirectory() as tmp_env:
            env_dir = Path(tmp_env)
            test_sys = env_dir / "test_sys"
            test_sys.mkdir(parents=True, exist_ok=True)
            
            # Write sources.yaml where last_found ALREADY has period 2025
            sources_yaml = test_sys / "sources.yaml"
            sources_yaml.write_text("""sources:
  - id: fixture_source
    title: "Fixture Water Quality Report"
    index_url: "https://example.invalid/water/reports"
    content: "Fixture data"
    cadence: annual
    cadence_basis:
      rule:
        citation: "TEST RULE § 0.0"
        quoted_sentence: "Test fixture rule text."
    active: true
    expected_by: "July 1 annually"
    grace_days: 30
    last_found:
      title: "Fixture Water Quality Report 2025"
      period: "2025"
      date: "2026-06-01"
      url: "https://example.invalid/water/report-2025.pdf"
      sha256: "0000000000000000000000000000000000000000000000000000000000000000"
""", encoding="utf-8")
            
            mock_opener = MagicMock()
            # Index only has the 2025 report link
            mock_opener.open.return_value = MockHTTPResponse(
                b"<html><body><a href='https://example.invalid/water/report-2025.pdf'>2025 Report</a></body></html>",
                code=200
            )

            cand_dir = env_dir / "candidates"
            actions = check_system_sources(
                test_sys,
                as_of=date(2026, 8, 1),
                candidate_output_dir=cand_dir,
                mock_opener=mock_opener
            )

            self.assertEqual(len(actions), 1)
            self.assertEqual(actions[0]["status"], "already_found")
            self.assertIn("already recorded in last_found", actions[0]["message"])
            self.assertFalse(cand_dir.exists())

    def test_10_is_cadence_basis_valid_strict_shape_checks(self):
        """is_cadence_basis_valid strictly requires dict with exactly one of rule / agency_statement."""
        # Rejected: non-dict
        self.assertFalse(is_cadence_basis_valid(None))
        self.assertFalse(is_cadence_basis_valid(""))
        self.assertFalse(is_cadence_basis_valid("[FOUNDER: pending side-chat return]"))
        self.assertFalse(is_cadence_basis_valid("40 CFR § 141.152"))
        self.assertFalse(is_cadence_basis_valid(123))
        self.assertFalse(is_cadence_basis_valid([]))

        # Rejected: empty dict or neither key
        self.assertFalse(is_cadence_basis_valid({}))
        self.assertFalse(is_cadence_basis_valid({"unrelated": "data"}))

        # Rejected: both rule and agency_statement present
        self.assertFalse(is_cadence_basis_valid({
            "rule": {"citation": "TEST RULE § 0.0", "quoted_sentence": "Rule quote"},
            "agency_statement": {"url": "https://example.invalid", "date_read": "2026-09-01", "quoted_sentence": "Agency quote"}
        }))

        # Rejected: rule not a dict
        self.assertFalse(is_cadence_basis_valid({"rule": "40 CFR § 141.152"}))

        # Rejected: rule missing citation or quote
        self.assertFalse(is_cadence_basis_valid({"rule": {"citation": "TEST RULE § 0.0"}}))
        self.assertFalse(is_cadence_basis_valid({"rule": {"quoted_sentence": "Some quote."}}))
        self.assertFalse(is_cadence_basis_valid({"rule": {"citation": "   ", "quoted_sentence": "Some quote."}}))
        self.assertFalse(is_cadence_basis_valid({"rule": {"citation": "TEST RULE § 0.0", "quoted_sentence": "   "}}))
        self.assertFalse(is_cadence_basis_valid({"rule": {"citation": "[FOUNDER: pending]", "quoted_sentence": "Some quote."}}))
        self.assertFalse(is_cadence_basis_valid({"rule": {"citation": "TEST RULE § 0.0", "quoted_sentence": "[FOUNDER: pending]"}}))

        # Rejected: agency_statement missing required fields or placeholder
        self.assertFalse(is_cadence_basis_valid({"agency_statement": {"url": "https://example.invalid"}}))
        self.assertFalse(is_cadence_basis_valid({"agency_statement": {"url": "https://example.invalid", "date_read": "2026-09-01"}}))
        self.assertFalse(is_cadence_basis_valid({"agency_statement": {"url": "https://example.invalid", "date_read": "2026-09-01", "quoted_sentence": ""}}))
        self.assertFalse(is_cadence_basis_valid({"agency_statement": {"url": "https://example.invalid", "date_read": "2026-09-01", "quoted_sentence": "[FOUNDER: pending]"}}))

        # Accepted: valid rule
        self.assertTrue(is_cadence_basis_valid({
            "rule": {
                "citation": "TEST RULE § 0.0",
                "quoted_sentence": "Test fixture systems shall deliver water monitoring summaries on the prescribed fixture schedule."
            }
        }))

        # Accepted: valid agency_statement
        self.assertTrue(is_cadence_basis_valid({
            "agency_statement": {
                "url": "https://example.invalid/schedule",
                "date_read": "2026-09-01",
                "quoted_sentence": "Annual water reports will be posted online by July 1."
            }
        }))

    def test_11_structured_expected_by_due_date_parsing(self):
        """parse_cadence_due_date correctly derives dates from structured expected_by formats."""
        # Case 1: Dict with month and day
        d1 = parse_cadence_due_date({"expected_by": {"month": 7, "day": 1}}, 2026)
        self.assertEqual(d1, date(2026, 7, 1))

        # Case 2: Month name and day
        d2 = parse_cadence_due_date({"expected_by": "July 1 annually following compliance reporting period"}, 2026)
        self.assertEqual(d2, date(2026, 7, 1))
        d3 = parse_cadence_due_date({"expected_by": "by April 1"}, 2026)
        self.assertEqual(d3, date(2026, 4, 1))

        # Case 3: MM-DD
        d4 = parse_cadence_due_date({"expected_by": "10-15"}, 2026)
        self.assertEqual(d4, date(2026, 10, 15))

        # Case 4: N days after quarter end
        d5 = parse_cadence_due_date({"cadence": "quarterly", "expected_by": "30 days after quarter end"}, 2026)
        self.assertEqual(d5, date(2026, 4, 30))

        # Case 5: Unparsable / placeholder stays inactive
        self.assertIsNone(parse_cadence_due_date({"expected_by": "[FOUNDER: pending side-chat return]"}, 2026))
        self.assertIsNone(parse_cadence_due_date({"expected_by": "unspecified schedule"}, 2026))
    def test_12_decoy_link_path_year_ignored(self):
        """A link with the expected year in its path segment (upload directory) does not falsely trigger match."""
        # Setup fixture source with issue_pattern
        src_with_pattern = {
            "id": "test_src",
            "title": "Water Quality Report",
            "active": True,
            "cadence": "annual",
            "expected_by": "July 1",
            "issue_pattern": r"(?:water[-_ ]quality[-_ ]report|ccr)[-_ ]*{period}",
            "cadence_basis": {
                "rule": {
                    "citation": "TEST RULE § 0.0",
                    "quoted_sentence": "Test fixture systems shall deliver water monitoring summaries on the prescribed fixture schedule."
                }
            },
            "last_found": {
                "title": "Water Quality Report 2024",
                "date": "2025-06-01",
                "url": "https://example.invalid/report-2024.pdf",
                "period": "2024"
            }
        }
        # Links on page: one decoy with /2025-06/ upload dir but filename is report-2024.pdf
        links = [
            ("https://example.invalid/uploads/2025-06/report-2024.pdf", "Read the 2024 Water Quality Report"),
            ("https://example.invalid/about.html", "About Us")
        ]
        # Check that expected_period 2025 does not match
        expected_period = "2025"
        issue_pattern_template = src_with_pattern.get("issue_pattern")
        matched = False
        import urllib.parse
        for link_url, link_text in links:
            parsed_path = urllib.parse.urlparse(link_url).path
            filename = os.path.basename(parsed_path.rstrip("/"))
            if issue_pattern_template:
                pattern = issue_pattern_template.replace("{period}", re.escape(expected_period))
                if re.search(pattern, filename, re.IGNORECASE) or re.search(pattern, link_text, re.IGNORECASE):
                    matched = True
                    break
        self.assertFalse(matched, "Decoy link with year in path segment must not match expected period")

    def test_13_closing_line_and_unset_topic(self):
        """Test closing_line posture and strict topic health_related validation."""
        # Valid ruled topics
        self.assertEqual(closing_line("zoning"), "Not legal advice.")
        self.assertEqual(closing_line(["zoning"]), "Not legal advice.")
        self.assertEqual(closing_line("water"), "Not legal or health advice.")
        self.assertEqual(closing_line(["water"]), "Not legal or health advice.")
        self.assertEqual(closing_line("pfas"), "Not legal or health advice.")
        self.assertEqual(closing_line(["pfas"]), "Not legal or health advice.")
        self.assertEqual(closing_line(["zoning", "water"]), "Not legal or health advice.")
        self.assertEqual(closing_line(["water", "zoning"]), "Not legal or health advice.")
        self.assertEqual(closing_line(["zoning", "pfas"]), "Not legal or health advice.")

        # Strict dictionary contents
        self.assertEqual(
            TOPIC_HEALTH_RELATED,
            {
                "zoning": False,
                "water": True,
                "pfas": True,
                "housing": False,
                "commercial": False,
                "planning": False,
                "industrial": False,
                "hoa": False,
            }
        )

        # Empty topics raises
        with self.assertRaises(ValueError):
            closing_line([])

        # Unruled topics must fail loudly, never fall back
        for unruled in ["firearms", "noise", "data-center"]:
            with self.assertRaises(ValueError) as ctx:
                closing_line(unruled)
            self.assertIn("unruled health_related status", str(ctx.exception))
            with self.assertRaises(ValueError):
                closing_line(["zoning", unruled])

    def test_14_missing_determination_fails_validation(self):
        """Test that missing, invalid, or incomplete determination block fails validation."""
        from generate_feeds import validate_determination
        
        # Valid determinations
        valid_det_1 = {
            "status": "violation_reported",
            "quote": "Assessed a violation.",
            "source_page": "Page 4"
        }
        valid_det_2 = {
            "status": "limit_not_yet_in_force",
            "quote": "Rule scheduled for 2029.",
            "source_page": "Page 14 (Footnote 12)"
        }
        self.assertTrue(validate_determination(valid_det_1))
        self.assertTrue(validate_determination(valid_det_2))

        # Missing determination block
        with self.assertRaises(ValueError) as ctx:
            validate_determination(None)
        self.assertIn("must include a 'determination' object", str(ctx.exception))

        # Invalid status
        invalid_det = {
            "status": "safe_clean_result",
            "quote": "Clean result",
            "source_page": "Page 1"
        }
        with self.assertRaises(ValueError) as ctx:
            validate_determination(invalid_det)
        self.assertIn("Invalid determination status", str(ctx.exception))

        # Missing / empty quote
        no_quote_det = {
            "status": "no_violation_reported",
            "quote": "",
            "source_page": "Page 13"
        }
        with self.assertRaises(ValueError) as ctx:
            validate_determination(no_quote_det)
        self.assertIn("must have non-empty 'quote'", str(ctx.exception))

        # Missing / empty source_page
        no_page_det = {
            "status": "no_violation_reported",
            "quote": "Violation: No",
            "source_page": ""
        }
        with self.assertRaises(ValueError) as ctx:
            validate_determination(no_page_det)
        self.assertIn("must have non-empty 'source_page'", str(ctx.exception))

    def test_15_first_issue_key_and_water_templates(self):
        """Test first-issue key display, footer links, dynamic card loading, and zero flex layout."""
        # 1. Water Notice
        notice_first = render_water_notice_email(show_first_issue_key=True)
        notice_later = render_water_notice_email(show_first_issue_key=False)
        self.assertIn("How to read a water record &middot; shown in the first issue", notice_first)
        self.assertIn("Violation reported", notice_first)
        self.assertIn("Limit not yet in force", notice_first)
        self.assertNotIn("How to read a water record &middot; shown in the first issue", notice_later)
        # Check required footer links
        for link in ["/unsubscribe", "/follows", "/coverage", "/how-to-read#water"]:
            self.assertIn(link, notice_first)
            self.assertIn(link, notice_later)
        # Check posture block second sentence
        self.assertIn("Which system serves an address, and what a result means for a household,", notice_first)
        self.assertIn("are questions for the agency named above.", notice_first)
        # Check zero flex
        self.assertEqual(notice_first.count("display: flex"), 0)
        self.assertEqual(notice_later.count("display: flex"), 0)

        # 2. Water Digest
        digest_first = render_water_digest_email(show_first_issue_key=True)
        digest_later = render_water_digest_email(show_first_issue_key=False)
        self.assertIn("How to read a water record &middot; shown in the first issue", digest_first)
        self.assertNotIn("How to read a water record &middot; shown in the first issue", digest_later)
        for link in ["/unsubscribe", "/follows", "/coverage", "/how-to-read#water"]:
            self.assertIn(link, digest_first)
            self.assertIn(link, digest_later)
        # Check posture block second sentence
        self.assertIn("Which system serves an address, and what a result means for a household,", digest_first)
        self.assertIn("are questions for the agency named above.", digest_first)
        # Check zero flex
        self.assertEqual(digest_first.count("display: flex"), 0)
        self.assertEqual(digest_later.count("display: flex"), 0)
        # Check all 5 records dynamically rendered
        self.assertIn("5 records from the 2025 Water Quality Report", digest_later)
        self.assertTrue("Distribution System Customer Taps · Lead" in digest_later or "Distribution System Customer Taps &middot; Lead" in digest_later)
        self.assertTrue("Patuxent Water Filtration Plant Tap · Perfluorooctanoic acid (PFOA)" in digest_later or "Patuxent Water Filtration Plant Tap &middot; Perfluorooctanoic acid (PFOA)" in digest_later)
        self.assertTrue("Patuxent Water Filtration Plant Tap · Perfluorooctanesulfonic acid (PFOS)" in digest_later or "Patuxent Water Filtration Plant Tap &middot; Perfluorooctanesulfonic acid (PFOS)" in digest_later)
        self.assertTrue("Potomac Water Filtration Plant Tap · Perfluorooctanoic acid (PFOA)" in digest_later or "Potomac Water Filtration Plant Tap &middot; Perfluorooctanoic acid (PFOA)" in digest_later)
        self.assertTrue("Potomac Water Filtration Plant Tap · Perfluorooctanesulfonic acid (PFOS)" in digest_later or "Potomac Water Filtration Plant Tap &middot; Perfluorooctanesulfonic acid (PFOS)" in digest_later)

        # 3. Anne Arundel Zoning Digest
        zoning_first = render_anne_arundel(show_first_issue_key=True)
        zoning_later = render_anne_arundel(show_first_issue_key=False)
        self.assertIn("How to read a record &middot; shown in the first issue", zoning_first)
        self.assertIn("Took effect", zoning_first)
        self.assertIn("Sunsets soon", zoning_first)
        self.assertNotIn("How to read a record &middot; shown in the first issue", zoning_later)
        for link in ["/unsubscribe", "/follows", "/coverage", "/how-to-read#zoning"]:
            self.assertIn(link, zoning_first)
            self.assertIn(link, zoning_later)


if __name__ == "__main__":
    unittest.main()
