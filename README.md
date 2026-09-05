# Enacted: Maryland Legal Repository (`enacted-state-md`)

This repository contains verified primary-source records of enacted Maryland land-use, zoning, and building law across all 24 county-level jurisdictions, statewide enabling statutes, and public water quality measurement records.

**Parent Entity:** Swapp Technologies LLC (Organized in Maryland)  
**Repository Scope:** Maryland Land-Use, Municipal Zoning Law & Public Water Quality  
**Posture:** This repository records the enacted law. It does not advise, approve, determine, or certify anything.  

---

## 1. What This Repository Is

Enacted records what changed, when it took effect, and who to ask:
1. **Verbatim Statutory & Measurement Records**: Quoted provisions mechanically extracted from primary enacted instruments and official agency reports.
2. **Deterministic Version History**: Structured changes and legislative chronologies with exact effective dates.
3. **Primary Municipal Contacts**: Official municipal planning, zoning, and utility departments responsible for administering each local jurisdiction.

### Standard Verification Line
*This repository records the enacted law. It does not advise, approve, determine, or certify anything.*  
All text quotes, reports, shows, and records primary government documents. It does not provide legal advice or apply law to specific facts.

---

## 2. Sourcing Standards & Aggregator Blocklist

All records in this repository are derived strictly from primary government portals (Maryland General Assembly, county legislative databases, Legistar systems, and official open data portals).

### Aggregator Hard Blocklist
Under Swapp Technologies LLC record integrity rules, third-party code aggregators are strictly blocklisted:
* **Municode** (`municode.com` / CivicPlus)
* **American Legal Publishing** (`amlegal.com`)
* **eCode360** (`ecode360.com` / General Code)

Jurisdictions whose codes are accessible only through blocklisted third-party aggregators contain a `SOURCING_BLOCKED.md` file detailing the evaluation and remain unpopulated. An unpopulated directory with a verified `SOURCING_BLOCKED.md` is a compliant, ratified state.

---

## 3. Ingestion Conventions & Multi-Topic Topology

* **Multi-Topic State Repository**: Repositories are organized per state (`enacted-state-md`) containing all topics for that state (Land-Use/Zoning, Public Water Quality, PFAS, Data Centers). Topics are directories and tags, never separate repos.
* **Measurement Records**: Public water measurement records live under `water/measurements/<system_slug>/<parameter>_<year>.md with explicit per-system attribution, governing limits, compliance dates, and basis`.
* **Primary Document Hashes**: Every record file includes the full 64-character SHA-256 hash of the source document fetched at generation time (`source_sha256`).
* **Fetch Timestamps**: Every record file includes the actual wall-clock ISO 8601 UTC timestamp of retrieval (`source_fetched_at`).
* **The `LAST_INGESTED` Convention**: Automated feeds and periodic dispatches record the latest ingestion timestamp (`LAST_INGESTED: <ISO timestamp>`).
* **Divergence Rules**: Where a summary page or legislative title diverges from the enacted instrument, the enacted text controls and the divergence is recorded.

---

## 4. News & Journalistic Sourcing Policy (Founder Ruling 2026-09-15)

* **No News Articles or Commentary in Corpus:** News articles, journalistic stories, op-eds, blogs, and press commentary are NEVER linked, quoted, or surfaced in this repository, its syndication feeds, or client dispatches.
* **Internal Operational Trigger Only:** News mentions and public tips serve exclusively as operational triggers to initiate an immediate deterministic poll of the primary government portal. If no primary legislative instrument or official measurement report is found on the official portal, no record is generated.
* **Official Government Press Releases:** Official agency press releases and formal public notices published by government bodies are classified as primary records and may only be ingested under hard provenance rules (HTTP 200, cryptographic SHA-256 hash, ISO timestamp, mechanical quotation).

---

## 5. Syndication Feeds & Demand Surface

* **Syndication Feeds (`feeds/`)**: Published via GitHub Pages at `feeds/<jur>/<topic>.atom|json`, statewide topic aggregates `feeds/topics/<topic>.atom|json`, and master aggregate `feeds/zoning.atom|json`.
* **Request Coverage Surface (`request_coverage.html`)**: Static intake form enabling users to request primary-source coverage for their jurisdiction and topic.
* **Confidential Demand Ledger (`scripts/demand_ledger.py`)**: Generates deterministic weekly internal demand summaries for founder review. Aggregate demand counts are strictly private and never published.

---

## 6. Jurisdiction Directory

| Jurisdiction | Status | Primary Code / Ingestion Framework |
| :--- | :--- | :--- |
| **Statewide** | Populated | Land Use Article (Divisions I & II), Critical Area Program |
| **Anne Arundel** | Populated | Article 18 (Zoning), Council Bills 18-26, 28-26, 57-26; Public Water (PWSID MD0020004, MD0020008, MD0020009) |
| **Baltimore City** | Populated | Article 32 (Zoning), Ordinances 26-128, 26-146 |
| **Baltimore County** | Populated | BCZR, Council Bills 9-26, 21-25 |
| **Frederick** | Populated | Chapter 1-19 (Zoning), Council Bills 23-21, 23-20 |
| **Harford** | Populated | Chapter 267 (Zoning Code) |
| **Howard** | Populated | HCZR, Council Bills 25-2026, 24-2026, 04-2026 |
| **Montgomery** | Populated | Chapter 59 (Zoning), Socrata ZTA Feed Index; WSSC Water (PWSID MD0150004) |
| **Prince George's** | Populated | Subtitle 27 (Zoning), Council Bills CB-015-2024, CB-020-2026 |
| **Allegany** | Blocked | `SOURCING_BLOCKED.md` (eCode360) |
| **Calvert** | Blocked | `SOURCING_BLOCKED.md` (eCode360) |
| **Caroline** | Blocked | `SOURCING_BLOCKED.md` (eCode360) |
| **Carroll** | Blocked | `SOURCING_BLOCKED.md` (American Legal Publishing) |
| **Cecil** | Blocked | `SOURCING_BLOCKED.md` (eCode360) |
| **Charles** | Blocked | `SOURCING_BLOCKED.md` (eCode360) |
| **Dorchester** | Blocked | `SOURCING_BLOCKED.md` (No countywide code / General Code) |
| **Garrett** | Blocked | `SOURCING_BLOCKED.md` (No countywide code / AmLegal) |
| **Kent** | Blocked | `SOURCING_BLOCKED.md` (eCode360) |
| **Queen Anne's** | Blocked | `SOURCING_BLOCKED.md` (eCode360) |
| **Somerset** | Blocked | `SOURCING_BLOCKED.md` (No online primary portal / eCode360) |
| **St. Mary's** | Blocked | `SOURCING_BLOCKED.md` (Municode) |
| **Talbot** | Blocked | `SOURCING_BLOCKED.md` (eCode360) |
| **Washington** | Blocked | `SOURCING_BLOCKED.md` (eCode360) |
| **Wicomico** | Blocked | `SOURCING_BLOCKED.md` (eCode360) |
| **Worcester** | Blocked | `SOURCING_BLOCKED.md` (eCode360) |
