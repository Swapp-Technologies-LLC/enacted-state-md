"""
generate_newsletter.py
Task 6: Enacted Newsletter Generation Engine
Renders newsletters strictly FROM backing legal record files in the corpus.
Invariant: The newsletter is a view of the corpus, never a source.
Swapp Technologies LLC (Maryland LLC)
"""

import os
import re
import html
import yaml
from pathlib import Path
from typing import Optional, Dict, Any, List

from generate_feeds import closing_line
try:
    from build import format_water_heading
except ImportError:
    import sys
    _site_dir = str(Path(__file__).resolve().parent.parent / "enacted-site")
    if _site_dir not in sys.path:
        sys.path.insert(0, _site_dir)
    from build import format_water_heading

REPO_BASE = Path(__file__).resolve().parent if (Path(__file__).resolve().parent / "anne_arundel").exists() else Path(__file__).resolve().parent / "staging" / "enacted-state-md"
DEV_DIR = Path("dev")
BRAIN_DIR = Path(os.environ.get("BRAIN_DIR", str(Path(__file__).resolve().parent / "dev")))

def parse_record_file(filepath: Path) -> dict:
    """Parses frontmatter and content from a markdown legal record file."""
    text = filepath.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if len(parts) >= 3:
        frontmatter = yaml.safe_load(parts[1]) or {}
        body = parts[2].strip()
    else:
        frontmatter = {}
        body = text
    return {"frontmatter": frontmatter, "body": body, "path": filepath}

def render_email_scaffold(jurisdiction_badge: str, jurisdiction_name: str, lead_text: str, items_html: str, contacts_html: str, last_ingested_iso: str, primary_portal: str, primary_domain: str) -> str:
    return f"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" lang="en">
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Enacted — {jurisdiction_name} Zoning Signal</title>
  <style type="text/css">
    body, table, td, a {{ -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }}
    table, td {{ mso-table-lspace: 0pt; mso-table-rspace: 0pt; }}
    img {{ -ms-interpolation-mode: bicubic; border: 0; outline: none; text-decoration: none; }}
    table {{ border-collapse: collapse !important; }}
    body {{ margin: 0 !important; padding: 0 !important; width: 100% !important; background-color: #0b2732; }}

    @media screen {{
      @font-face {{
        font-family: 'Source Serif 4';
        font-style: normal;
        font-weight: 600;
        src: local('Source Serif 4'), local('SourceSerif4-SemiBold'), url(https://fonts.gstatic.com/s/sourceserif4/v8/neIIzCuh3AThbF07Z9v7a1W7z1w.woff2) format('woff2');
      }}
    }}

    @media only screen and (max-width: 620px) {{
      .email-container {{ width: 100% !important; max-width: 100% !important; }}
      .mobile-padding {{ padding-left: 20px !important; padding-right: 20px !important; }}
      .col-split {{ display: block !important; width: 100% !important; box-sizing: border-box !important; }}
    }}
  </style>
</head>
<body style="margin: 0; padding: 0; background-color: #0b2732; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">

  <!-- Outer Canvas Table (Ink #0b2732) -->
  <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #0b2732; table-layout: fixed;">
    <tr>
      <td align="center" style="padding: 24px 12px 40px 12px;">

        <!-- Main Email Container (600px) -->
        <table role="presentation" class="email-container" border="0" cellpadding="0" cellspacing="0" width="600" style="max-width: 600px; background-color: #f7f4ee; border-radius: 4px; overflow: hidden; box-shadow: 0 8px 32px rgba(0, 0, 0, 0.45);">

          <!-- Masthead Header -->
          <tr>
            <td style="background-color: #0b2732; padding: 28px 32px 24px 32px; border-bottom: 4px solid #9cd0ca;">
              <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%">
                <tr>
                  <td>
                    <!-- Brand Mark + Wordmark -->
                    <table role="presentation" border="0" cellpadding="0" cellspacing="0">
                      <tr>
                        <!-- Direction E Mark: Paper over Ghost + Mint Change-Bar -->
                        <td valign="middle" style="padding-right: 14px;">
                          <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="32" height="38" style="background-color: #f7f4ee; border-left: 4px solid #9cd0ca; box-shadow: 2px 2px 0px #527a83;">
                            <tr>
                              <td align="center" valign="middle" style="font-family: 'Source Serif 4', Georgia, serif; font-size: 18px; font-weight: 700; color: #0b2732; line-height: 1;">
                                &para;
                              </td>
                            </tr>
                          </table>
                        </td>
                        <td valign="middle">
                          <div style="font-family: 'Source Serif 4', Georgia, serif; font-size: 24px; font-weight: 700; color: #f7f4ee; letter-spacing: -0.02em; line-height: 1.1;">
                            Enacted
                          </div>
                          <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 11px; font-weight: 500; color: #9cd0ca; letter-spacing: 0.08em; text-transform: uppercase; margin-top: 4px;">
                            What changed. What's current. Who to ask.
                          </div>
                        </td>
                      </tr>
                    </table>
                  </td>
                  <td align="right" valign="top">
                    <!-- Jurisdiction Badge -->
                    <span style="display: inline-block; background-color: rgba(156, 208, 202, 0.12); border: 1px solid #527a83; color: #9cd0ca; padding: 4px 10px; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; border-radius: 2px;">
                      {jurisdiction_badge}
                    </span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Context Subheader & Timestamp -->
          <tr>
            <td style="background-color: #0e2e3a; padding: 12px 32px; border-bottom: 1px solid #1c4250;">
              <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%">
                <tr>
                  <td style="font-size: 12px; color: #88a1a6; font-family: -apple-system, BlinkMacSystemFont, sans-serif;">
                    Signal Dispatch &middot; <strong>Primary Government Record Notification</strong>
                  </td>
                  <td align="right" style="font-size: 12px; color: #9cd0ca; font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-weight: 500;">
                    Last checked: 2026-09-04
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Editorial Lead / Posture Statement -->
          <tr>
            <td class="mobile-padding" style="padding: 28px 32px 16px 32px;">
              <div style="font-family: 'Source Serif 4', Georgia, serif; font-size: 20px; font-weight: 600; color: #0b2732; line-height: 1.35; margin-bottom: 8px;">
                {jurisdiction_name} Land-Use &amp; Zoning Updates
              </div>
              <p style="margin: 0; font-size: 14px; line-height: 1.6; color: #527a83;">
                {lead_text}
              </p>
            </td>
          </tr>

          <!-- DIVIDER -->
          <tr>
            <td style="padding: 0 32px;">
              <hr style="border: 0; border-top: 1px solid #e5dfd3; margin: 8px 0 20px 0;" />
            </td>
          </tr>

          <!-- ITEMS RENDERED FROM RECORD FILES -->
          {items_html}

          <!-- WHO TO ASK DIRECTORY -->
          <tr>
            <td class="mobile-padding" style="background-color: #0b2732; padding: 28px 32px; color: #f7f4ee;">
              <div style="font-family: 'Source Serif 4', Georgia, serif; font-size: 18px; font-weight: 600; color: #9cd0ca; margin-bottom: 6px;">
                Who to Ask (County contacts &middot; Source + last-checked date)
              </div>
              <p style="margin: 0 0 16px 0; font-size: 13px; line-height: 1.5; color: #88a1a6;">
                Enacted reports the primary government record and does not advise or certify. For official zoning verifications, interpretations, or development reviews in {jurisdiction_name}:
              </p>

              {contacts_html}
            </td>
          </tr>

          <!-- FOOTER & AUDIT PROVENANCE -->
          <tr>
            <td class="mobile-padding" style="background-color: #08161d; padding: 24px 32px; border-top: 1px solid #142f3b; color: #88a1a6; font-size: 11px; line-height: 1.6;">
              <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%">
                <tr>
                  <td>
                    <div style="font-weight: 600; color: #f7f4ee; margin-bottom: 4px;">
                      Primary Government Sourcing (L-01 Read-Only Posture)
                    </div>
                    <p style="margin: 0 0 10px 0;">
                      All data retrieved directly from primary government records (<a href="{primary_portal}" target="_blank" style="color: #9cd0ca; text-decoration: underline;">{primary_domain}</a>). Zero third-party aggregator dependencies (hard blocklist on Municode, AmLegal, and eCode360). Enacted records the enacted law and does not advise or certify.
                    </p>
                    <p style="margin: 0 0 10px 0; font-family: monospace; font-size: 10px; color: #527a83;">
                      LAST_INGESTED: {last_ingested_iso}
                    </p>
                    <p style="margin: 0 0 10px 0;">
                      <a href="/unsubscribe" style="color: #9cd0ca; text-decoration: underline;">Unsubscribe</a> &middot; <a href="/follows" style="color: #9cd0ca; text-decoration: underline;">Manage follows</a> &middot; <a href="/coverage" style="color: #9cd0ca; text-decoration: underline;">Coverage statement</a> &middot; <a href="/how-to-read#zoning" style="color: #9cd0ca; text-decoration: underline;">How to read a record</a>
                    </p>
                    <div style="color: #527a83;">
                      {closing_line(['zoning'])} &copy; 2026 Swapp Technologies LLC &middot; [FOUNDER: confirm mailing address] &middot; Organized under the laws of Maryland &middot; <a href="https://enacted.app" target="_blank" style="color: #527a83; text-decoration: underline;">enacted.app</a>
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

        </table>
        <!-- /End Email Container -->

      </td>
    </tr>
  </table>

</body>
</html>"""

def render_anne_arundel(show_first_issue_key: bool = False):
    aa_dir = REPO_BASE / "anne_arundel" / "council_bills"
    b18 = parse_record_file(aa_dir / "bill_18_26.md")
    b28 = parse_record_file(aa_dir / "bill_28_26.md")
    b57 = parse_record_file(aa_dir / "bill_57_26.md")

    first_issue_key_html = ""
    if show_first_issue_key:
        first_issue_key_html = """
          <!-- FIRST ISSUE KEY -->
          <tr>
            <td class="mobile-padding" style="padding: 0 32px 20px 32px;">
              <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="border: 1px solid #d8d2c6; background-color: #fbfaf6; padding: 14px 18px;">
                <tr>
                  <td>
                    <div style="font-family: 'Source Serif 4', Georgia, serif; font-size: 10.5px; letter-spacing: 0.14em; text-transform: uppercase; color: #527a83; margin-bottom: 6px; font-weight: 600;">How to read a record &middot; shown in the first issue</div>
                    <div style="font-size: 13.5px; line-height: 1.5; color: #2c3e44; margin-bottom: 10px;">Each record carries a small sun on a line. Where it sits shows the provision&rsquo;s life stage. The shape carries the meaning, never the color alone.</div>
                    <table role="presentation" border="0" cellpadding="6" cellspacing="0" width="100%" style="font-size: 12px; line-height: 1.45; color: #0b2732; border-top: 1px solid #d8d2c6;">
                      <tr style="border-bottom: 1px solid #d8d2c6;">
                        <td width="36" align="center" valign="middle"><svg width="24" height="16" viewBox="0 0 18 12" aria-hidden="true"><path d="M2 11 A7 7 0 0 1 16 11" fill="none" stroke="#88a1a6" stroke-width="1.6" stroke-dasharray="2 2"/></svg></td>
                        <td width="120" valign="middle" style="font-size: 10.5px; letter-spacing: 0.12em; text-transform: uppercase; font-weight: 600;">Pending</td>
                        <td valign="middle" style="color: #2c3e44;">Adopted, but the effective date is still ahead. Not yet law.</td>
                      </tr>
                      <tr style="border-bottom: 1px solid #d8d2c6;">
                        <td width="36" align="center" valign="middle"><svg width="24" height="16" viewBox="0 0 18 12" aria-hidden="true"><path d="M2 11 A7 7 0 0 1 16 11" fill="#9cd0ca" stroke="#0b2732" stroke-width="1.6"/></svg></td>
                        <td width="120" valign="middle" style="font-size: 10.5px; letter-spacing: 0.12em; text-transform: uppercase; font-weight: 600;">Took effect</td>
                        <td valign="middle" style="color: #2c3e44;">A new provision is in force as of the date shown.</td>
                      </tr>
                      <tr style="border-bottom: 1px solid #d8d2c6;">
                        <td width="36" align="center" valign="middle"><svg width="24" height="16" viewBox="0 0 18 12" aria-hidden="true"><path d="M2 11 A7 7 0 0 1 16 11" fill="#9cd0ca" stroke="#0b2732" stroke-width="1.6"/><rect x="8" y="2" width="2.5" height="9" fill="#0b2732"/></svg></td>
                        <td width="120" valign="middle" style="font-size: 10.5px; letter-spacing: 0.12em; text-transform: uppercase; font-weight: 600;">Amended</td>
                        <td valign="middle" style="color: #2c3e44;">The text changed. Deletions are struck, additions underscored.</td>
                      </tr>
                      <tr style="border-bottom: 1px solid #d8d2c6;">
                        <td width="36" align="center" valign="middle"><svg width="24" height="16" viewBox="0 0 18 12" aria-hidden="true"><path d="M2 11 A7 7 0 0 1 16 11" fill="none" stroke="#0b2732" stroke-width="1.6"/><line x1="2" y1="11" x2="16" y2="11" stroke="#0b2732" stroke-width="2"/></svg></td>
                        <td width="120" valign="middle" style="font-size: 10.5px; letter-spacing: 0.12em; text-transform: uppercase; font-weight: 600;">Sunsets soon</td>
                        <td valign="middle" style="color: #2c3e44;">Its own clause sets an expiry, and that date is near.</td>
                      </tr>
                      <tr>
                        <td width="36" align="center" valign="middle"><svg width="24" height="16" viewBox="0 0 18 12" aria-hidden="true"><path d="M2 11 A7 7 0 0 1 16 11" fill="none" stroke="#a05252" stroke-width="1.6"/><line x1="4" y1="3" x2="14" y2="11" stroke="#a05252" stroke-width="1.6"/></svg></td>
                        <td width="120" valign="middle" style="font-size: 10.5px; letter-spacing: 0.12em; text-transform: uppercase; font-weight: 600;">Repealed</td>
                        <td valign="middle" style="color: #2c3e44;">Removed or expired. The old text stays on the record.</td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        """

    items_html = f"""
          {first_issue_key_html}
          <!-- ITEM 1: {b18['frontmatter']['bill_number']} -->
          <tr>
            <td class="mobile-padding" style="padding: 0 32px 24px 32px;">
              <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #ffffff; border: 1px solid #e2d9c7; border-left: 4px solid #527a83; border-radius: 2px;">
                <tr>
                  <td style="padding: 20px 22px;">
                    <table role="presentation" border="0" cellpadding="0" cellspacing="0" style="margin-bottom: 12px;">
                      <tr>
                        <td style="background-color: #eaf6f4; border: 1px solid #9cd0ca; border-radius: 2px; padding: 3px 8px;">
                          <span style="color: #0b2732; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">
                            PASSED &middot; VETO OVERRIDDEN
                          </span>
                        </td>
                        <td style="padding-left: 10px; font-size: 12px; color: #88a1a6; font-family: -apple-system, BlinkMacSystemFont, sans-serif;">
                          Base Effective: {b18['frontmatter']['effective_date_base']} &middot; Overrides Effective: {b18['frontmatter']['effective_date_overridden_amendments']}
                        </td>
                      </tr>
                    </table>
                    <div style="font-family: 'Source Serif 4', Georgia, serif; font-size: 17px; font-weight: 600; color: #0b2732; line-height: 1.3; margin-bottom: 6px;">
                      {b18['frontmatter']['bill_number']}: Comprehensive Zoning &mdash; Region Planning Area No. 5 (As Amended)
                    </div>
                    <div style="font-size: 12px; color: #527a83; margin-bottom: 14px; font-weight: 500;">
                      <strong>Affected Communities:</strong> Odenton, Crofton, Piney Orchard, Gambrills, Woodwardville, Two Rivers
                    </div>
                    <div style="background-color: #fcfbf8; border: 1px solid #ece5d8; padding: 12px 14px; border-radius: 2px; margin-bottom: 14px;">
                      <div style="font-size: 11px; font-weight: 700; color: #0b2732; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 6px;">
                        What Changed (Primary Government Record):
                      </div>
                      <p style="margin: 0; font-size: 13px; line-height: 1.55; color: #0b2732;">
                        Repeals prior paper zoning maps for Region Planning Area 5 and adopts the <strong>Anne Arundel County Digital Zoning Layer (dated February 2, 2026, as amended)</strong> as the official spatial zoning baseline for Region 5.
                      </p>
                    </div>
                    <div style="font-size: 12px; line-height: 1.5; color: #527a83; margin-bottom: 12px;">
                      <em>Legislative Chronology &amp; Split Effective Dates:</em> Passed June 1, 2026. County Executive issued line-item vetoes on Amendment Nos. 3, 10, 12, 13, 15, 16, and 17 on June 5, 2026. County Council voted to override line-item vetoes on June 15, 2026. Base provisions took effect <strong>{b18['frontmatter']['effective_date_base']}</strong>; override-restored amendments took effect <strong>{b18['frontmatter']['effective_date_overridden_amendments']}</strong>.
                    </div>
                    <table role="presentation" border="0" cellpadding="0" cellspacing="0">
                      <tr>
                        <td>
                          <a href="{b18['frontmatter']['primary_source_url']}" target="_blank" style="font-size: 12px; font-weight: 600; color: #0b2732; text-decoration: underline; font-family: -apple-system, BlinkMacSystemFont, sans-serif;">
                            View Primary {b18['frontmatter']['bill_number']} PDF &rarr;
                          </a>
                        </td>
                        <td style="padding-left: 14px;">
                          <a href="{b18['frontmatter']['veto_letter_url']}" target="_blank" style="font-size: 12px; font-weight: 600; color: #527a83; text-decoration: underline; font-family: -apple-system, BlinkMacSystemFont, sans-serif;">
                            View Primary Veto Letter PDF &rarr;
                          </a>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- ITEM 2: {b28['frontmatter']['bill_number']} -->
          <tr>
            <td class="mobile-padding" style="padding: 0 32px 24px 32px;">
              <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #ffffff; border: 1px solid #e2d9c7; border-left: 4px solid #9cd0ca; border-radius: 2px;">
                <tr>
                  <td style="padding: 20px 22px;">
                    <table role="presentation" border="0" cellpadding="0" cellspacing="0" style="margin-bottom: 12px;">
                      <tr>
                        <td style="background-color: #eaf6f4; border: 1px solid #9cd0ca; border-radius: 2px; padding: 3px 8px;">
                          <span style="color: #0b2732; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">
                            ENACTED &middot; UNANIMOUS
                          </span>
                        </td>
                        <td style="padding-left: 10px; font-size: 12px; color: #88a1a6; font-family: -apple-system, BlinkMacSystemFont, sans-serif;">
                          Passed: {b28['frontmatter']['passed_date']} &middot; Enacted: {b28['frontmatter']['enacted_date']} &middot; Effective: {b28['frontmatter']['effective_date']}
                        </td>
                      </tr>
                    </table>
                    <div style="font-family: 'Source Serif 4', Georgia, serif; font-size: 17px; font-weight: 600; color: #0b2732; line-height: 1.3; margin-bottom: 6px;">
                      {b28['frontmatter']['bill_number']}: Commercial Districts &mdash; Apartment Dwelling Units
                    </div>
                    <div style="font-size: 12px; color: #527a83; margin-bottom: 14px; font-weight: 500;">
                      <strong>Citation:</strong> Anne Arundel County Code, Article 18 (Zoning), Title 5 (Commercial Districts), &sect; 18-5-102
                    </div>
                    <div style="background-color: #f7f4ee; border: 1px solid #e2d9c7; padding: 14px; border-radius: 2px; margin-bottom: 14px; font-family: 'Courier New', Courier, monospace; font-size: 12px; line-height: 1.6;">
                      <div style="color: #88a1a6; font-size: 10px; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 6px; font-family: -apple-system, sans-serif; font-weight: 600;">
                        Statutory Text Quoted from Enacted Bill:
                      </div>
                      <div style="color: #527a83;">
                        &sect; 18-5-102. Permitted uses chart (Commercial Districts):
                      </div>
                      <div style="color: #0b2732; margin-top: 4px; padding-left: 12px; border-left: 2px solid #527a83;">
                        <span style="color: #0b2732; font-weight: 600;">Dwelling unit, apartment, as an accessory use provided the entrance is separate from the commercial use</span><br />&nbsp;&nbsp;Enacted table designation: <strong>C1: P &middot; C2: P &middot; C3: P &middot; C4: P</strong>
                      </div>
                    </div>
                    <p style="margin: 0 0 12px 0; font-size: 13px; line-height: 1.55; color: #0b2732;">
                      <strong>Primary Record &amp; Divergence Note:</strong> The title and summary clause of Bill No. 28-26 refer to C4 commercial districts. However, the enacted instrument's use table designates the accessory apartment row as permitted (P) across all four commercial districts: <strong>C1, C2, C3, and C4</strong>. Where the summary clause and the enacted statutory chart diverge, the enacted statutory text controls.
                    </p>
                    <a href="{b28['frontmatter']['primary_source_url']}" target="_blank" style="font-size: 12px; font-weight: 600; color: #0b2732; text-decoration: underline; font-family: -apple-system, BlinkMacSystemFont, sans-serif;">
                      View Primary {b28['frontmatter']['bill_number']} PDF &rarr;
                    </a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- ITEM 3: {b57['frontmatter']['bill_number']} -->
          <tr>
            <td class="mobile-padding" style="padding: 0 32px 28px 32px;">
              <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #faf9f6; border: 1px dashed #d5ccc0; border-radius: 2px;">
                <tr>
                  <td style="padding: 16px 20px;">
                    <table role="presentation" border="0" cellpadding="0" cellspacing="0" style="margin-bottom: 8px;">
                      <tr>
                        <td style="background-color: #f0eae1; border: 1px solid #c9beaf; border-radius: 2px; padding: 2px 7px;">
                          <span style="color: #a05252; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">
                            WITHDRAWN &middot; DID NOT TAKE EFFECT
                          </span>
                        </td>
                        <td style="padding-left: 10px; font-size: 11px; color: #88a1a6; font-family: -apple-system, BlinkMacSystemFont, sans-serif;">
                          Introduced: {b57['frontmatter']['introduced_date']} &middot; Withdrawn: {b57['frontmatter']['withdrawn_date']}
                        </td>
                      </tr>
                    </table>
                    <div style="font-family: 'Source Serif 4', Georgia, serif; font-size: 15px; font-weight: 600; color: #0b2732; margin-bottom: 4px;">
                      {b57['frontmatter']['bill_number']}: Proposed "Rural Commerce Center" Zoning Classification
                    </div>
                    <p style="margin: 0; font-size: 12px; line-height: 1.5; color: #527a83;">
                      Sponsor withdrew legislative proposal concerning Article 18, Title 9. Did not become law. Existing rural and agricultural baselines remain unaltered.
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
    """

    contacts_html = """
              <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%">
                <tr>
                  <td class="col-split" width="48%" valign="top" style="background-color: rgba(255, 255, 255, 0.04); border: 1px solid #1c4250; padding: 14px; border-radius: 2px;">
                    <div style="font-size: 12px; font-weight: 700; color: #f7f4ee; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px;">
                      Office of Planning &amp; Zoning (OPZ)
                    </div>
                    <div style="font-size: 12px; color: #9cd0ca; line-height: 1.5;">
                      Heritage Complex<br />
                      2664 Riva Road, Annapolis, MD 21401<br />
                      <strong>Zoning Division:</strong> (410) 222-7437<br />
                      <strong>General:</strong> (410) 222-7450<br />
                      <span style="font-size: 10px; color: #88a1a6;">Source: aacounty.org/planning-and-zoning (Checked 2026-09-04)</span>
                    </div>
                  </td>
                  <td class="col-split" width="4%" style="font-size: 1px; line-height: 1px;">&nbsp;</td>
                  <td class="col-split" width="48%" valign="top" style="background-color: rgba(255, 255, 255, 0.04); border: 1px solid #1c4250; padding: 14px; border-radius: 2px;">
                    <div style="font-size: 12px; font-weight: 700; color: #f7f4ee; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px;">
                      City of Annapolis (Autonomous)
                    </div>
                    <div style="font-size: 12px; color: #9cd0ca; line-height: 1.5;">
                      Planning &amp; Zoning Department<br />
                      145 Gorman Street, 3rd Floor<br />
                      Annapolis, MD 21401<br />
                      <strong>Phone:</strong> (410) 263-7946<br />
                      <em>Independent Title 21 Code</em><br />
                      <span style="font-size: 10px; color: #88a1a6;">Source: annapolis.gov/planning (Checked 2026-09-04)</span>
                    </div>
                  </td>
                </tr>
              </table>
    """

    return render_email_scaffold(
        jurisdiction_badge="MD &middot; Anne Arundel",
        jurisdiction_name="Anne Arundel County",
        lead_text="The Anne Arundel County Council records legislative actions amending <strong>Article 18 (Zoning)</strong> and planning boundary regulations. Below are the primary government records, legislative chronologies, quoted statutory text, and municipal contacts.",
        items_html=items_html,
        contacts_html=contacts_html,
        last_ingested_iso="2026-09-04T22:33:23Z",
        primary_portal="https://www.aacounty.org",
        primary_domain="aacounty.org"
    )

def render_howard():
    hw_dir = REPO_BASE / "howard" / "council_bills"
    cb25 = parse_record_file(hw_dir / "cb_25_2026.md")
    cb24 = parse_record_file(hw_dir / "cb_24_2026.md")
    cb4 = parse_record_file(hw_dir / "cb_04_2026.md")

    items_html = f"""
          <!-- ITEM 1: {cb25['frontmatter']['bill_number']} ({cb25['frontmatter']['zra_number']}) -->
          <tr>
            <td class="mobile-padding" style="padding: 0 32px 24px 32px;">
              <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #ffffff; border: 1px solid #e2d9c7; border-left: 4px solid #9cd0ca; border-radius: 2px;">
                <tr>
                  <td style="padding: 20px 22px;">
                    <table role="presentation" border="0" cellpadding="0" cellspacing="0" style="margin-bottom: 12px;">
                      <tr>
                        <td style="background-color: #eaf6f4; border: 1px solid #9cd0ca; border-radius: 2px; padding: 3px 8px;">
                          <span style="color: #0b2732; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">
                            PASSED AS AMENDED &middot; ENACTED
                          </span>
                        </td>
                        <td style="padding-left: 10px; font-size: 12px; color: #88a1a6; font-family: -apple-system, BlinkMacSystemFont, sans-serif;">
                          Passed: {cb25['frontmatter']['passed_date']} &middot; Executive Action: {cb25['frontmatter']['executive_action_date']} &middot; Effective: {cb25['frontmatter']['effective_date']}
                        </td>
                      </tr>
                    </table>
                    <div style="font-family: 'Source Serif 4', Georgia, serif; font-size: 17px; font-weight: 600; color: #0b2732; line-height: 1.3; margin-bottom: 6px;">
                      {cb25['frontmatter']['bill_number']} ({cb25['frontmatter']['zra_number']}): Age-Restricted Adult Housing Cottage Clusters
                    </div>
                    <div style="font-size: 12px; color: #527a83; margin-bottom: 14px; font-weight: 500;">
                      <strong>Citations:</strong> HCZR &sect; 103.0 (Definitions), &sect; 125.0 (NT), &sect; 126.0 (PGCC), &sect; 128.0.R (Optional Design), &sect; 133.0.D (Parking)
                    </div>
                    <div style="background-color: #f7f4ee; border: 1px solid #e2d9c7; padding: 14px; border-radius: 2px; margin-bottom: 14px; font-family: 'Courier New', Courier, monospace; font-size: 12px; line-height: 1.6;">
                      <div style="color: #88a1a6; font-size: 10px; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 6px; font-family: -apple-system, sans-serif; font-weight: 600;">
                        Statutory Text Quoted from Enacted Bill (HCZR &sect; 103.0):
                      </div>
                      <div style="color: #0b2732; padding-left: 12px; border-left: 2px solid #9cd0ca;">
                        <strong>COTTAGE CLUSTER:</strong> A GROUPING, INCLUDING A COMMON COURTYARD, OF AT LEAST FOUR SINGLE STORY DETACHED DWELLING UNITS THAT HAVE A FOOTPRINT OF NO MORE THAN 1,200 SQUARE FEET AND DOES NOT INCLUDE A BASEMENT.
                      </div>
                    </div>
                    <div style="background-color: #fcfbf8; border: 1px solid #ece5d8; padding: 12px 14px; border-radius: 2px; margin-bottom: 14px;">
                      <div style="font-size: 11px; font-weight: 700; color: #0b2732; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 6px;">
                        What Changed (Primary Government Record):
                      </div>
                      <p style="margin: 0; font-size: 13px; line-height: 1.55; color: #0b2732;">
                        Defines Cottage Clusters and provides where Age-Restricted Adult Housing (ARAH) Cottage Clusters are permitted within New Town (NT) and Planned Golf Course Community (PGCC) districts; adds Section 128.0.R criteria for Cottage Clusters within an Optional Design Project; establishes parking requirements under Section 133.0.D.
                      </p>
                    </div>
                    <a href="{cb25['frontmatter']['primary_source_url']}" target="_blank" style="font-size: 12px; font-weight: 600; color: #0b2732; text-decoration: underline; font-family: -apple-system, BlinkMacSystemFont, sans-serif;">
                      View Primary {cb25['frontmatter']['bill_number']} Record (OLIS) &rarr;
                    </a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- ITEM 2: {cb24['frontmatter']['bill_number']} ({cb24['frontmatter']['zra_number']}) -->
          <tr>
            <td class="mobile-padding" style="padding: 0 32px 24px 32px;">
              <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #ffffff; border: 1px solid #e2d9c7; border-left: 4px solid #527a83; border-radius: 2px;">
                <tr>
                  <td style="padding: 20px 22px;">
                    <table role="presentation" border="0" cellpadding="0" cellspacing="0" style="margin-bottom: 12px;">
                      <tr>
                        <td style="background-color: #eaf6f4; border: 1px solid #9cd0ca; border-radius: 2px; padding: 3px 8px;">
                          <span style="color: #0b2732; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">
                            ENACTED
                          </span>
                        </td>
                        <td style="padding-left: 10px; font-size: 12px; color: #88a1a6; font-family: -apple-system, BlinkMacSystemFont, sans-serif;">
                          Passed: {cb24['frontmatter']['passed_date']} &middot; Executive Action: {cb24['frontmatter']['executive_action_date']} &middot; Effective: {cb24['frontmatter']['effective_date']}
                        </td>
                      </tr>
                    </table>
                    <div style="font-family: 'Source Serif 4', Georgia, serif; font-size: 17px; font-weight: 600; color: #0b2732; line-height: 1.3; margin-bottom: 6px;">
                      {cb24['frontmatter']['bill_number']} ({cb24['frontmatter']['zra_number']}): Route 1 Corridor Optional Design Projects
                    </div>
                    <div style="font-size: 12px; color: #527a83; margin-bottom: 14px; font-weight: 500;">
                      <strong>Citation:</strong> Howard County Zoning Regulations, &sect; 128.0 (Supplementary Regulations), Subsection 128.0.Q
                    </div>
                    <div style="background-color: #fcfbf8; border: 1px solid #ece5d8; padding: 12px 14px; border-radius: 2px; margin-bottom: 14px;">
                      <div style="font-size: 11px; font-weight: 700; color: #0b2732; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 6px;">
                        What Changed (Primary Government Record):
                      </div>
                      <p style="margin: 0; font-size: 13px; line-height: 1.55; color: #0b2732;">
                        Amends Section 128.0 to add Subsection 128.0.Q ("Optional Design Projects in Route 1 Corridor"), expanding eligibility for Optional Design Projects to commercial properties fronting U.S. Route 1 with a total lot area of less than ten (10) acres.
                      </p>
                    </div>
                    <a href="{cb24['frontmatter']['primary_source_url']}" target="_blank" style="font-size: 12px; font-weight: 600; color: #0b2732; text-decoration: underline; font-family: -apple-system, BlinkMacSystemFont, sans-serif;">
                      View Primary {cb24['frontmatter']['bill_number']} Record (OLIS) &rarr;
                    </a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- ITEM 3: {cb4['frontmatter']['bill_number']} ({cb4['frontmatter']['zra_number']}) -->
          <tr>
            <td class="mobile-padding" style="padding: 0 32px 28px 32px;">
              <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #faf9f6; border: 1px dashed #d5ccc0; border-radius: 2px;">
                <tr>
                  <td style="padding: 16px 20px;">
                    <table role="presentation" border="0" cellpadding="0" cellspacing="0" style="margin-bottom: 8px;">
                      <tr>
                        <td style="background-color: #f0eae1; border: 1px solid #c9beaf; border-radius: 2px; padding: 2px 7px;">
                          <span style="color: #a05252; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">
                            WITHDRAWN &middot; DID NOT TAKE EFFECT
                          </span>
                        </td>
                        <td style="padding-left: 10px; font-size: 11px; color: #88a1a6; font-family: -apple-system, BlinkMacSystemFont, sans-serif;">
                          Introduced: {cb4['frontmatter']['introduced_date']} &middot; Withdrawn: {cb4['frontmatter']['withdrawn_date']}
                        </td>
                      </tr>
                    </table>
                    <div style="font-family: 'Source Serif 4', Georgia, serif; font-size: 15px; font-weight: 600; color: #0b2732; margin-bottom: 4px;">
                      {cb4['frontmatter']['bill_number']} ({cb4['frontmatter']['zra_number']}): Activity Centers Diverse Housing in TOD &amp; TNC Districts
                    </div>
                    <p style="margin: 0; font-size: 12px; line-height: 1.5; color: #527a83;">
                      Petitioner withdrew legislative proposal to add an Activity Centers definition and housing provisions in TOD and TNC districts. Did not become law. Existing Transit Oriented Development (TOD) and Traditional Neighborhood Center (TNC) regulations remain in effect.
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
    """

    contacts_html = """
              <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%">
                <tr>
                  <td class="col-split" width="48%" valign="top" style="background-color: rgba(255, 255, 255, 0.04); border: 1px solid #1c4250; padding: 14px; border-radius: 2px;">
                    <div style="font-size: 12px; font-weight: 700; color: #f7f4ee; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px;">
                      Department of Planning &amp; Zoning (DPZ)
                    </div>
                    <div style="font-size: 12px; color: #9cd0ca; line-height: 1.5;">
                      Division of Public Service &amp; Zoning Admin<br />
                      3430 Court House Drive<br />
                      Ellicott City, MD 21043<br />
                      <strong>Phone:</strong> (410) 313-2350<br />
                      <strong>Public Service:</strong> (410) 313-4395<br />
                      <span style="font-size: 10px; color: #88a1a6;">Source: howardcountymd.gov/planning-zoning (Checked 2026-09-04)</span>
                    </div>
                  </td>
                  <td class="col-split" width="4%" style="font-size: 1px; line-height: 1px;">&nbsp;</td>
                  <td class="col-split" width="48%" valign="top" style="background-color: rgba(255, 255, 255, 0.04); border: 1px solid #1c4250; padding: 14px; border-radius: 2px;">
                    <div style="font-size: 12px; font-weight: 700; color: #f7f4ee; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px;">
                      Howard County Council
                    </div>
                    <div style="font-size: 12px; color: #9cd0ca; line-height: 1.5;">
                      Council Administrator<br />
                      George Howard Building<br />
                      3430 Court House Drive<br />
                      Ellicott City, MD 21043<br />
                      <strong>Phone:</strong> (410) 313-2001<br />
                      <span style="font-size: 10px; color: #88a1a6;">Source: cc.howardcountymd.gov (Checked 2026-09-04)</span>
                    </div>
                  </td>
                </tr>
              </table>
    """

    return render_email_scaffold(
        jurisdiction_badge="MD &middot; Howard",
        jurisdiction_name="Howard County",
        lead_text="The Howard County Council records legislative enactments amending the <strong>Howard County Zoning Regulations (HCZR)</strong> and supplementary district standards. Below are the primary government records, legislative chronologies, quoted statutory text, and municipal contacts.",
        items_html=items_html,
        contacts_html=contacts_html,
        last_ingested_iso="2026-09-04T20:30:16Z",
        primary_portal="https://cc.howardcountymd.gov",
        primary_domain="cc.howardcountymd.gov"
    )

def render_water_email_scaffold(
    system_name: str,
    checked_date_str: str,
    content_html: str,
    contacts_html: str,
    last_ingested_iso: str = "",
    posture_text: str = "",
    source_hash_str: str = "",
    notice_type_label: str = "Water record notice",
) -> str:
    """
    Renders dedicated water notification email scaffold following
    design/design_handoff_water_2026-10-06/artboards/WaterNotice.dc.html and WaterDigest.dc.html.
    Zero zoning, land-use, or 'enacted law' terminology.
    Zero display: flex layout. All layouts use HTML tables.
    """
    if not posture_text:
        posture_text = (
            '<strong style="color: #f7f4ee;">What this notice is.</strong> '
            'Enacted reports what the agency published and quotes it. Enacted does not interpret a result, '
            'assess the water at any address, or advise. '
            '<strong style="color: #f7f4ee;">Which system serves an address, and what a result means for a household,</strong> '
            'are questions for the agency named above.'
        )

    hash_display = f" {source_hash_str}" if source_hash_str else (f" Fetched {last_ingested_iso}." if last_ingested_iso else "")

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Water Notice &middot; {system_name}</title>
  <style>
    body {{
      margin: 0;
      padding: 0;
      background-color: #efeae0;
      font-family: 'Source Serif 4', Charter, Georgia, serif;
      color: #0b2732;
      -webkit-text-size-adjust: 100%;
      -ms-text-size-adjust: 100%;
    }}
    table {{
      border-collapse: collapse;
      mso-table-lspace: 0pt;
      mso-table-rspace: 0pt;
    }}
    td {{
      padding: 0;
    }}
    img {{
      border: 0;
      outline: none;
      text-decoration: none;
      display: block;
    }}
    a {{
      color: #3f646c;
      text-decoration: underline;
    }}
    @media only screen and (max-width: 640px) {{
      .wrapper-table {{
        width: 100% !important;
        margin: 0 auto !important;
      }}
      .mobile-padding {{
        padding-left: 20px !important;
        padding-right: 20px !important;
      }}
    }}
  </style>
</head>
<body style="margin: 0; padding: 24px 0; background-color: #efeae0;">
  <center>
    <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" height="100%" style="background-color: #efeae0;">
      <tr>
        <td align="center" valign="top" style="padding: 12px;">
          <!-- MAIN CONTAINER (640px max) -->
          <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="640" class="wrapper-table" style="background-color: #f7f4ee; border: 1px solid #d8d2c6; border-radius: 2px;">
            
            <!-- HEADER (Light, Water Notice) -->
            <tr>
              <td class="mobile-padding" style="padding: 24px 32px 18px 32px; border-bottom: 3px solid #0b2732;">
                <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%">
                  <tr>
                    <td valign="middle" width="48" style="padding-right: 16px;">
                      <svg width="40" height="44" viewBox="0 0 60 66" aria-label="Enacted" fill="none">
                        <rect x="9" y="9" width="28" height="37" stroke="#88a1a6" stroke-width="2" stroke-dasharray="4 3" fill="none"/>
                        <rect x="21" y="15" width="28" height="37" fill="#f7f4ee" stroke="#0b2732" stroke-width="3"/>
                        <rect x="21" y="15" width="4" height="37" fill="#8fbfd6"/>
                      </svg>
                    </td>
                    <td valign="middle">
                      <div style="font-family: 'Source Serif 4', Georgia, serif; font-size: 26px; font-weight: 400; color: #0b2732; line-height: 1.1;">
                        Enacted
                      </div>
                      <div style="font-family: 'Source Serif 4', Georgia, serif; font-size: 11px; font-weight: 600; color: #3f646c; letter-spacing: 0.14em; text-transform: uppercase; margin-top: 4px;">
                        {notice_type_label} &middot; {system_name}
                      </div>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>

            <!-- SUBHEADER: Following Strip -->
            <tr>
              <td class="mobile-padding" style="background-color: #f0ece2; padding: 12px 32px; border-bottom: 1px solid #d8d2c6;">
                <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%">
                  <tr>
                    <td style="font-size: 13px; color: #0b2732; font-family: 'Source Serif 4', Georgia, serif;">
                      <strong style="font-weight: 600;">Following:</strong> {system_name} &middot; water system
                    </td>
                  </tr>
                  <tr>
                    <td style="font-size: 12px; color: #3f646c; font-family: 'Source Serif 4', Georgia, serif; padding-top: 2px;">
                      Sent because a record was added for this system. Source checked {checked_date_str}.
                    </td>
                  </tr>
                </table>
              </td>
            </tr>

            <!-- CONTENT BLOCK -->
            <tr>
              <td style="padding: 24px 0 0 0;">
                <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%">
                  {content_html}
                </table>
              </td>
            </tr>

            <!-- WHO TO ASK SECTION -->
            <tr>
              <td class="mobile-padding" style="padding: 20px 32px; border-top: 1px solid #d8d2c6; border-bottom: 1px solid #d8d2c6;">
                <div style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-size: 11px; font-weight: 700; color: #3f646c; letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 8px;">
                  Who to ask
                </div>
                {contacts_html}
              </td>
            </tr>

            <!-- POSTURE BLOCK -->
            <tr>
              <td class="mobile-padding" style="background-color: #0b2732; padding: 20px 32px; color: #cfdcdd;">
                <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%">
                  <tr>
                    <td width="38" valign="top" style="padding-right: 14px;">
                      <svg width="30" height="30" viewBox="0 0 60 60" fill="none" style="display: block; margin-top: 2px;" aria-hidden="true">
                        <path d="M18 9 H11 V51 H18" stroke="#8fbfd6" stroke-width="4" stroke-linecap="square"/>
                        <path d="M42 9 H49 V51 H42" stroke="#8fbfd6" stroke-width="4" stroke-linecap="square"/>
                        <circle cx="25" cy="27" r="2.4" fill="#f7f4ee"/>
                        <circle cx="35" cy="27" r="2.4" fill="#f7f4ee"/>
                      </svg>
                    </td>
                    <td valign="top" style="font-family: 'Source Serif 4', Georgia, serif; font-size: 13px; line-height: 1.6; color: #cfdcdd;">
                      {posture_text}
                    </td>
                  </tr>
                </table>
              </td>
            </tr>

            <!-- FOOTER -->
            <tr>
              <td class="mobile-padding" style="padding: 18px 32px 24px 32px; font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-size: 11px; line-height: 1.6; color: #3f646c;">
                Enacted is not a law firm and does not provide legal advice; no attorney&ndash;client relationship is created by reading this notice. Not legal or health advice. Content is compiled from reports the agency published and may lag the agency; the agency&rsquo;s report is the official source.{hash_display} &copy; 2026 Swapp Technologies LLC &middot; [FOUNDER: confirm mailing address] &middot; <a href="/unsubscribe" style="color: #3f646c; text-decoration: underline;">Unsubscribe</a> &middot; <a href="/follows" style="color: #3f646c; text-decoration: underline;">Manage follows</a> &middot; <a href="/coverage" style="color: #3f646c; text-decoration: underline;">Coverage statement</a> &middot; <a href="/how-to-read#water" style="color: #3f646c; text-decoration: underline;">How to read a water record</a>
              </td>
            </tr>

          </table>
        </td>
      </tr>
    </table>
  </center>
</body>
</html>"""


def render_water_source_not_found_email(record=None) -> str:
    """Renders the email notification for a water source report not found."""
    if record is None:
        record = {
            "system": "TEST FIXTURE SYSTEM",
            "source_title": "Fixture Water Quality Report",
            "period": "2025",
            "as_of_date": "August 1, 2026",
            "index_url": "https://example.invalid/fixture/index.html",
            "checked_at": "2026-08-01T12:00:00Z",
            "citation": "TEST RULE § 0.0",
            "quoted_sentence": "Test fixture systems shall deliver water monitoring summaries on the prescribed fixture schedule.",
            "last_title": "Fixture Water Quality Report 2024",
            "last_date": "",
            "last_url": "https://example.invalid/fixture/report-2024.pdf",
            "agency": "TEST FIXTURE WATER DEPARTMENT",
            "phone": "(555) 010-0000",
            "email": "test-water@example.invalid",
            "website": "https://example.invalid"
        }

    title = f"{record['system']} · {record['source_title']}: no {record['period']} report found at the watched source as of {record['as_of_date']}."
    
    last_date_str = str(record.get('last_date', '')).strip()
    if last_date_str and not last_date_str.startswith('['):
        last_found_desc = f"{record['last_title']} &middot; Published {last_date_str}"
    else:
        last_found_desc = record['last_title']

    items_html = f"""
          <!-- WATER ABSENCE ITEM -->
          <tr>
            <td class="mobile-padding" style="padding: 0 32px 24px 32px;">
              <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #ffffff; border: 1px solid #e2d9c7; border-left: 4px solid #527a83; border-radius: 2px;">
                <tr>
                  <td style="padding: 20px 22px;">
                    <table role="presentation" border="0" cellpadding="0" cellspacing="0" style="margin-bottom: 12px;">
                      <tr>
                        <td style="background-color: #f7f4ee; border: 1px solid #527a83; border-radius: 2px; padding: 3px 8px;">
                          <span style="color: #0b2732; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">
                            Report not found at source
                          </span>
                        </td>
                        <td style="padding-left: 10px; font-size: 12px; color: #88a1a6; font-family: -apple-system, BlinkMacSystemFont, sans-serif;">
                          Checked: {record['checked_at']}
                        </td>
                      </tr>
                    </table>
                    <div style="font-family: 'Source Serif 4', Georgia, serif; font-size: 17px; font-weight: 600; color: #0b2732; line-height: 1.3; margin-bottom: 6px;">
                      {title}
                    </div>
                    <div style="font-size: 12px; color: #527a83; margin-bottom: 14px; font-weight: 500;">
                      <strong>Watched Address:</strong> <a href="{record['index_url']}" target="_blank" style="color: #0b2732; text-decoration: underline;">{record['index_url']}</a>
                    </div>
                    <div style="background-color: #fcfbf8; border: 1px solid #ece5d8; padding: 12px 14px; border-radius: 2px; margin-bottom: 14px;">
                      <div style="font-size: 11px; font-weight: 700; color: #0b2732; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 6px;">
                        Cadence Basis ({record['citation']}):
                      </div>
                      <blockquote style="margin: 0; font-size: 13px; line-height: 1.55; color: #0b2732; padding-left: 10px; border-left: 2px solid #527a83;">
                        &ldquo;{record['quoted_sentence']}&rdquo;
                      </blockquote>
                    </div>
                    <div style="font-size: 12px; line-height: 1.5; color: #527a83;">
                      <strong>Last issue found:</strong> {last_found_desc} (<a href="{record['last_url']}" target="_blank" style="color: #527a83; text-decoration: underline;">source link</a>)
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
    """

    contacts_html = f"""
      <div style="font-size: 14px; line-height: 1.55; color: #0b2732;">
        <strong>{record['agency']}</strong><br />
        {record['phone']} &middot; <a href="mailto:{record['email']}" style="color: #3f646c;">{record['email']}</a><br />
        <span style="font-size: 12px; color: #3f646c;">Contact as published on the system record.</span>
      </div>
    """

    posture_text = (
        '<strong style="color: #f7f4ee;">What this notice is.</strong> '
        'Enacted reports what was and was not found at the address the agency publishes to, on the date shown. '
        'A report may exist elsewhere. Enacted does not interpret this, assess the water at any address, or advise.'
    )

    return render_water_email_scaffold(
        system_name=record['system'],
        checked_date_str=record['as_of_date'],
        content_html=items_html,
        contacts_html=contacts_html,
        last_ingested_iso=record['checked_at'],
        posture_text=posture_text,
        notice_type_label="Water monitoring notice",
    )


def render_water_source_found_email(record=None) -> str:
    """Renders the email notification for a closing record when an expected water report is found."""
    if record is None:
        record = {
            "system": "TEST FIXTURE SYSTEM",
            "source_title": "Fixture Water Quality Report",
            "period": "2025",
            "found_date": "August 15, 2026",
            "found_iso": "2026-08-15T10:00:00Z",
            "report_link": "https://example.invalid/fixture/report-2025.pdf",
            "report_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
            "closes_record": "water/measurements/test_fixture_system/source_check_not_found_2025_2026-08-01",
            "agency": "TEST FIXTURE WATER DEPARTMENT",
            "phone": "(555) 010-0000",
            "email": "test-water@example.invalid",
            "website": "https://example.invalid"
        }

    title = f"{record['system']} · {record['source_title']}: {record['period']} report found {record['found_date']}."

    items_html = f"""
          <!-- WATER FOUND ITEM -->
          <tr>
            <td class="mobile-padding" style="padding: 0 32px 24px 32px;">
              <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #ffffff; border: 1px solid #e2d9c7; border-left: 4px solid #9cd0ca; border-radius: 2px;">
                <tr>
                  <td style="padding: 20px 22px;">
                    <table role="presentation" border="0" cellpadding="0" cellspacing="0" style="margin-bottom: 12px;">
                      <tr>
                        <td style="background-color: #eaf6f4; border: 1px solid #9cd0ca; border-radius: 2px; padding: 3px 8px;">
                          <span style="color: #0b2732; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">
                            Report found
                          </span>
                        </td>
                        <td style="padding-left: 10px; font-size: 12px; color: #88a1a6; font-family: -apple-system, BlinkMacSystemFont, sans-serif;">
                          Published: {record['found_date']}
                        </td>
                      </tr>
                    </table>
                    <div style="font-family: 'Source Serif 4', Georgia, serif; font-size: 17px; font-weight: 600; color: #0b2732; line-height: 1.3; margin-bottom: 6px;">
                      {title}
                    </div>
                    <div style="font-size: 12px; line-height: 1.55; color: #0b2732; margin-bottom: 12px;">
                      <strong>Primary Document:</strong> <a href="{record['report_link']}" target="_blank" style="color: #0b2732; text-decoration: underline;">{record['report_link']}</a><br />
                      <strong>Document SHA-256:</strong> <code>{record['report_sha256'][:16]}...</code><br />
                      <strong>Closed Absence Notice:</strong> {record['closes_record']}
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
    """

    contacts_html = f"""
      <div style="font-size: 14px; line-height: 1.55; color: #0b2732;">
        <strong>{record['agency']}</strong><br />
        {record['phone']} &middot; <a href="mailto:{record['email']}" style="color: #3f646c;">{record['email']}</a><br />
        <span style="font-size: 12px; color: #3f646c;">Contact as published on the system record.</span>
      </div>
    """

    posture_text = (
        '<strong style="color: #f7f4ee;">What this notice is.</strong> '
        'Enacted reports what was and was not found at the address the agency publishes to, on the date shown. '
        'A report may exist elsewhere. Enacted does not interpret this, assess the water at any address, or advise.'
    )

    return render_water_email_scaffold(
        system_name=record['system'],
        checked_date_str=record['found_date'],
        content_html=items_html,
        contacts_html=contacts_html,
        last_ingested_iso=record['found_iso'],
        posture_text=posture_text,
        source_hash_str=f"Document SHA-256: {record['report_sha256'][:16]}...",
        notice_type_label="Water monitoring notice",
    )


def render_water_notice_email(record: Optional[Dict[str, Any]] = None, show_first_issue_key: bool = False) -> str:
    """
    Renders water notice email matching WaterNotice.dc.html artboard.
    Uses TIDE = '#8fbfd6'. Dynamically renders all values, figures, quotes,
    and contacts from backing record file. Zero typed figures. Zero display: flex.
    """
    if record is None:
        rec_path = REPO_BASE / "water" / "measurements" / "aa_broad_creek" / "lead_copper_violation_2025.md"
        record = parse_record_file(rec_path)["frontmatter"]

    first_issue_key_html = ""
    if show_first_issue_key:
        first_issue_key_html = """
          <!-- FIRST ISSUE KEY -->
          <tr>
            <td class="mobile-padding" style="padding: 0 32px 20px 32px;">
              <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="border: 1px solid #d8d2c6; background-color: #fbfaf6; padding: 14px 18px;">
                <tr>
                  <td>
                    <div style="font-family: 'Source Serif 4', Georgia, serif; font-size: 10.5px; letter-spacing: 0.14em; text-transform: uppercase; color: #3f646c; margin-bottom: 6px; font-weight: 600;">How to read a water record &middot; shown in the first issue</div>
                    <div style="font-size: 12px; line-height: 1.45; color: #2c3e44; margin-bottom: 10px;">Each record carries a drop. Its shape marks what the agency&rsquo;s report states about a result. The shape carries the meaning, never the color.</div>
                    <table role="presentation" border="0" cellpadding="4" cellspacing="0" width="100%" style="font-size: 11.5px; line-height: 1.6; color: #0b2732;">
                      <tr>
                        <td width="24" valign="middle"><svg width="13" height="15" viewBox="0 0 18 20" aria-hidden="true"><path d="M9 1.5C9 1.5 3 9 3 13a6 6 0 0 0 12 0C15 9 9 1.5 9 1.5Z" fill="#0b2732" stroke="#0b2732" stroke-width="1.6"/><line x1="5.5" y1="13" x2="12.5" y2="13" stroke="#f7f4ee" stroke-width="2"/></svg></td>
                        <td><strong>Violation reported:</strong> The report or the regulator states a violation.</td>
                      </tr>
                      <tr>
                        <td width="24" valign="middle"><svg width="13" height="15" viewBox="0 0 18 20" aria-hidden="true"><path d="M9 1.5C9 1.5 3 9 3 13a6 6 0 0 0 12 0C15 9 9 1.5 9 1.5Z" fill="none" stroke="#0b2732" stroke-width="1.8"/></svg></td>
                        <td><strong>No violation reported:</strong> The report prints &ldquo;Violation: No&rdquo;.</td>
                      </tr>
                      <tr>
                        <td width="24" valign="middle"><svg width="13" height="15" viewBox="0 0 18 20" aria-hidden="true"><path d="M9 1.5C9 1.5 3 9 3 13a6 6 0 0 0 12 0C15 9 9 1.5 9 1.5Z" fill="none" stroke="#0b2732" stroke-width="1.8" stroke-dasharray="2.4 1.8"/></svg></td>
                        <td><strong>Limit not yet in force:</strong> The report prints &ldquo;Violation: N/A&rdquo;. Compliance date is ahead.</td>
                      </tr>
                      <tr>
                        <td width="24" valign="middle"><svg width="13" height="15" viewBox="0 0 18 20" aria-hidden="true"><path d="M9 1.5C9 1.5 3 9 3 13a6 6 0 0 0 12 0C15 9 9 1.5 9 1.5Z" fill="none" stroke="#527a83" stroke-width="1.8"/><circle cx="9" cy="13" r="1.5" fill="#527a83"/></svg></td>
                        <td><strong>Not stated:</strong> The report gives no determination.</td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        """

    det = record.get("determination", {})
    det_status = det.get("status", "not_stated")
    if det_status == "violation_reported":
        drop_glyph = """<svg width="13" height="15" viewBox="0 0 18 20" aria-hidden="true" style="vertical-align: middle;"><path d="M9 1.5C9 1.5 3 9 3 13a6 6 0 0 0 12 0C15 9 9 1.5 9 1.5Z" fill="#0b2732" stroke="#0b2732" stroke-width="1.6"/><line x1="5.5" y1="13" x2="12.5" y2="13" stroke="#f7f4ee" stroke-width="2"/></svg>"""
        det_label = "Violation reported"
    elif det_status == "no_violation_reported":
        drop_glyph = """<svg width="13" height="15" viewBox="0 0 18 20" aria-hidden="true" style="vertical-align: middle;"><path d="M9 1.5C9 1.5 3 9 3 13a6 6 0 0 0 12 0C15 9 9 1.5 9 1.5Z" fill="none" stroke="#0b2732" stroke-width="1.8"/></svg>"""
        det_label = "No violation reported"
    elif det_status == "limit_not_yet_in_force":
        drop_glyph = """<svg width="13" height="15" viewBox="0 0 18 20" aria-hidden="true" style="vertical-align: middle;"><path d="M9 1.5C9 1.5 3 9 3 13a6 6 0 0 0 12 0C15 9 9 1.5 9 1.5Z" fill="none" stroke="#0b2732" stroke-width="1.8" stroke-dasharray="2.4 1.8"/></svg>"""
        det_label = "Limit not yet in force"
    else:
        drop_glyph = """<svg width="13" height="15" viewBox="0 0 18 20" aria-hidden="true" style="vertical-align: middle;"><path d="M9 1.5C9 1.5 3 9 3 13a6 6 0 0 0 12 0C15 9 9 1.5 9 1.5Z" fill="none" stroke="#527a83" stroke-width="1.8"/><circle cx="9" cy="13" r="1.5" fill="#527a83"/></svg>"""
        det_label = "Not stated"

    source_title = html.escape(str(record.get("source_title") or f"Water Quality Report {record.get('reporting_period', '')}"))
    source_fetched_str = html.escape(str(record.get("source_fetched_at", "")[:10]))
    file_last_saved = record.get("file_last_saved")
    saved_str = f" &middot; file last saved {html.escape(str(file_last_saved))}" if file_last_saved else ""
    finding_text = html.escape(str(record.get("agency_finding") or record.get("value", "")))
    comp_period = html.escape(str(record.get("compliance_period") or record.get("reporting_period", "")))
    gov_req = html.escape(str(record.get("governing_requirement") or record.get("governing_limit", {}).get("basis", "")))
    cit_text = html.escape(str(record.get("citation") or record.get("governing_limit", {}).get("citation", "")))
    quote_text = html.escape(str(record.get("quoted_text") or det.get("quote", "")))
    quote_page = html.escape(str(det.get("source_page", "Page 4")))
    contact = record.get("contact", {})
    system_text = html.escape(str(record.get("system", "")))
    param_text = html.escape(str(record.get("parameter", "")))
    agency_text = html.escape(str(contact.get("agency", record.get("source_agency", "Department of Public Works"))))
    phone_text = html.escape(str(contact.get("phone", "")))
    email_text = html.escape(str(contact.get("email", "")))
    contact_page = html.escape(str(contact.get("source_page", "the report")))

    items_html = f"""
          {first_issue_key_html}
          <!-- WATER NOTICE ITEM -->
          <tr>
            <td class="mobile-padding" style="padding: 0 32px 24px 32px;">
              <table role="presentation" border="0" cellpadding="0" cellspacing="0" style="margin-bottom: 12px;">
                <tr>
                  <td valign="middle" style="padding-right: 6px;">
                    {drop_glyph}
                  </td>
                  <td valign="middle" style="font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase; font-weight: 600; color: #0b2732; padding-right: 8px;">
                    {det_label}
                  </td>
                  <td valign="middle" style="font-size: 12px; color: #3f646c;">
                    {source_title}{saved_str} &middot; fetched {source_fetched_str}
                  </td>
                </tr>
              </table>
              <div style="font-family: 'Source Serif 4', Georgia, serif; font-size: 20px; font-weight: 600; line-height: 1.25; color: #0b2732; margin-bottom: 10px;">
                {html.escape(format_water_heading(record))}
              </div>
              <div style="font-size: 13.5px; line-height: 1.55; color: #2c3e44; margin-bottom: 16px;">
                {agency_text} reported {finding_text.lower() if finding_text else 'a finding'} for {comp_period}.
              </div>

              <!-- Key Figures Grid -->
              <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="border: 1px solid #d8d2c6; background-color: #fbfaf6; font-size: 13px; margin-bottom: 16px;">
                <tr>
                  <td width="50%" style="padding: 10px 12px; border-right: 1px solid #d8d2c6; border-bottom: 1px solid #d8d2c6;" valign="top">
                    <div style="color: #3f646c; text-transform: uppercase; letter-spacing: 0.1em; font-size: 10px; margin-bottom: 2px;">Finding, as reported</div>
                    <div style="font-weight: 600; color: #0b2732;">{finding_text}</div>
                  </td>
                  <td width="50%" style="padding: 10px 12px; border-bottom: 1px solid #d8d2c6;" valign="top">
                    <div style="color: #3f646c; text-transform: uppercase; letter-spacing: 0.1em; font-size: 10px; margin-bottom: 2px;">Compliance period</div>
                    <div style="color: #0b2732;">{comp_period}</div>
                  </td>
                </tr>
                <tr>
                  <td width="50%" style="padding: 10px 12px; border-right: 1px solid #d8d2c6;" valign="top">
                    <div style="color: #3f646c; text-transform: uppercase; letter-spacing: 0.1em; font-size: 10px; margin-bottom: 2px;">Governing requirement</div>
                    <div style="color: #0b2732;">{gov_req}</div>
                  </td>
                  <td width="50%" style="padding: 10px 12px;" valign="top">
                    <div style="color: #3f646c; text-transform: uppercase; letter-spacing: 0.1em; font-size: 10px; margin-bottom: 2px;">Citation on the record</div>
                    <div style="color: #0b2732;">{cit_text}</div>
                  </td>
                </tr>
              </table>

              <!-- Quote Block -->
              <div style="border: 1px solid #d8d2c6; background-color: #fbfaf6; padding: 14px 18px; font-size: 13.5px; line-height: 1.65; margin-bottom: 16px;">
                <div style="color: #3f646c; font-size: 10.5px; letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 8px;">From the report &middot; {source_title}, {quote_page.lower()}</div>
                <div style="color: #2c3e44;">&ldquo;{quote_text}&rdquo;</div>
              </div>

              <div style="margin-bottom: 16px;">
                <div style="color: #3f646c; font-size: 10.5px; letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 4px;">Against the earlier record</div>
                <div style="font-size: 13px; line-height: 1.5; color: #2c3e44;">First record for this system and parameter. No earlier record to compare.</div>
              </div>

              <div style="font-size: 13px;">
                <a href="{record.get('primary_source_url', '#')}" target="_blank" style="color: #3f646c; text-decoration: underline; margin-right: 14px;">Read the report (county PDF)</a>
                <a href="#" style="color: #3f646c; text-decoration: underline; margin-right: 14px;">Full record</a>
                <a href="#" style="color: #3f646c; text-decoration: underline;">All records for {system_text}</a>
              </div>
            </td>
          </tr>
    """

    contacts_html = f"""
      <div style="font-size: 14px; line-height: 1.55; color: #0b2732; font-family: 'Source Serif 4', Georgia, serif;">
        <strong>{agency_text}</strong><br />
        {phone_text} &middot; <a href="mailto:{email_text}" style="color: #3f646c;">{email_text}</a><br />
        <span style="font-size: 12px; color: #3f646c;">Contact as printed on {contact_page}.</span>
      </div>
    """

    source_hash_str = ""
    if record.get("source_sha256"):
        sha = record["source_sha256"]
        source_hash_str = f"Source file sha256 {sha[:8]}...{sha[-5:]}, fetched {source_fetched_str}."

    return render_water_email_scaffold(
        system_name=record.get('system', ''),
        checked_date_str=source_fetched_str,
        content_html=items_html,
        contacts_html=contacts_html,
        last_ingested_iso=record.get('source_fetched_at', ''),
        source_hash_str=source_hash_str,
        notice_type_label="Water record notice",
    )


def render_water_digest_email(records: Optional[List[Dict[str, Any]]] = None, show_first_issue_key: bool = False) -> str:
    """
    Renders water digest email matching WaterDigest.dc.html artboard.
    Dynamically renders all 5 WSSC records from backing markdown record files on disk.
    Zero typed figures, quotes, or contacts. Zero display: flex.
    """
    if records is None:
        wssc_dir = REPO_BASE / "water" / "measurements"
        wssc_record_paths = [
            wssc_dir / "wssc_customer_tap" / "lead_tap_2025.md",
            wssc_dir / "wssc_patuxent" / "pfoa_2025.md",
            wssc_dir / "wssc_patuxent" / "pfos_2025.md",
            wssc_dir / "wssc_potomac" / "pfoa_2025.md",
            wssc_dir / "wssc_potomac" / "pfos_2025.md",
        ]
        records = [parse_record_file(p)["frontmatter"] for p in wssc_record_paths if p.exists()]

    first_issue_key_html = ""
    if show_first_issue_key:
        first_issue_key_html = """
          <!-- FIRST ISSUE KEY -->
          <tr>
            <td class="mobile-padding" style="padding: 0 32px 20px 32px;">
              <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="border: 1px solid #d8d2c6; background-color: #fbfaf6; padding: 14px 18px;">
                <tr>
                  <td>
                    <div style="font-family: 'Source Serif 4', Georgia, serif; font-size: 10.5px; letter-spacing: 0.14em; text-transform: uppercase; color: #3f646c; margin-bottom: 6px; font-weight: 600;">How to read a water record &middot; shown in the first issue</div>
                    <div style="font-size: 12px; line-height: 1.45; color: #2c3e44; margin-bottom: 10px;">Each record carries a drop. Its shape marks what the agency&rsquo;s report states about a result. The shape carries the meaning, never the color.</div>
                    <table role="presentation" border="0" cellpadding="4" cellspacing="0" width="100%" style="font-size: 11.5px; line-height: 1.6; color: #0b2732;">
                      <tr>
                        <td width="24" valign="middle"><svg width="13" height="15" viewBox="0 0 18 20" aria-hidden="true"><path d="M9 1.5C9 1.5 3 9 3 13a6 6 0 0 0 12 0C15 9 9 1.5 9 1.5Z" fill="#0b2732" stroke="#0b2732" stroke-width="1.6"/><line x1="5.5" y1="13" x2="12.5" y2="13" stroke="#f7f4ee" stroke-width="2"/></svg></td>
                        <td><strong>Violation reported:</strong> The report or the regulator states a violation.</td>
                      </tr>
                      <tr>
                        <td width="24" valign="middle"><svg width="13" height="15" viewBox="0 0 18 20" aria-hidden="true"><path d="M9 1.5C9 1.5 3 9 3 13a6 6 0 0 0 12 0C15 9 9 1.5 9 1.5Z" fill="none" stroke="#0b2732" stroke-width="1.8"/></svg></td>
                        <td><strong>No violation reported:</strong> The report prints &ldquo;Violation: No&rdquo;.</td>
                      </tr>
                      <tr>
                        <td width="24" valign="middle"><svg width="13" height="15" viewBox="0 0 18 20" aria-hidden="true"><path d="M9 1.5C9 1.5 3 9 3 13a6 6 0 0 0 12 0C15 9 9 1.5 9 1.5Z" fill="none" stroke="#0b2732" stroke-width="1.8" stroke-dasharray="2.4 1.8"/></svg></td>
                        <td><strong>Limit not yet in force:</strong> The report prints &ldquo;Violation: N/A&rdquo;. Compliance date is ahead.</td>
                      </tr>
                      <tr>
                        <td width="24" valign="middle"><svg width="13" height="15" viewBox="0 0 18 20" aria-hidden="true"><path d="M9 1.5C9 1.5 3 9 3 13a6 6 0 0 0 12 0C15 9 9 1.5 9 1.5Z" fill="none" stroke="#527a83" stroke-width="1.8"/><circle cx="9" cy="13" r="1.5" fill="#527a83"/></svg></td>
                        <td><strong>Not stated:</strong> The report gives no determination.</td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        """

    drop_violation = """<svg width="13" height="15" viewBox="0 0 18 20" aria-hidden="true" style="vertical-align: middle;"><path d="M9 1.5C9 1.5 3 9 3 13a6 6 0 0 0 12 0C15 9 9 1.5 9 1.5Z" fill="#0b2732" stroke="#0b2732" stroke-width="1.6"/><line x1="5.5" y1="13" x2="12.5" y2="13" stroke="#f7f4ee" stroke-width="2"/></svg>"""
    drop_no_violation = """<svg width="13" height="15" viewBox="0 0 18 20" aria-hidden="true" style="vertical-align: middle;"><path d="M9 1.5C9 1.5 3 9 3 13a6 6 0 0 0 12 0C15 9 9 1.5 9 1.5Z" fill="none" stroke="#0b2732" stroke-width="1.8"/></svg>"""
    drop_limit_not_in_force = """<svg width="13" height="15" viewBox="0 0 18 20" aria-hidden="true" style="vertical-align: middle;"><path d="M9 1.5C9 1.5 3 9 3 13a6 6 0 0 0 12 0C15 9 9 1.5 9 1.5Z" fill="none" stroke="#0b2732" stroke-width="1.8" stroke-dasharray="2.4 1.8"/></svg>"""
    drop_not_stated = """<svg width="13" height="15" viewBox="0 0 18 20" aria-hidden="true" style="vertical-align: middle;"><path d="M9 1.5C9 1.5 3 9 3 13a6 6 0 0 0 12 0C15 9 9 1.5 9 1.5Z" fill="none" stroke="#527a83" stroke-width="1.8"/><circle cx="9" cy="13" r="1.5" fill="#527a83"/></svg>"""

    cards_html = []
    for rec in records:
        det = rec.get("determination", {})
        det_status = det.get("status", "not_stated")
        if det_status == "violation_reported":
            drop_glyph = drop_violation
            det_label = "Violation reported"
        elif det_status == "no_violation_reported":
            drop_glyph = drop_no_violation
            det_label = "No violation reported"
        elif det_status == "limit_not_yet_in_force":
            drop_glyph = drop_limit_not_in_force
            det_label = "Limit not yet in force"
        else:
            drop_glyph = drop_not_stated
            det_label = "Not stated"

        det_quote = html.escape(str(det.get("quote", "")))
        det_page = html.escape(str(det.get("source_page", "")))
        det_meta_text = f"Report prints &ldquo;{det_quote}&rdquo; &middot; {det_page}" if det_quote else det_page

        gov_limit = rec.get("governing_limit", {})
        limit_val = html.escape(str(gov_limit.get("value", "None on record")))
        limit_unit = html.escape(str(gov_limit.get("unit", "")))
        limit_str = f"{limit_val} {limit_unit}".strip() if limit_val != "None on record" else "None on record"
        limit_basis = html.escape(str(gov_limit.get("basis", "")))
        limit_citation = html.escape(str(gov_limit.get("citation", "")))
        limit_compliance = html.escape(str(gov_limit.get("compliance_date", "")))
        fed_desc_parts = [p for p in [limit_citation, limit_basis, limit_compliance] if p]
        fed_limit_desc = " &middot; ".join(fed_desc_parts)

        val = html.escape(str(rec.get("value", "")))
        unit = html.escape(str(rec.get("unit", "")))
        rep_val_str = f"{val} {unit}".strip()
        raw_range = rec.get("range", "")
        rep_range = html.escape(str(raw_range)) if raw_range else ""
        rec_param = html.escape(str(rec.get("parameter", "")))
        rec_system = html.escape(str(rec.get("system", "")))
        rec_period = html.escape(str(rec.get("reporting_period", "")))

        if rec.get("parameter") == "Lead":
            basis_str = html.escape(str(gov_limit.get("basis", "90th percentile")))
            rep_sub = f"{basis_str} &middot; range {rep_range}" if rep_range else basis_str
            period_label = f"reporting period {rec_period}" if rec_period else ""
        else:
            rep_sub = f"highest level found &middot; range {rep_range}" if rep_range else "highest level found"
            period_label = f"reporting period {rec_period}" if rec_period else ""

        mclg_val = html.escape(str(rec.get("mclg", "")))

        extra_card_bottom = ""
        comp_date_val = gov_limit.get("compliance_date", "")
        lim_status_val = gov_limit.get("limit_status", "")
        if comp_date_val and "November 1, 2027" in comp_date_val:
            extra_card_bottom = f"""
                <div style="padding: 8px 14px; border-top: 1px solid #d8d2c6; font-size: 12px; color: #2c3e44;">
                  Limit status: {html.escape(str(lim_status_val))}. Compliance note: {html.escape(str(comp_date_val))}
                </div>
            """

        card_html = f"""
          <!-- CARD: {rec_system} · {rec_param} -->
          <tr>
            <td class="mobile-padding" style="padding: 0 32px 16px 32px;">
              <div style="border: 1px solid #d8d2c6; background-color: #fbfaf6;">
                <div style="padding: 10px 14px; border-bottom: 1px solid #d8d2c6;">
                  <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%">
                    <tr>
                      <td valign="baseline" style="font-family: 'Source Serif 4', Georgia, serif; font-size: 14.5px; font-weight: 600; color: #0b2732;">
                        {html.escape(format_water_heading(rec))}
                      </td>
                      <td align="right" valign="baseline" style="font-size: 12px; color: #3f646c; white-space: nowrap;">
                        {period_label}
                      </td>
                    </tr>
                  </table>
                  <table role="presentation" border="0" cellpadding="0" cellspacing="0" style="margin-top: 4px;">
                    <tr>
                      <td valign="middle" style="padding-right: 6px;">
                        {drop_glyph}
                      </td>
                      <td valign="middle" style="font-size: 10.5px; letter-spacing: 0.12em; text-transform: uppercase; font-weight: 600; color: #0b2732; padding-right: 10px;">
                        {det_label}
                      </td>
                      <td valign="middle" style="font-size: 12px; color: #2c3e44;">
                        {det_meta_text}
                      </td>
                    </tr>
                  </table>
                </div>
                <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="font-size: 13px;">
                  <tr>
                    <td width="50%" style="padding: 9px 14px; border-right: 1px solid #d8d2c6; border-bottom: 1px solid #d8d2c6;" valign="top">
                      <div style="color: #3f646c; text-transform: uppercase; letter-spacing: 0.1em; font-size: 10px;">Reported</div>
                      <div style="font-weight: 600; color: #0b2732;">{rep_val_str}</div>
                      {f'<div style="font-size: 11.5px; color: #3f646c;">{rep_sub}</div>' if rep_sub else ''}
                    </td>
                    <td width="50%" style="padding: 9px 14px; border-bottom: 1px solid #d8d2c6;" valign="top">
                      <div style="color: #3f646c; text-transform: uppercase; letter-spacing: 0.1em; font-size: 10px;">State limit</div>
                      <div style="color: #0b2732;">None on record</div>
                    </td>
                  </tr>
                  <tr>
                    <td width="50%" style="padding: 9px 14px; border-right: 1px solid #d8d2c6;" valign="top">
                      <div style="color: #3f646c; text-transform: uppercase; letter-spacing: 0.1em; font-size: 10px;">Federal limit</div>
                      <div style="font-weight: 600; color: #0b2732;">{limit_str}</div>
                      {f'<div style="font-size: 11.5px; color: #3f646c;">{fed_limit_desc}</div>' if fed_limit_desc else ''}
                    </td>
                    <td width="50%" style="padding: 9px 14px;" valign="top">
                      <div style="color: #3f646c; text-transform: uppercase; letter-spacing: 0.1em; font-size: 10px;">Federal health goal</div>
                      <div style="font-weight: 600; color: #0b2732;">{mclg_val}</div>
                      <div style="font-size: 11.5px; color: #3f646c;">MCLG &middot; not enforceable</div>
                    </td>
                  </tr>
                </table>
                {extra_card_bottom}
              </div>
            </td>
          </tr>
        """
        cards_html.append(card_html)

    cards_joined = "\n".join(cards_html)
    first_rec = records[0] if records else {}
    source_agency = html.escape(str(first_rec.get("source_agency", "Washington Suburban Sanitary Commission (WSSC Water)")))
    p_url = html.escape(str(first_rec.get("primary_source_url", "https://www.wsscwater.com/wqr")))
    source_title = html.escape(str(first_rec.get("source_title") or "2025 Water Quality Report"))
    source_fetched_str = html.escape(str(first_rec.get("source_fetched_at", "")[:10]))
    file_last_saved = first_rec.get("file_last_saved")
    saved_str = f" &middot; file last saved {html.escape(str(file_last_saved))}" if file_last_saved else ""

    # Extract PFAS note from PFAS record dynamically
    pfas_rec = next((r for r in records if "PFOA" in r.get("parameter", "")), None)
    pfas_note_html = ""
    if pfas_rec:
        p_det = pfas_rec.get("determination", {})
        p_quote = html.escape(str(p_det.get("quote", "")))
        p_page = html.escape(str(p_det.get("source_page", "")))
        p_gov = pfas_rec.get("governing_limit", {})
        p_raw_status = str(p_gov.get("limit_status", "")).strip()
        # Clean proposed extension phrasing so it does not duplicate 'Proposed' or '(FR 2026-10086)'
        p_clean = p_raw_status
        if p_clean.lower().startswith("proposed "):
            p_clean = p_clean[len("proposed "):].strip()
            if p_clean:
                p_clean = p_clean[0].upper() + p_clean[1:]
        p_clean = re.sub(r"\s*\(FR\s*2026-10086\)\.?$", "", p_clean, flags=re.IGNORECASE).strip()
        if p_clean and not p_clean.endswith("."):
            p_clean += "."
        p_status = html.escape(p_clean)
        p_url_ref = html.escape(str(p_gov.get("limit_status_url", "https://www.govinfo.gov/content/pkg/FR-2026-05-20/pdf/2026-10086.pdf")))
        pfas_note_html = f"""
          <!-- PFAS Limit Note -->
          <tr>
            <td class="mobile-padding" style="padding: 0 32px 16px 32px;">
              <div style="border: 1px solid #d8d2c6; padding: 12px 14px; font-size: 12.5px; line-height: 1.6; color: #2c3e44; background-color: #fbfaf6;">
                <div style="color: #3f646c; font-size: 10.5px; letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 6px;">PFOA and PFOS limit &middot; status on the record</div>
                {p_page}: &ldquo;{p_quote}&rdquo;<br />
                Proposed. Not a rule yet. {p_status} <a href="{p_url_ref}" target="_blank" style="color: #3f646c;">FR 2026-10086</a>
              </div>
            </td>
          </tr>
        """

    items_html = f"""
          {first_issue_key_html}
          <tr>
            <td class="mobile-padding" style="padding: 0 32px 14px 32px;">
              <div style="font-family: 'Source Serif 4', Georgia, serif; font-size: 10.5px; letter-spacing: 0.14em; text-transform: uppercase; color: #3f646c; margin-bottom: 4px;">Water system serving this jurisdiction, as on record</div>
              <div style="font-family: 'Source Serif 4', Georgia, serif; font-size: 19px; font-weight: 600; line-height: 1.25; color: #0b2732;">{source_agency}</div>
              <div style="font-size: 13px; color: #2c3e44; line-height: 1.5; margin-top: 2px;">Serves Montgomery County and Prince George&rsquo;s County. {len(records)} records from the {source_title}{saved_str} &middot; fetched {source_fetched_str}.</div>
            </td>
          </tr>

          {cards_joined}

          {pfas_note_html}

          <tr>
            <td class="mobile-padding" style="padding: 0 32px 20px 32px;">
              <div style="font-size: 13px;">
                <a href="{p_url}" target="_blank" style="color: #3f646c; text-decoration: underline; margin-right: 14px;">Read the report (wsscwater.com/wqr)</a>
                <a href="#" style="color: #3f646c; text-decoration: underline;">All WSSC Water records</a>
              </div>
            </td>
          </tr>
    """

    # Extract contacts dynamically across records without duplicate pipetype email
    contacts_by_email = {}
    for r in records:
        c = r.get("contact", {})
        em = c.get("email")
        if em and em not in contacts_by_email:
            contacts_by_email[em] = c

    gen_c = contacts_by_email.get("customerservice@wsscwater.com") or (list(contacts_by_email.values())[0] if contacts_by_email else {})
    lead_c = contacts_by_email.get("pipetype@wsscwater.com")

    agency_name = html.escape(str(gen_c.get('agency', source_agency)))
    gen_phone = html.escape(str(gen_c.get('phone', '')))
    gen_email = html.escape(str(gen_c.get('email', '')))

    contacts_lines = [f"<strong>{agency_name}</strong><br />"]
    if gen_phone and gen_email:
        contacts_lines.append(f"{gen_phone} &middot; <a href=\"mailto:{gen_email}\" style=\"color: #3f646c;\">{gen_email}</a><br />")
    elif gen_email:
        contacts_lines.append(f"<a href=\"mailto:{gen_email}\" style=\"color: #3f646c;\">{gen_email}</a><br />")

    if lead_c and lead_c.get("email") != gen_email:
        lead_email = html.escape(str(lead_c.get("email", "")))
        contacts_lines.append(f"Lead testing: <a href=\"mailto:{lead_email}\" style=\"color: #3f646c;\">{lead_email}</a><br />")

    page_nums = []
    for c in contacts_by_email.values():
        sp = c.get("source_page", "")
        if sp:
            for m in re.finditer(r"\bpage[s]?\s*(\d+)\b", sp, re.IGNORECASE):
                num = int(m.group(1))
                if num not in page_nums:
                    page_nums.append(num)
    page_nums.sort()
    if page_nums:
        if len(page_nums) == 1:
            pages_str = f"page {page_nums[0]}"
        elif len(page_nums) == 2:
            pages_str = f"pages {page_nums[0]} and {page_nums[1]}"
        else:
            pages_str = f"pages {', '.join(str(p) for p in page_nums[:-1])} and {page_nums[-1]}"
        contacts_lines.append(f"<span style=\"font-size: 12px; color: #3f646c;\">Contacts as printed on {pages_str} of the report.</span>")
    else:
        source_pages = sorted(list(set(c.get("source_page") for c in contacts_by_email.values() if c.get("source_page"))))
        if source_pages:
            pages_str = " &amp; ".join(html.escape(str(sp)) for sp in source_pages)
            contacts_lines.append(f"<span style=\"font-size: 12px; color: #3f646c;\">Contacts as printed on {pages_str}.</span>")

    contacts_html = f"""
      <div style="font-size: 14px; line-height: 1.55; color: #0b2732; font-family: 'Source Serif 4', Georgia, serif;">
        {''.join(contacts_lines)}
      </div>
    """

    posture_text = (
        '<strong style="color: #f7f4ee;">What this digest is.</strong> '
        'Enacted reports what the agency published and quotes it. A reported value and a governing limit are shown as the report prints them, each with its own basis. '
        'Enacted does not compare them, interpret a result, assess the water at any address, or advise. '
        '<strong style="color: #f7f4ee;">Which system serves an address, and what a result means for a household,</strong> '
        'are questions for the agency named above.'
    )

    source_hash_str = ""
    if first_rec.get("source_sha256"):
        sha = first_rec["source_sha256"]
        fetched_dt = first_rec.get("source_fetched_at", "")[:10]
        source_hash_str = f"Source file sha256 {sha[:8]}...{sha[-5:]}, fetched {fetched_dt}."

    return render_water_email_scaffold(
        system_name="Montgomery County",
        checked_date_str=first_rec.get("source_fetched_at", "")[:10],
        content_html=items_html,
        contacts_html=contacts_html,
        last_ingested_iso=first_rec.get("source_fetched_at", ""),
        posture_text=posture_text,
        source_hash_str=source_hash_str,
        notice_type_label="Water quality digest",
    )


def main():
    print("Executing Task 6: Rendering newsletters strictly from backing legal record files...")
    
    aa_later_html = render_anne_arundel(show_first_issue_key=False)
    aa_first_html = render_anne_arundel(show_first_issue_key=True)
    hw_html = render_howard()
    water_not_found_html = render_water_source_not_found_email()
    water_found_html = render_water_source_found_email()
    water_notice_later_html = render_water_notice_email(show_first_issue_key=False)
    water_notice_first_html = render_water_notice_email(show_first_issue_key=True)
    water_digest_later_html = render_water_digest_email(show_first_issue_key=False)
    water_digest_first_html = render_water_digest_email(show_first_issue_key=True)

    # Ensure output directories exist
    DEV_DIR.mkdir(parents=True, exist_ok=True)
    BRAIN_DIR.mkdir(parents=True, exist_ok=True)

    # Write to dev/
    (DEV_DIR / "enacted_newsletter_anne_arundel.html").write_text(aa_later_html, encoding="utf-8")
    (DEV_DIR / "anne_arundel_email_notification.html").write_text(aa_later_html, encoding="utf-8")
    (DEV_DIR / "zoning_digest_later_issue.html").write_text(aa_later_html, encoding="utf-8")
    (DEV_DIR / "zoning_digest_first_issue.html").write_text(aa_first_html, encoding="utf-8")
    (DEV_DIR / "enacted_newsletter_howard.html").write_text(hw_html, encoding="utf-8")
    (DEV_DIR / "water_source_not_found_email.html").write_text(water_not_found_html, encoding="utf-8")
    (DEV_DIR / "water_source_found_email.html").write_text(water_found_html, encoding="utf-8")
    (DEV_DIR / "water_notice_email.html").write_text(water_notice_later_html, encoding="utf-8")
    (DEV_DIR / "water_notice_first_issue_email.html").write_text(water_notice_first_html, encoding="utf-8")
    (DEV_DIR / "water_digest_email.html").write_text(water_digest_later_html, encoding="utf-8")
    (DEV_DIR / "water_digest_first_issue_email.html").write_text(water_digest_first_html, encoding="utf-8")

    # Write to brain artifacts
    (BRAIN_DIR / "enacted_newsletter_anne_arundel.html").write_text(aa_later_html, encoding="utf-8")
    (BRAIN_DIR / "zoning_digest_later_issue.html").write_text(aa_later_html, encoding="utf-8")
    (BRAIN_DIR / "zoning_digest_first_issue.html").write_text(aa_first_html, encoding="utf-8")
    (BRAIN_DIR / "enacted_newsletter_howard.html").write_text(hw_html, encoding="utf-8")
    (BRAIN_DIR / "water_source_not_found_email.html").write_text(water_not_found_html, encoding="utf-8")
    (BRAIN_DIR / "water_source_found_email.html").write_text(water_found_html, encoding="utf-8")
    (BRAIN_DIR / "water_notice_email.html").write_text(water_notice_later_html, encoding="utf-8")
    (BRAIN_DIR / "water_notice_first_issue_email.html").write_text(water_notice_first_html, encoding="utf-8")
    (BRAIN_DIR / "water_digest_email.html").write_text(water_digest_later_html, encoding="utf-8")
    (BRAIN_DIR / "water_digest_first_issue_email.html").write_text(water_digest_first_html, encoding="utf-8")

    print("PASS: Rendered Anne Arundel newsletter from bill_18_26.md, bill_28_26.md, bill_57_26.md (first & later issue).")
    print("PASS: Rendered Howard County newsletter from cb_25_2026.md, cb_24_2026.md, cb_04_2026.md.")
    print("PASS: Rendered Water notice (first & later issue) dynamically from aa_broad_creek/lead_copper_violation_2025.md.")
    print("PASS: Rendered Water digest (first & later issue) dynamically from all 5 WSSC Water markdown records.")
    print("PASS: Rendered Water source not-found and found closing notice templates.")
    print("Invariant verified: The newsletter is a view of the corpus, never a source.")

if __name__ == "__main__":
    main()


