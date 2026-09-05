# Legal Provenance & Ingestion Specifications: Maryland Corpus

**Repository:** `enacted-state-md`  
**Parent Entity:** Swapp Technologies LLC (Organized in Maryland)  
**Corpus Scope:** Primary Government Records of Enacted Maryland Land-Use & Zoning Law  

---

## 1. The Hard Generation Rule (Record Integrity)

No legislative record file exists in this repository without a primary government source document fetched at generation time (HTTP 200), verified by cryptographic hash and recorded timestamp. Quoted statutory text is mechanically extracted from the fetched document, never drafted from memory.

### Required Record Metadata Fields
Every legislative record file in `council_bills/`, `zta_amendments/`, and `zoning_code/` carries structured YAML frontmatter:
* `primary_source_url`: The canonical government legislative matter or portal URL.
* `source_pdf`: Direct download URL of the primary enacted instrument.
* `source_sha256`: Cryptographic SHA-256 hash of the exact binary payload fetched at generation time.
* `source_fetched_at`: Actual wall-clock ISO 8601 UTC timestamp of the retrieval that produced `source_sha256`.
* `action_status`: Legislative status (`Enacted`, `Adopted`, `Introduced`, `Worksession`, `Withdrawn`, `Vetoed`). Unknown dates render `[pending verification]`, never null.
* `effective_date`: Authoritative date the enactment takes legal effect. Where split effective dates apply (e.g. base bill vs. veto-override provisions), each is specifically enumerated.

---

## 2. Authoritative Primary Sourcing & Hard Aggregator Blocklist

All corpus records are ingested exclusively from official government portals:
* **Statewide:** Maryland General Assembly (`mgaleg.maryland.gov`)
* **Municipal/County Councils:** Official county council legislative portals (e.g., Montgomery County Council & Socrata Open Data, Anne Arundel County Council, Howard County Council OLIS, Baltimore City Council Legistar, Baltimore County Council, Frederick County Council, Prince George's County Council Legistar, Harford County Department of Planning and Zoning).

### Hard Blocklist
Third-party code aggregators and commercial publishers are strictly prohibited from serving as sources:
* `municode.com` (CivicPlus / Municode)
* `amlegal.com` (American Legal Publishing)
* `ecode360.com` (General Code)

---

## 3. SOURCING_BLOCKED.md Invariant

A jurisdiction whose code lives exclusively on blocklisted third-party aggregators is recorded as `SOURCING_BLOCKED.md` (documenting the portals checked, timestamps, and municipal contacts) and left empty of legislative markdown files.

Under repository integrity rules, an empty jurisdiction with an authoritative `SOURCING_BLOCKED.md` file is a **passing compliance outcome**, never a gap to paper over.
