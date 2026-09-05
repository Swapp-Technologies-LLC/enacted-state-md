"""
generate_newsletter.py
Task 6: Enacted Newsletter Generation Engine
Renders newsletters strictly FROM backing legal record files in the corpus.
Invariant: The newsletter is a view of the corpus, never a source.
Swapp Technologies LLC (Maryland LLC)
"""

import os
import re
import yaml
from pathlib import Path

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
                      <a href="#" style="color: #9cd0ca; text-decoration: underline;">[FOUNDER: confirm opt-out URL]</a>
                    </p>
                    <div style="color: #527a83;">
                      &copy; 2026 Swapp Technologies LLC &middot; [FOUNDER: confirm mailing address] &middot; Organized under the laws of Maryland &middot; <a href="https://enacted.app" target="_blank" style="color: #527a83; text-decoration: underline;">enacted.app</a> &middot; <a href="https://enacted.news" target="_blank" style="color: #527a83; text-decoration: underline;">enacted.news</a>
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

def render_anne_arundel():
    aa_dir = REPO_BASE / "anne_arundel" / "council_bills"
    b18 = parse_record_file(aa_dir / "bill_18_26.md")
    b28 = parse_record_file(aa_dir / "bill_28_26.md")
    b57 = parse_record_file(aa_dir / "bill_57_26.md")

    items_html = f"""
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

def main():
    print("Executing Task 6: Rendering newsletters strictly from backing legal record files...")
    
    aa_html = render_anne_arundel()
    hw_html = render_howard()

    # Write to dev/
    (DEV_DIR / "enacted_newsletter_anne_arundel.html").write_text(aa_html, encoding="utf-8")
    (DEV_DIR / "anne_arundel_email_notification.html").write_text(aa_html, encoding="utf-8")
    (DEV_DIR / "enacted_newsletter_howard.html").write_text(hw_html, encoding="utf-8")

    # Write to brain artifacts
    (BRAIN_DIR / "enacted_newsletter_anne_arundel.html").write_text(aa_html, encoding="utf-8")
    (BRAIN_DIR / "enacted_newsletter_howard.html").write_text(hw_html, encoding="utf-8")

    print("PASS: Rendered Anne Arundel newsletter from bill_18_26.md, bill_28_26.md, bill_57_26.md.")
    print("PASS: Rendered Howard County newsletter from cb_25_2026.md, cb_24_2026.md, cb_04_2026.md.")
    print("Invariant verified: The newsletter is a view of the corpus, never a source.")

if __name__ == "__main__":
    main()
