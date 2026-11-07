#!/usr/bin/env python3
"""
test_ingest_slice_i1.py
Acceptance and Integrity Test Suite for Ingest Slice I1 (Deterministic Workflows & Water Checks).
Swapp Technologies LLC

Tests:
1. Workflows parse as valid YAML with distinct concurrency groups.
2. Workflow hygiene: zero [FOUNDER:, zero PATs (ENACTED_BOT_TOKEN), zero personal emails,
   zero firearms strings, crons commented out with disabled note, ubuntu-24.04 runner,
   actions/create-github-app-token using SWAPP_BOT_CLIENT_ID & SWAPP_BOT_PRIVATE_KEY.
3. Robots.txt: a path disallowed by robots.txt is skipped and logged, never fetched.
4. Rate limiting: enforces >= 5 s spacing between requests to the same host.
5. Discovery: An index fixture lists the known report plus a newer-year file ->
   newer one is cached, manifest note is written, covered for both issue_pattern and year rule.
6. Same-URL changed bytes -> cached and noted in manifest.
7. Absence: Past due + grace, index fetched OK, no current-cycle link -> exactly one absence candidate.
8. Outages: Past due + grace, index unreachable -> source health failure and issue, ZERO absence candidates.
9. Before due: No absence whatever happens.
10. Health commit policy (F3): Two consecutive no-change runs -> no diff in status/sources.json;
    a status flip -> updates status/sources.json.
11. status/sources.json schema validation.
12. Stub issue manager lifecycle: open on failure, comment on repeat, close on recovery.
13. README-dev.md doc-hygiene: zero retired tokens (ENACTED_BOT_TOKEN, workflows-pending,
    SWAPP_BOT_APP_ID, Personal Access Token), names SWAPP_BOT_CLIENT_ID & SWAPP_BOT_PRIVATE_KEY,
    and all four workflow labels; all referenced workflow files exist.
"""

import os
import sys
import re
import json
import yaml
import time
import shutil
import hashlib
import tempfile
import unittest
from pathlib import Path
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

TESTS_DIR = Path(__file__).resolve().parent
REPO_DIR = TESTS_DIR.parent
SCRIPTS_DIR = REPO_DIR / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

from crawler import EnactedCrawler, ENACTED_USER_AGENT
from source_health import (
    load_source_health,
    save_source_health,
    record_source_check,
    manage_source_alert_issues,
    has_meaningful_change,
    StubIssueClient,
    get_iso_now
)
from check_water_sources import run_water_checks, load_all_system_sources
from bs4 import BeautifulSoup
import poll_montgomery
import poll_anne_arundel


class TestIngestSliceI1(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.tmp_path = Path(self.tmp_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    # 1. Workflow YAML Validity & Concurrency Separation
    def test_workflows_valid_yaml_and_concurrency(self):
        workflows_dir = REPO_DIR / ".github" / "workflows"
        self.assertTrue(workflows_dir.exists(), "Workflows dir must exist")

        workflow_files = list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml"))
        self.assertTrue(len(workflow_files) >= 2, "Expected at least 2 workflows")

        concurrency_groups = {}
        for wf_path in workflow_files:
            content = wf_path.read_text(encoding="utf-8")
            data = yaml.safe_load(content)
            self.assertIsInstance(data, dict, f"Failed to parse YAML in {wf_path.name}")

            concurrency = data.get("concurrency")
            if concurrency:
                group = concurrency.get("group") if isinstance(concurrency, dict) else concurrency
                concurrency_groups[wf_path.name] = group

        zoning_wf = concurrency_groups.get("ingest-zoning.yml")
        water_wf = concurrency_groups.get("ingest-water.yml")
        if zoning_wf and water_wf:
            self.assertNotEqual(
                zoning_wf, water_wf,
                "Zoning and water workflows must have separate concurrency groups so one failure never blocks the other"
            )

    # 2. Workflow Hygiene
    def test_workflow_hygiene(self):
        workflows_dir = REPO_DIR / ".github" / "workflows"
        workflow_files = list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml"))

        banned_terms = [
            "[FOUNDER:", "ENACTED_BOT_TOKEN", "hola-there", "firearms",
            "actions/checkout@v4", "actions/setup-python@v5", "actions/cache@v4",
            "actions/create-github-app-token@v1", "actions/upload-artifact@v4",
            "peter-evans/create-pull-request@v6",
            "app-id:", "SWAPP_BOT_APP_ID",
        ]
        for wf_path in workflow_files:
            content = wf_path.read_text(encoding="utf-8")

            for banned in banned_terms:
                self.assertNotIn(
                    banned, content,
                    f"Forbidden token '{banned}' found in {wf_path.name}"
                )

            if "runs-on:" in content:
                self.assertIn("runs-on: ubuntu-24.04", content, f"{wf_path.name} must use ubuntu-24.04 runner")

            # Node-24 action pins (ig12)
            self.assertIn("actions/checkout@v5", content, f"{wf_path.name} must use actions/checkout@v5")
            self.assertIn("actions/setup-python@v6", content, f"{wf_path.name} must use actions/setup-python@v6")
            self.assertIn("actions/cache@v5", content, f"{wf_path.name} must use actions/cache@v5")

            if wf_path.name.startswith("ingest-"):
                self.assertIn("actions/create-github-app-token@v3", content, f"{wf_path.name} must use actions/create-github-app-token@v3")
                self.assertIn("client-id: ${{ secrets.SWAPP_BOT_CLIENT_ID }}", content, f"{wf_path.name} must use client-id: ${{ secrets.SWAPP_BOT_CLIENT_ID }}")
                self.assertIn("actions/upload-artifact@v6", content, f"{wf_path.name} must use actions/upload-artifact@v6")
                self.assertIn("peter-evans/create-pull-request@v8", content, f"{wf_path.name} must use peter-evans/create-pull-request@v8")
                self.assertIn("${{ secrets.SWAPP_BOT_CLIENT_ID }}", content)
                self.assertIn("${{ secrets.SWAPP_BOT_PRIVATE_KEY }}", content)
                self.assertIn("swapp-bot[bot]", content)
                self.assertIn(
                    "# Disabled until /bot/ is live (sa06) and ig03 has run",
                    content,
                    f"{wf_path.name} must have cron commented out with the exact disabled note"
                )
                self.assertIn("Upload Health Artifact", content)

    # 3. Robots.txt Compliance
    def test_crawler_robots_txt_disallowed(self):
        crawler = EnactedCrawler(min_interval=0.0)
        host = "water.example.gov"
        robots_content = (
            "User-agent: *\n"
            "Disallow: /reports/\n"
            "Disallow: /internal/\n"
            "Allow: /public/\n"
        )
        crawler.register_robots_txt(host, robots_content)

        disallowed_url = f"https://{host}/reports/2026_ccr.pdf"
        self.assertFalse(crawler.can_fetch(disallowed_url))

        allowed, code, body, err = crawler.fetch(disallowed_url)
        self.assertFalse(allowed)
        self.assertEqual(code, 403)
        self.assertEqual(err, "disallowed_by_robots_txt")
        self.assertEqual(len(crawler.disallowed_log), 2)
        self.assertEqual(crawler.disallowed_log[0]["url"], disallowed_url)

        allowed_url = f"https://{host}/public/water_quality.html"
        self.assertTrue(crawler.can_fetch(allowed_url))

    # 4. Host Rate Limiting Spacing
    def test_crawler_rate_limiting_spacing(self):
        crawler = EnactedCrawler(min_interval=5.0, obey_robots=False)
        host = "source.example.gov"

        with patch("time.sleep") as mock_sleep:
            crawler.wait_if_needed(host)
            mock_sleep.assert_not_called()

            crawler.wait_if_needed(host)
            mock_sleep.assert_called_once()
            sleep_duration = mock_sleep.call_args[0][0]
            self.assertTrue(4.8 <= sleep_duration <= 5.0, f"Sleep duration was {sleep_duration}")

    # 5. Discovery of Newer-Year File: Both Issue Pattern and Year Rule (F1)
    def test_discovery_newer_year_file_cached_and_noted(self):
        repo = self.tmp_path / "repo"
        repo.mkdir()

        # System 1: uses issue_pattern
        sys1_dir = repo / "water" / "measurements" / "sys1_pattern"
        sys1_dir.mkdir(parents=True)
        old_bytes_1 = b"%PDF-1.4 sys1 2024 report"
        new_bytes_1 = b"%PDF-1.4 sys1 2025 report updated"
        new_sha_1 = hashlib.sha256(new_bytes_1).hexdigest()

        src1 = {
            "sources": [
                {
                    "id": "sys1_ccr",
                    "title": "Sys1 Quality Report",
                    "index_url": "https://water1.example.gov/index.html",
                    "cadence": "annual",
                    "cadence_basis": {
                        "rule": {
                            "citation": "40 CFR 141.152",
                            "quoted_sentence": "Reports must be delivered by July 1 annually."
                        }
                    },
                    "issue_pattern": r"(?:{period}[-_ ]*(?:ccr|water[-_ ]*quality[-_ ]*report)|(?:ccr|water[-_ ]*quality[-_ ]*report)[-_ ]*{period})",
                    "active": True,
                    "last_found": {
                        "title": "2024 Report",
                        "url": "https://water1.example.gov/reports/2024_ccr.pdf",
                        "sha256": hashlib.sha256(old_bytes_1).hexdigest()
                    }
                }
            ]
        }
        (sys1_dir / "sources.yaml").write_text(yaml.dump(src1), encoding="utf-8")

        # System 2: uses year rule (no issue_pattern)
        sys2_dir = repo / "water" / "measurements" / "sys2_year_rule"
        sys2_dir.mkdir(parents=True)
        old_bytes_2 = b"%PDF-1.4 sys2 2024 report"
        new_bytes_2 = b"%PDF-1.4 sys2 2025 report updated"
        new_sha_2 = hashlib.sha256(new_bytes_2).hexdigest()

        src2 = {
            "sources": [
                {
                    "id": "sys2_ccr",
                    "title": "Sys2 Annual Report",
                    "index_url": "https://water2.example.gov/index.html",
                    "cadence": "annual",
                    "cadence_basis": {
                        "rule": {
                            "citation": "40 CFR 141.152",
                            "quoted_sentence": "Reports must be delivered by July 1 annually."
                        }
                    },
                    "active": True,
                    "last_found": {
                        "title": "2024 Annual Water Quality Report",
                        "url": "https://water2.example.gov/reports/report_2024.pdf",
                        "sha256": hashlib.sha256(old_bytes_2).hexdigest()
                    }
                }
            ]
        }
        (sys2_dir / "sources.yaml").write_text(yaml.dump(src2), encoding="utf-8")

        mock_crawler = EnactedCrawler(min_interval=0.0, obey_robots=False)

        def mock_fetch(url, timeout=15):
            if url == "https://water1.example.gov/index.html":
                html = (
                    '<html><body>'
                    '<a href="https://water1.example.gov/reports/2024_ccr.pdf">2024 CCR</a>'
                    '<a href="https://water1.example.gov/reports/2025_ccr.pdf">2025 CCR</a>'
                    '</body></html>'
                )
                return True, 200, html.encode("utf-8"), ""
            elif url == "https://water1.example.gov/reports/2025_ccr.pdf":
                return True, 200, new_bytes_1, ""

            elif url == "https://water2.example.gov/index.html":
                html = (
                    '<html><body>'
                    '<a href="https://water2.example.gov/reports/report_2024.pdf">2024 Water Quality Report</a>'
                    '<a href="https://water2.example.gov/reports/report_2025.pdf">2025 Water Quality Report</a>'
                    '</body></html>'
                )
                return True, 200, html.encode("utf-8"), ""
            elif url == "https://water2.example.gov/reports/report_2025.pdf":
                return True, 200, new_bytes_2, ""

            return False, 404, b"", "not found"

        mock_crawler.fetch = mock_fetch

        stub_client = StubIssueClient()
        res = run_water_checks(
            repo_dir=repo,
            as_of=date(2026, 7, 15),
            crawler=mock_crawler,
            issue_client=stub_client
        )

        self.assertEqual(res["checked_sources"], 2)
        self.assertEqual(res["changed_sources"], 2)
        self.assertEqual(res["new_reports_count"], 2)

        # Both binaries cached under .cache/pdf_cache/{sha256}.bin
        cache_file_1 = repo / ".cache" / "pdf_cache" / f"{new_sha_1}.bin"
        self.assertTrue(cache_file_1.exists())
        self.assertEqual(cache_file_1.read_bytes(), new_bytes_1)

        cache_file_2 = repo / ".cache" / "pdf_cache" / f"{new_sha_2}.bin"
        self.assertTrue(cache_file_2.exists())
        self.assertEqual(cache_file_2.read_bytes(), new_bytes_2)

        # Manifest entries verified
        manifest_path = repo / ".cache" / "new_reports_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(len(manifest), 2)
        for entry in manifest:
            self.assertEqual(entry["note"], "new report — record not yet written")

        # Zero measurement markdown records authored
        self.assertEqual(len(list(sys1_dir.glob("*.md"))), 0)
        self.assertEqual(len(list(sys2_dir.glob("*.md"))), 0)

    # 6. Same-URL Changed Bytes Detected
    def test_same_url_changed_bytes(self):
        repo = self.tmp_path / "repo"
        repo.mkdir()
        sys_dir = repo / "water" / "measurements" / "test_system"
        sys_dir.mkdir(parents=True)

        old_bytes = b"%PDF-1.4 old content"
        old_sha = hashlib.sha256(old_bytes).hexdigest()
        new_bytes = b"%PDF-1.4 updated content at identical URL"
        new_sha = hashlib.sha256(new_bytes).hexdigest()

        sources_yaml = {
            "sources": [
                {
                    "id": "test_ccr",
                    "title": "Water Quality Report",
                    "cadence": "annual",
                    "active": True,
                    "last_found": {
                        "title": "2025 Report",
                        "url": "https://water.example.gov/report.pdf",
                        "sha256": old_sha
                    }
                }
            ]
        }
        (sys_dir / "sources.yaml").write_text(yaml.dump(sources_yaml), encoding="utf-8")

        mock_crawler = EnactedCrawler(min_interval=0.0, obey_robots=False)

        def mock_fetch(url, timeout=15):
            if url == "https://water.example.gov/report.pdf":
                return True, 200, new_bytes, ""
            return False, 404, b"", "not found"

        mock_crawler.fetch = mock_fetch

        stub_client = StubIssueClient()
        res = run_water_checks(
            repo_dir=repo,
            as_of=date(2026, 7, 15),
            crawler=mock_crawler,
            issue_client=stub_client
        )

        self.assertEqual(res["changed_sources"], 1)
        self.assertEqual(res["new_reports_count"], 1)
        cache_file = repo / ".cache" / "pdf_cache" / f"{new_sha}.bin"
        self.assertTrue(cache_file.exists())
        self.assertEqual(cache_file.read_bytes(), new_bytes)

    # 7. Absence: Past Due + Grace, Index OK, No Current-Cycle Link -> Exactly 1 Candidate (F1)
    def test_absence_past_due_plus_grace_index_ok_no_link(self):
        repo = self.tmp_path / "repo"
        repo.mkdir()
        sys_dir = repo / "water" / "measurements" / "test_system"
        sys_dir.mkdir(parents=True)

        sources_yaml = {
            "sources": [
                {
                    "id": "test_ccr",
                    "title": "Water Quality Report",
                    "index_url": "https://water.example.gov/reports",
                    "cadence": "annual",
                    "cadence_basis": {
                        "rule": {
                            "citation": "40 CFR 141.152(b)",
                            "quoted_sentence": "Reports must be delivered by July 1 each year."
                        }
                    },
                    "expected_by": "July 1 annually",
                    "grace_days": 30,
                    "active": True,
                    "last_found": {
                        "title": "2024 Report",
                        "url": "https://water.example.gov/reports/2024_report.pdf",
                        "sha256": "abcdef123456"
                    }
                }
            ]
        }
        (sys_dir / "sources.yaml").write_text(yaml.dump(sources_yaml), encoding="utf-8")

        mock_crawler = EnactedCrawler(min_interval=0.0, obey_robots=False)

        def mock_fetch(url, timeout=15):
            if url == "https://water.example.gov/reports":
                # Index fetched OK, but only contains old 2024 report link (no 2025 link)
                html = '<html><body><a href="https://water.example.gov/reports/2024_report.pdf">2024 Report</a></body></html>'
                return True, 200, html.encode("utf-8"), ""
            elif url == "https://water.example.gov/reports/2024_report.pdf":
                return True, 200, b"%PDF-1.4 2024 unchanged", ""
            return False, 404, b"", "not found"

        mock_crawler.fetch = mock_fetch

        # As of Aug 15, 2026: past July 1 + 30 days grace (July 31).
        stub_client = StubIssueClient()
        res = run_water_checks(
            repo_dir=repo,
            as_of=date(2026, 8, 15),
            crawler=mock_crawler,
            issue_client=stub_client
        )

        self.assertEqual(res["absence_candidates_count"], 1)
        cand = res["absence_candidates"][0]
        self.assertEqual(cand["source_id"], "test_ccr")
        self.assertEqual(cand["period"], "2025")
        self.assertEqual(cand["status"], "expected_report_not_found")

    # 8. Outages: Past Due + Grace, Index Unreachable -> Health Failure, ZERO Absence Candidates (F1)
    def test_outage_past_due_plus_grace_index_unreachable_no_absence_candidate(self):
        repo = self.tmp_path / "repo"
        repo.mkdir()
        sys_dir = repo / "water" / "measurements" / "test_system"
        sys_dir.mkdir(parents=True)

        sources_yaml = {
            "sources": [
                {
                    "id": "test_ccr",
                    "title": "Water Quality Report",
                    "index_url": "https://water.example.gov/reports",
                    "cadence": "annual",
                    "cadence_basis": {
                        "rule": {
                            "citation": "40 CFR 141.152(b)",
                            "quoted_sentence": "Reports must be delivered by July 1 each year."
                        }
                    },
                    "expected_by": "July 1 annually",
                    "grace_days": 30,
                    "active": True,
                    "last_found": {
                        "title": "2024 Report",
                        "url": "https://water.example.gov/reports/2024_report.pdf",
                        "sha256": "abcdef123456"
                    }
                }
            ]
        }
        (sys_dir / "sources.yaml").write_text(yaml.dump(sources_yaml), encoding="utf-8")

        mock_crawler = EnactedCrawler(min_interval=0.0, obey_robots=False)

        def mock_fetch(url, timeout=15):
            # Index page suffers an outage (HTTP 500)
            if url == "https://water.example.gov/reports":
                return True, 500, b"Server Error", "Internal Server Error"
            return False, 404, b"", "not found"

        mock_crawler.fetch = mock_fetch

        stub_client = StubIssueClient()
        res = run_water_checks(
            repo_dir=repo,
            as_of=date(2026, 8, 15),
            crawler=mock_crawler,
            issue_client=stub_client
        )

        # Invariant: Outages NEVER produce an absence candidate!
        self.assertEqual(res["absence_candidates_count"], 0)
        # Outage opens an issue on source alert
        self.assertEqual(len(stub_client.list_open_issues()), 1)
        self.assertEqual(res["issue_actions"][0]["action"], "opened")

    # 9. Before Due Date: No Absence Whatever Happens (F1)
    def test_before_due_date_no_absence(self):
        repo = self.tmp_path / "repo"
        repo.mkdir()
        sys_dir = repo / "water" / "measurements" / "test_system"
        sys_dir.mkdir(parents=True)

        sources_yaml = {
            "sources": [
                {
                    "id": "test_ccr",
                    "title": "Water Quality Report",
                    "index_url": "https://water.example.gov/reports",
                    "cadence": "annual",
                    "cadence_basis": {
                        "rule": {
                            "citation": "40 CFR 141.152(b)",
                            "quoted_sentence": "Reports must be delivered by July 1 each year."
                        }
                    },
                    "expected_by": "July 1 annually",
                    "grace_days": 30,
                    "active": True,
                    "last_found": {
                        "title": "2024 Report",
                        "url": "https://water.example.gov/reports/2024_report.pdf",
                        "sha256": "abcdef123456"
                    }
                }
            ]
        }
        (sys_dir / "sources.yaml").write_text(yaml.dump(sources_yaml), encoding="utf-8")

        mock_crawler = EnactedCrawler(min_interval=0.0, obey_robots=False)

        def mock_fetch(url, timeout=15):
            if url == "https://water.example.gov/reports":
                return True, 200, b"<html><body>Index</body></html>", ""
            return False, 404, b"", "not found"

        mock_crawler.fetch = mock_fetch

        stub_client = StubIssueClient()
        # Evaluated on June 1, 2026: before July 1 due date
        res = run_water_checks(
            repo_dir=repo,
            as_of=date(2026, 6, 1),
            crawler=mock_crawler,
            issue_client=stub_client
        )

        self.assertEqual(res["absence_candidates_count"], 0)

    # 10. Meaningful Health Change & PR Suppression Policy (F3)
    def test_meaningful_health_change_pr_suppression(self):
        status_path = self.tmp_path / "status" / "sources.json"
        artifact_path = self.tmp_path / "sources-health.json"
        summary_path = self.tmp_path / "summary.md"

        initial_health = {
            "version": "1.0",
            "last_run": "2026-10-20T16:00:00Z",
            "sources": {
                "src_a": {
                    "source_id": "src_a",
                    "url": "https://example.gov/a",
                    "status": "ok",
                    "consecutive_failures": 0,
                    "last_reached": "2026-10-20T16:00:00Z",
                    "last_changed": "2026-09-14T00:00:00Z"
                }
            }
        }
        # Save initial file
        save_source_health(initial_health, status_path, only_if_meaningful=False, artifact_path=artifact_path)
        initial_content = status_path.read_text(encoding="utf-8")

        # Run 2: Unchanged run where only timestamps advance (no status flip, no last_changed move)
        run2_health = {
            "version": "1.0",
            "last_run": "2026-10-21T06:00:00Z",
            "sources": {
                "src_a": {
                    "source_id": "src_a",
                    "url": "https://example.gov/a",
                    "status": "ok",
                    "consecutive_failures": 0,
                    "last_reached": "2026-10-21T06:00:00Z",
                    "last_changed": "2026-09-14T00:00:00Z"
                }
            }
        }
        updated = save_source_health(
            run2_health, status_path, only_if_meaningful=True,
            step_summary_path=summary_path, artifact_path=artifact_path
        )
        self.assertFalse(updated, "status/sources.json must NOT be updated when only timestamps change")
        self.assertEqual(status_path.read_text(encoding="utf-8"), initial_content, "File on disk must remain bit-for-bit identical")
        # Full health was written to artifact and summary
        self.assertTrue(artifact_path.exists())
        self.assertIn("2026-10-21T06:00:00Z", artifact_path.read_text(encoding="utf-8"))
        self.assertTrue(summary_path.exists())

        # Run 3: Status flip occurs (source becomes unreachable)
        run3_health = {
            "version": "1.0",
            "last_run": "2026-10-22T06:00:00Z",
            "sources": {
                "src_a": {
                    "source_id": "src_a",
                    "url": "https://example.gov/a",
                    "status": "unreachable: HTTP 500",
                    "consecutive_failures": 1,
                    "last_reached": "2026-10-21T06:00:00Z",
                    "last_changed": "2026-09-14T00:00:00Z"
                }
            }
        }
        updated_flip = save_source_health(
            run3_health, status_path, only_if_meaningful=True,
            step_summary_path=summary_path, artifact_path=artifact_path
        )
        self.assertTrue(updated_flip, "status/sources.json MUST be updated on a status flip")
        self.assertIn("unreachable: HTTP 500", status_path.read_text(encoding="utf-8"))

    # 11. status/sources.json Schema Validation
    def test_sources_json_schema(self):
        status_file = REPO_DIR / "status" / "sources.json"
        self.assertTrue(status_file.exists(), "status/sources.json must exist in repo")

        data = json.loads(status_file.read_text(encoding="utf-8"))
        self.assertIn("version", data)
        self.assertIn("last_run", data)
        self.assertIn("sources", data)
        self.assertIsInstance(data["sources"], dict)

        for sid, src in data["sources"].items():
            self.assertEqual(src.get("source_id"), sid)
            self.assertIn("url", src)
            self.assertIn("last_reached", src)
            self.assertIn("last_changed", src)
            self.assertIn("consecutive_failures", src)
            self.assertIn("status", src)
            self.assertIsInstance(src["consecutive_failures"], int)

    # 12. Stub Issue Manager Lifecycle (Open -> Comment -> Close)
    def test_stub_issue_manager_lifecycle(self):
        client = StubIssueClient()
        source_id = "test_src"
        url = "https://example.gov/water"

        health = {
            "version": "1.0",
            "last_run": get_iso_now(),
            "sources": {}
        }

        # Step 1: First failure -> opens issue
        record_source_check(source_id, url, success=False, error="HTTP 500", health_data=health)
        actions = manage_source_alert_issues(health, issue_client=client)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["action"], "opened")
        self.assertEqual(len(client.list_open_issues()), 1)
        issue_num = actions[0]["issue_number"]

        # Step 2: Repeat failure -> comments on existing issue
        record_source_check(source_id, url, success=False, error="HTTP 503", health_data=health)
        actions = manage_source_alert_issues(health, issue_client=client)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["action"], "commented")
        self.assertEqual(len(client.comments), 1)
        self.assertEqual(len(client.list_open_issues()), 1)

        # Step 3: Recovery -> closes issue
        record_source_check(source_id, url, success=True, health_data=health)
        actions = manage_source_alert_issues(health, issue_client=client)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["action"], "closed")
        self.assertEqual(len(client.list_open_issues()), 0)

    # 13. README-dev.md Doc-Hygiene Test
    def test_readme_dev_doc_hygiene(self):
        readme_dev_path = REPO_DIR / "README-dev.md"
        self.assertTrue(readme_dev_path.exists(), "README-dev.md must exist in repository root")
        content = readme_dev_path.read_text(encoding="utf-8")

        banned_tokens = [
            "ENACTED_BOT_TOKEN",
            "workflows-pending",
            "SWAPP_BOT_APP_ID",
            "Personal Access Token",
        ]
        for token in banned_tokens:
            self.assertNotIn(
                token, content,
                f"Forbidden stale token '{token}' found in README-dev.md"
            )

        required_tokens = [
            "SWAPP_BOT_CLIENT_ID",
            "SWAPP_BOT_PRIVATE_KEY",
            "ingestion-failure",
            "source-alert",
            "automated-ingest",
            "needs-review",
        ]
        for token in required_tokens:
            self.assertIn(
                token, content,
                f"Required token '{token}' missing from README-dev.md"
            )

        # Every workflow file named in README-dev.md exists in .github/workflows/
        workflows_dir = REPO_DIR / ".github" / "workflows"
        workflow_mentions = set(re.findall(r"[\w-]+\.ya?ml", content))
        self.assertTrue(len(workflow_mentions) > 0, "Expected workflow references in README-dev.md")
        for wf_name in workflow_mentions:
            wf_file = workflows_dir / wf_name
            self.assertTrue(
                wf_file.exists(),
                f"Workflow '{wf_name}' named in README-dev.md does not exist in .github/workflows/"
            )

    # 14. Poller Code No-Inference Grep Test
    def test_poller_code_no_inference_grep(self):
        scripts_to_check = [
            SCRIPTS_DIR / "poll_montgomery.py",
            SCRIPTS_DIR / "poll_anne_arundel.py",
            SCRIPTS_DIR / "check_water_sources.py",
        ]
        banned_patterns = [
            ("[pending verification]", "placeholder sponsor/status default"),
            ('or "Introduced"', "inferred fallback status"),
            ("or 'Introduced'", "inferred fallback status"),
            ('"action_status": "Introduced"', "hardcoded action_status default"),
            ("'action_status': 'Introduced'", "hardcoded action_status default"),
            ("montgomerycountymd.gov/COUNCIL/Resources/Files/zta/", "constructed URL template"),
        ]
        for script_path in scripts_to_check:
            self.assertTrue(script_path.exists(), f"Script {script_path.name} must exist")
            text = script_path.read_text(encoding="utf-8")
            for pattern, reason in banned_patterns:
                self.assertNotIn(
                    pattern, text,
                    f"Forbidden pattern '{pattern}' ({reason}) found in {script_path.name}"
                )

    # 15. Montgomery Schema Contract Validation Test
    def test_montgomery_schema_contract_validation(self):
        fixture_path = TESTS_DIR / "fixtures" / "montgomery_zoning_response.json"
        contract_path = REPO_DIR / "sources" / "contracts" / "montgomery_zoning.yaml"
        self.assertTrue(fixture_path.exists(), "Montgomery response fixture must exist")
        self.assertTrue(contract_path.exists(), "Montgomery contract must exist")

        fixture_data = json.loads(fixture_path.read_text(encoding="utf-8"))
        contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))

        # Real fixture passes contract check
        poll_montgomery.check_schema_contract(fixture_data, contract)

        # Missing or renamed field raises "schema changed: <field>"
        bad_fixture = [{"renamed_col": "val", "title": "Some Title"}]
        with self.assertRaises(ValueError) as ctx:
            poll_montgomery.check_schema_contract(bad_fixture, contract)
        self.assertIn("schema changed: zta_no", str(ctx.exception))

    # 16. Montgomery Stale Source Handling Test
    def test_montgomery_stale_source_handling(self):
        mock_crawler = EnactedCrawler(min_interval=0.0, obey_robots=False)
        mock_crawler.fetch = MagicMock(side_effect=AssertionError("Fetch must not be called when source is stale"))

        stale_health = {
            "sources": {
                "montgomery_zoning": {
                    "status": "stale",
                    "stale_reason": "newest row 24-01, metadata date June 6, 2024"
                }
            }
        }
        res = poll_montgomery.poll(crawler=mock_crawler, health_data=stale_health)
        self.assertEqual(res, 0)
        mock_crawler.fetch.assert_not_called()

    # 17. Montgomery Missing Required Fields Skips Without Defaults
    def test_montgomery_missing_required_fields_skips_without_defaults(self):
        tmp_dir = self.tmp_path / "montgomery_out"
        tmp_dir.mkdir(parents=True, exist_ok=True)

        # Batch has contract-satisfying record plus record missing action_status (like live ZTA 23-09)
        batch = [
            {
                "zta_no": "24-01",
                "title": "Existing Valid ZTA",
                "introduction_date": "2024-01-16",
                "sponsor_s": "Councilmember Stewart",
                "action_status": "Adopted",
                "ordinance": {"url": "https://example.gov/24-01.pdf"}
            },
            {
                "zta_no": "99-99",
                "title": "Test Missing Status ZTA",
                "introduction_date": "2026-01-01",
                "sponsor_s": "Councilmember Test",
                "ordinance": {"url": "https://example.gov/doc.pdf"}
                # action_status intentionally omitted
            }
        ]

        # Simulate 24-01 already existing on disk so it is not re-ingested
        (tmp_dir / "zta_24_01.md").write_text("existing", encoding="utf-8")

        with patch("poll_montgomery.MONTGOMERY_DIR", str(tmp_dir)):
            mock_crawler = EnactedCrawler(min_interval=0.0, obey_robots=False)
            mock_crawler.fetch = MagicMock(return_value=(True, 200, json.dumps(batch).encode("utf-8"), ""))
            # Call poll with non-stale health_data
            ingested = poll_montgomery.poll(
                crawler=mock_crawler,
                health_data={"sources": {"montgomery_zoning": {"status": "ok"}}}
            )
            self.assertEqual(ingested, 0)
            # Only zta_24_01.md exists; 99-99 was skipped without defaulting
            created_files = [f.name for f in tmp_dir.glob("*.md")]
            self.assertEqual(created_files, ["zta_24_01.md"], "Record missing required field must be skipped")

    # 18. Anne Arundel Schema Contract Validation Test
    def test_anne_arundel_schema_contract_validation(self):
        contract_path = REPO_DIR / "sources" / "contracts" / "anne_arundel_zoning.yaml"
        self.assertTrue(contract_path.exists(), "Anne Arundel contract must exist")
        contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))

        # 1. Past legislation listing fixture
        past_fixture = TESTS_DIR / "fixtures" / "aa_past_legislation.html"
        self.assertTrue(past_fixture.exists(), "aa_past_legislation.html fixture must exist")
        past_soup = BeautifulSoup(past_fixture.read_text(encoding="utf-8"), "html.parser")
        poll_anne_arundel.check_html_schema_contract(past_soup, contract, is_bill_page=False)

        # 2. Bill detail page fixture (Bill 67-26)
        bill_fixture = TESTS_DIR / "fixtures" / "aa_bill_67_26.html"
        self.assertTrue(bill_fixture.exists(), "aa_bill_67_26.html fixture must exist")
        bill_soup = BeautifulSoup(bill_fixture.read_text(encoding="utf-8"), "html.parser")
        poll_anne_arundel.check_html_schema_contract(bill_soup, contract, is_bill_page=True)

        # 3. Bad HTML missing required selector raises schema changed error
        bad_soup = BeautifulSoup("<html><body><p>No content</p></body></html>", "html.parser")
        with self.assertRaises(ValueError) as ctx:
            poll_anne_arundel.check_html_schema_contract(bad_soup, contract, is_bill_page=False)
        self.assertIn("schema changed:", str(ctx.exception))

    # 19. Anne Arundel Zoning Inclusion Rule Classification Test
    def test_anne_arundel_zoning_rule_classification(self):
        # Inclusions: "AN ORDINANCE concerning: Zoning" and "AN ORDINANCE concerning: Subdivision and Development"
        self.assertTrue(poll_anne_arundel.matches_zoning_rule("AN ORDINANCE concerning: Zoning – BWI Mixed Use Overlay Area"))
        self.assertTrue(poll_anne_arundel.matches_zoning_rule("(As Amended) AN ORDINANCE concerning: Zoning – BWI Mixed Use Overlay Area"))
        self.assertTrue(poll_anne_arundel.matches_zoning_rule("Bill No. 67-26: (As Amended) AN ORDINANCE concerning: Zoning – BWI Mixed Use"))
        self.assertTrue(poll_anne_arundel.matches_zoning_rule("AN ORDINANCE concerning: Subdivision and Development – Cottage Homes"))

        # Exclusions: Other subject matters
        self.assertFalse(poll_anne_arundel.matches_zoning_rule("AN ORDINANCE concerning: Current Expense Budget – FY27"))
        self.assertFalse(poll_anne_arundel.matches_zoning_rule("AN ORDINANCE concerning: Public Safety – Police Department"))
        self.assertFalse(poll_anne_arundel.matches_zoning_rule("AN ORDINANCE concerning: Personnel – Salaries"))

    # 20. Anne Arundel Missing Required Fields Skips
    def test_anne_arundel_missing_required_fields_skips(self):
        # Missing sponsor
        mock_html_no_sponsor = (
            "<html><body>"
            "<h1>Bill No. 99-99</h1>"
            "<div class=\"zn-field-intro\">AN ORDINANCE concerning: Zoning - Test</div>"
            "<div class=\"zn-legislation-documents\"><a href=\"/test.pdf\">PDF</a></div>"
            "</body></html>"
        )
        rec = poll_anne_arundel.parse_bill_page(mock_html_no_sponsor, "https://example.gov/bill-no-99-99")
        self.assertIsNone(rec, "Record with missing sponsor must return None and skip")

        # Missing PDF
        mock_html_no_pdf = (
            "<html><body>"
            "<h1>Bill No. 99-99</h1>"
            "<div class=\"zn-field-intro\">AN ORDINANCE concerning: Zoning - Test</div>"
            "<div class=\"zn-field-introduced-by\">Mr. Smith</div>"
            "</body></html>"
        )
        rec = poll_anne_arundel.parse_bill_page(mock_html_no_pdf, "https://example.gov/bill-no-99-99")
        self.assertIsNone(rec, "Record with missing PDF must return None and skip")

    # 21. Verify Gate No Direct Network Grep Test
    def test_verify_gate_no_direct_network_grep(self):
        verify_py = REPO_DIR / "verify_corpus_integrity.py"
        self.assertTrue(verify_py.exists(), "verify_corpus_integrity.py must exist")
        text = verify_py.read_text(encoding="utf-8")
        forbidden = ["urllib.request", "requests", "urlopen", "curl.exe"]
        for f_word in forbidden:
            self.assertNotIn(f_word, text, f"Direct network primitive '{f_word}' forbidden in verify_corpus_integrity.py")

    # 22. Verify Gate Robots.txt Skip Mock Test
    def test_verify_gate_robots_txt_skip(self):
        # EnactedCrawler with disallowed host
        crawler = EnactedCrawler(min_interval=0.0, obey_robots=True)
        crawler.register_robots_txt("blocked.gov", "User-agent: *\nDisallow: /\n")
        crawler.register_robots_txt("allowed.gov", "User-agent: *\nAllow: /\n")

        # Blocked URL is not permitted and not fetched
        self.assertFalse(crawler.can_fetch("https://blocked.gov/doc.pdf"))
        # Allowed URL is permitted
        self.assertTrue(crawler.can_fetch("https://allowed.gov/doc.pdf"))

    # 22b. Verify Gate Crawler Default Interval Test
    def test_verify_crawler_default_interval_unset(self):
        """With VERIFY_CRAWLER_INTERVAL unset, verify gate crawler must have min_interval == 5.0 (the crawler default)."""
        import verify_corpus_integrity as vci
        old_val = os.environ.pop("VERIFY_CRAWLER_INTERVAL", None)
        try:
            crawler = vci.get_verify_crawler()
            self.assertEqual(crawler.min_interval, 5.0)
            os.environ["VERIFY_CRAWLER_INTERVAL"] = "1.5"
            crawler_override = vci.get_verify_crawler()
            self.assertEqual(crawler_override.min_interval, 1.5)
        finally:
            if old_val is not None:
                os.environ["VERIFY_CRAWLER_INTERVAL"] = old_val
            else:
                os.environ.pop("VERIFY_CRAWLER_INTERVAL", None)

    # 23. Stale Source Alert Lifecycle & Run Summary Order Test
    def test_stale_source_alert_lifecycle(self):
        client = StubIssueClient()
        health = {
            "version": "1.0",
            "last_run": get_iso_now(),
            "sources": {
                "active_src": {
                    "source_id": "active_src",
                    "status": "ok",
                    "consecutive_failures": 0,
                    "url": "https://example.gov/active"
                },
                "stale_src": {
                    "source_id": "stale_src",
                    "status": "stale",
                    "stale_reason": "metadata date June 6, 2024",
                    "consecutive_failures": 0,
                    "url": "https://example.gov/stale"
                }
            }
        }

        # Step 1: Manage issues opens a stale alert issue
        actions = manage_source_alert_issues(health, issue_client=client)
        stale_actions = [a for a in actions if a["source_id"] == "stale_src"]
        self.assertEqual(len(stale_actions), 1)
        self.assertEqual(stale_actions[0]["action"], "opened")
        open_issues = client.list_open_issues(label="source-alert")
        self.assertEqual(len(open_issues), 1)
        self.assertIn("stale_src stale", open_issues[0]["title"])

        # Step 2: Next run keeps the stale issue open (does NOT close it!)
        actions2 = manage_source_alert_issues(health, issue_client=client)
        stale_actions2 = [a for a in actions2 if a["source_id"] == "stale_src"]
        self.assertEqual(len(stale_actions2), 1)
        self.assertEqual(stale_actions2[0]["action"], "kept_open")
        self.assertEqual(len(client.list_open_issues(label="source-alert")), 1)

        # Step 3: Summary table sorts stale sources first
        summary_file = self.tmp_path / "step_summary.md"
        save_source_health(health, status_path=self.tmp_path / "sources.json", only_if_meaningful=False, step_summary_path=summary_file)
        summary_text = summary_file.read_text(encoding="utf-8")
        stale_idx = summary_text.find("stale_src")
        active_idx = summary_text.find("active_src")
        self.assertNotEqual(stale_idx, -1)
        self.assertNotEqual(active_idx, -1)
        self.assertLess(stale_idx, active_idx, "Stale source must appear before active source in summary table")


if __name__ == "__main__":
    unittest.main()
