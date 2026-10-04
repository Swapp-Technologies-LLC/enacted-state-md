# Developer & Operational Runbook — Enacted Maryland Legal Repository (`enacted-state-md`)

This repository records the enacted law. It does not advise, approve, determine, or certify anything.

---

## 1. Branch Protection Configuration (Founder Setup Guide)

When publishing this repository on GitHub under the organization account, configure branch protection for the `main` branch under **Settings > Branches > Branch protection rules > Add rule**:

### Required Settings:
1. **Branch name pattern:** `main`
2. **Protect matching branches:**
   - **Require a pull request before merging:**
     - Require approvals: `1`
     - Dismiss stale pull request approvals when new commits are pushed: `Checked`
     - Require review from Code Owners: `Optional / Checked`
   - **Require status checks to pass before merging:**
     - Require branches to be up to date before merging: `Checked`
     - Status checks that must pass:
       - `Record Integrity & Gate Suite` (defined in `verify.yml`)
   - **Do not allow bypassing the above settings:**
     - Enforce for repository administrators: `Checked`
   - **Restrict direct pushes:**
     - Do not allow direct pushes to `main`: `Checked`
3. **Auto-Merge Policy:**
   - **Auto-merge stays strictly OFF for every source** until the founder issues an explicit ruling per source based on an established track record.
   - All automated pull requests opened by `ingest.yml` require human review before merge.

---

## 2. CI Workflow Activation (Post-Push)

The automated workflows are staged in `.github/workflows-pending/`:
- `ingest.yml`: Scheduled deterministic legislative polling (Montgomery daily, Anne Arundel twice weekly). Opens pull requests via `peter-evans/create-pull-request`. Never pushes directly to `main`.
- `verify.yml`: Triggers on `push` and `pull_request` to `main`. Runs `python verify_corpus_integrity.py` and blocks merge on any red gate.

### Activation Step:
After the founder creates the GitHub organization, creates the `enacted-state-md` repository, and completes the initial push:
```bash
git mv .github/workflows-pending .github/workflows
git commit -m "chore(ci): activate ingestion and verification workflows"
git push origin main
```

### Required Repository Secret (Founder Setup):
Before activating `ingest.yml`, configure the following secret under **Settings > Secrets and variables > Actions > New repository secret**:
- **Name:** `ENACTED_BOT_TOKEN`
- **Type:** Fine-grained Personal Access Token (PAT) created by the founder for the bot account.
- **Permissions Required:**
  - Repository permissions:
    - `Contents: Read and write` (to branch and commit harvested records)
    - `Pull requests: Read and write` (to open automated pull requests)
- **Why this is required:** Pull requests created with GitHub's default `GITHUB_TOKEN` do not trigger downstream workflow runs (GitHub Actions security policy). Because `verify.yml` must execute and pass its complete gate suite on all automated ingestion PRs before human review and merge, `ingest.yml` uses `token: ${{ secrets.ENACTED_BOT_TOKEN }}` for the `peter-evans/create-pull-request` step. All other steps (such as opening issue alerts on poller failure) continue to use the standard `GITHUB_TOKEN`.

---

## 3. Record Integrity Rules & Pipeline Invariants

1. **Rule 10 (Zero Model in Ingestion Path):**
   - No LLM calls, AI services, or external model APIs exist anywhere in the ingestion or verification pipeline.
   - All record harvesting, frontmatter extraction, feed rendering, and newsletter generation are deterministic code.
   - Scrapers and pollers extract only mechanically verifiable fields from primary government portals. If a selector or field cannot be found, the poller omits the field or exits non-zero and automatically opens a GitHub issue (`ingestion-failure`). It never infers.
2. **Cryptographic Re-Hash Gate:**
   - Every primary PDF document is downloaded and verified against its committed `source_sha256` hash.
   - PDFs are cached by hash (`.cache/pdf_cache`) in GitHub Actions cache to ensure polite crawling and sub-second runtimes.
3. **Corpus-First Invariant:**
   - Syndication feeds (`feeds/`) and newsletters are strictly views of the verified corpus, never sources.
   - No feed item or dispatch exists without a verified backing record file.
4. **Primary Government Sourcing Only:**
   - Aggregators (Municode, AmLegal, eCode360) are blocklisted.
   - Blocked jurisdictions remain empty with documentation in `SOURCING_BLOCKED.md`.

---

## 4. External Endpoints Touched by Workflows

The deterministic workflows interact only with the following official endpoints:
- Montgomery County Socrata Open Data API: `https://data.montgomerycountymd.gov`
- Montgomery County Portal & Assets: `https://www.montgomerycountymd.gov`, `https://assets.montgomerycountymd.gov`, `https://montgomerycountymd.granicus.com`
- Anne Arundel County Council Portal: `https://www.aacounty.org`
- Baltimore City Council Legistar Portal: `https://baltimore.legistar.com`, `https://baltimore.legistar1.com`
- Baltimore County Council Web Portal: `https://countycouncilweb.s3.amazonaws.com`
- Frederick County Document Center: `https://www.frederickcountymd.gov`
- Harford County Document Center: `https://www.harfordcountymd.gov`
- Howard County OLIS Portal: `https://apps.howardcountymd.gov`
- Prince George's County Legistar Portal: `https://princegeorgescountymd.legistar.com`, `https://princegeorgescountymd.legistar1.com`
- Maryland General Assembly Statutes Portal: `https://mgaleg.maryland.gov`
- GitHub API (`api.github.com` via GitHub Actions runner for PR / issue creation)\n
---

## 5. Multi-Topic Topology & Directory Layout

Repositories are organized on a per-state basis (`enacted-state-md`) containing all topics for that state's jurisdictions (alongside `enacted-federal` for federal matters).
- **Topic is a Directory + Tag, Never a Repo**: Legislative records live in `<jurisdiction>/council_bills/` or `<jurisdiction>/zta_amendments/` with frontmatter tags: `record_type: legislative`, `topic: zoning`, `topics: ["zoning", ...]`.
- **Measurement Records**: Public water and environmental measurement records live strictly under `water/measurements/<PWSID>/<parameter>_<year>.md` with frontmatter tags: `record_type: measurement`, `topic: water`, `topics: ["water"]`, `system_id: <PWSID>`, and mechanical quotation from Consumer Confidence Reports (CCRs) or SDWIS reports.
- **Feed Topology**: Atom 1.0 and JSON Feed 1.1 syndication feeds are generated for each populated jurisdiction and topic:
  - Per-jurisdiction topic feeds: `feeds/<jur>/<topic>.atom|json`
  - Statewide topic aggregates: `feeds/topics/<topic>.atom|json`
  - Master statewide zoning feed: `feeds/zoning.atom|json`

---

## 6. News & Journalistic Sourcing Policy (Founder Ruling 2026-09-15)

- **Zero Journalistic Links in Corpus**: News articles, investigative reports, press commentary, op-eds, blogs, and secondary reporting are strictly barred from the corpus. No news domain is ever linked or cited in frontmatter or dispatches.
- **Internal Operational Trigger Only**: News mentions, press reporting, and user tips serve solely as operational alerts that prompt an immediate deterministic crawl of the relevant official government portal. If the primary legislative bill or measurement report is not present on the official government portal, no record is created.
- **Official Government Press Releases**: Formal agency press releases or official notices published by the municipal or state government body itself are classified as primary records and may only be ingested under hard provenance standards (HTTP 200, SHA-256 hash, fetch timestamp, mechanical quoting).

---

## 7. Demand Capture & Private Demand Ledger

- **Intake Surface (`request_coverage.html`)**: Clean, static web form hosted via GitHub Pages enabling users to submit coverage requests by jurisdiction and topic.
- **Private Counts**: Aggregate waitlist counts and subscriber metrics are strictly confidential and must never be published publicly or surfaced in marketing copy.
- **Deterministic Demand Ledger (`scripts/demand_ledger.py`)**: Runs weekly to compile waitlist entries, feed subscriptions, and search demand into a confidential founder report (`reports/demand_ledger_YYYY-MM-DD.md`) with deterministic prioritization scores.

---

## 8. Topic Derivation Rule & Validation Engine (`scripts/derive_topics.py`)

Topic tags are deterministically derived from enacted text and frontmatter sections:
- **Rule 10 Invariant**: Zero model calls. Topic tags are derived solely through deterministic pattern matching:
  - `zoning`: Matches local land-use titles (Article 18, Article 32, BCZR, HCZR, Chapter 59, Chapter 1-19, Chapter 267, Subtitle 27, Land Use Article) or statutory zoning terms (`zoning`, `zta`, `comprehensive zoning`, `setback`, `district`).
  - `water`: Matches drinking water standards, water quality monitoring, utility service areas, contaminant thresholds (MCL, AL, PFAS, Lead and Copper Rule), or coastal critical area statutory protection (Natural Resources Article Title 8).
  - `pfas`: Matches specific per- and polyfluoroalkyl substances (PFOA, PFOS, GenX).
- **Enforcement Gate**: In CI, `python scripts/derive_topics.py` runs across the entire corpus. Any tag not mechanically produced by this derivation rule fails the gate. Records cannot carry speculative or unverified topic tags.

---

## 9. Partner Tier Architecture & Address Resolution Contract (Spec §7c)

- **Zero Property-Level Adjudication (L-01 Posture)**: Enacted records enacted municipal law and public water quality. It does not advise, evaluate, or certify individual properties, parcels, or addresses.
- **Partner-Side Address Resolution**: Partners (such as HouseOver Pro) resolve any user/customer street address or ZIP code to a canonical `jurisdiction_key` (e.g., `md/montgomery`, `md/anne_arundel`, `md/baltimore_city`) on their own infrastructure prior to querying Enacted APIs.
- **Hard Rejection of Address/Parcel/ZIP Fields by Design**: The Enacted Partner API explicitly and intentionally rejects (HTTP 400 Bad Request) any query carrying `address`, `street`, `parcel`, `parcel_id`, `pin`, `tax_id`, `zipcode`, `postal_code`, `owner`, or `homeowner` fields. Such queries are rejected before entering any data store and are bypassed from the usage ledger.
- **Vendored Crosswalk Library**: A future vendored crosswalk library (`enacted-crosswalk`) will be provided for partner-side integration to map ZIP codes and address coordinate bounding boxes to official municipal and county jurisdiction keys without transmitting address data to Enacted services.

---

## 10. Recorded Covenants Record Class (`hoa_covenant`) & Data Minimisation

Recorded covenants (declarations, CC&Rs, amendments, supplemental declarations, recorded bylaws, plat notes) are ingested through the public corpus mechanism under the same posture as zoning and environmental records: Enacted records the recorded instrument and its dates; it never says what an association allows or forbids, never resolves a conflict between a covenant and a later rule, and never addresses a lot or an owner.

### 10.1 Corpus Directory Topology
Recorded covenants reside under the county directory in each state data repository:
```
<county_slug>/recorded_covenants/<association_slug>/<instrument_slug>.md
```
Example: `montgomery/recorded_covenants/woodland_hills/declaration.md` or `anne_arundel/recorded_covenants/bay_ridge/amendment_01.md`.

### 10.2 Frontmatter Schema
Every `hoa_covenant` record requires YAML frontmatter adhering to this schema:
| Field | Type | Description / Allowed Values |
| :--- | :--- | :--- |
| `association_name` | string | Exact legal name of the association as stated in the charter / declaration. |
| `association_slug` | string | Lowercase alphanumeric slug with underscores (e.g., `woodland_hills`). |
| `county` | string | Canonical county key as in `build.py` (e.g., `md/montgomery` or `montgomery`). |
| `instrument_type` | enum | `declaration`, `amendment`, `supplemental_declaration`, `bylaws_recorded`, `plat_note`. |
| `recording_reference` | string | Free text as recorded: liber/folio, book/page, or instrument number. |
| `recorded_date` | string | ISO date (`YYYY-MM-DD`) when the instrument was recorded in land records. |
| `effective_date` | string (optional) | ISO date (`YYYY-MM-DD`) only if explicitly stated in the instrument; otherwise omitted. |
| `supersedes` | string or null | `instrument_slug` of the prior instrument superseded or amended, or `null`. |
| `amends_sections` | list[string] | List of section citations amended within the declaration (e.g., `["Section 4.02"]`). |
| `source_kind` | enum | `county_land_records`, `county_depository`, `association_provided`, `owner_provided`. |
| `source_reference` | string | Citation text (e.g. Liber/Folio citation). URL permitted ONLY when source terms permit linking (`county_depository`, `association_provided`). |
| `source_sha256` | string | 64-character lowercase hex SHA-256 of the document file on record. |
| `source_fetched_at` | string | ISO 8601 UTC timestamp (`YYYY-MM-DDTHH:MM:SSZ`) of document acquisition. |
| `who_to_ask` | object | `{office: "<association name> — registered agent or management company as listed in the association's charter record", contact lines as stated in public record}`. |
| `record_type` | string | Exactly `covenant`. |
| `topic` | string | Exactly `hoa`. |
| `topics` | list[string] | Exactly `["hoa"]`. |

### 10.3 Body Structure
The Markdown body consists strictly of three sections:
1. `## 1. Instrument`: Type, recording reference, and recording/effective dates.
2. `## 2. Recorded text`: Verbatim quoted text:
   - For amendments: a ` ```diff ` fence showing struck text (`- `) and inserted text (`+ `) against the prior instrument, quoting whole sections only.
   - For initial declarations: operative articles quoted, with an omissions notice (e.g., `[Articles 1–3 and 5–12 omitted — full text in the recorded instrument]`).
3. `## 3. Who to ask`: Administrative contact note directing questions to the association's registered agent or management company.

### 10.4 Data Minimisation Rules (Enforced by Automated Gate)
To protect privacy and minimize non-operative personally identifiable data, the automated gate enforces strict redaction/exclusion:
- **Never quote**:
  - Signature pages or execution blocks
  - Notary acknowledgments or certificates
  - Grantor or grantee individual personal names
  - Lot owners' names
  - Legal descriptions of individual lots (metes and bounds, lot/block parcel schedules)
- **Banned phrases**: `witness`, `notary`, `acknowledged before me`, `grantor`, `grantee`, `lot owner`.
- **Address patterns**: Street address patterns are prohibited in covenant bodies.
- **Permitted names**: The association's name and its official registered agent or management company contact are the only personal/entity names permitted.

