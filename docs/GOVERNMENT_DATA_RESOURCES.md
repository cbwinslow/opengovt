# Government Data Resources and Repositories

This document provides a comprehensive list of repositories, APIs, and resources related to OpenStates, OpenLegislation, Congress.gov, GovInfo.gov, and related government data sources for the OpenDiscourse.net project.

## Table of Contents
- [OpenStates Resources](#openstates-resources)
- [OpenLegislation Resources](#openlegislation-resources)
- [Congress.gov & API.Congress.gov](#congressgov--apicongressgov)
- [GovInfo.gov](#govinfoagov)
- [Related Projects & Tools](#related-projects--tools)
- [Data Models Overview](#data-models-overview)
- [API Documentation Links](#api-documentation-links)

---

## OpenStates Resources

### Official Repositories
- **OpenStates API & Core**: https://github.com/openstates/openstates-core
  - Main repository for OpenStates core functionality
  - Python library for accessing state legislative data
  - Data models for bills, legislators, votes, committees

- **OpenStates Scrapers**: https://github.com/openstates/openstates-scrapers
  - State-specific scrapers for all 50 states + DC, PR, VI
  - Individual scrapers per jurisdiction
  - Used to collect and normalize state legislative data

- **OpenStates GraphQL API**: https://github.com/openstates/openstates-graphql
  - Modern GraphQL API for accessing OpenStates data
  - Query interface for bills, people, votes, committees

### Data Access
- **OpenStates Downloads**: https://openstates.org/downloads/
  - Bulk data downloads for each state
  - JSON format, updated regularly
  - Historical and current legislative session data

- **OpenStates API Documentation**: https://docs.openstates.org/
  - REST and GraphQL API documentation
  - Data models and entity relationships
  - Rate limits and authentication

- **Plural Mirror**: https://open.pluralpolicy.com/data/
  - Alternative mirror for OpenStates bulk data
  - Per-state ZIP files with complete legislative data

### Data Model Components
- **Bills**: Bill text, sponsors, actions, versions, votes
- **Legislators**: Bio, contact info, party, district, roles
- **Votes**: Roll call votes with individual member positions
- **Committees**: Committee membership and hearings
- **Sessions**: Legislative session information

---

## OpenLegislation Resources

### New York OpenLegislation
- **NY Senate OpenLegislation**: https://github.com/nysenate/OpenLegislation
  - New York State legislative data platform
  - Full-text bill search and API
  - Comprehensive NY legislative database

- **API Documentation**: https://legislation.nysenate.gov/static/docs/html/
  - REST API for NY legislative data
  - Bill status, amendments, votes, calendars
  - JSON response format

### Other State OpenLegislation Projects
- **California LegInfo**: https://leginfo.legislature.ca.gov/
  - California legislative information
  - Bill tracking and full text
  - No official GitHub repo but has public API

- **Texas Legislature Online**: https://capitol.texas.gov/
  - Texas legislative information
  - Bill search and tracking

---

## Congress.gov & API.Congress.gov

### Official Congress.gov Resources
- **Congress.gov API**: https://api.congress.gov/
  - Official API for federal legislative data
  - Requires API key (free registration)
  - JSON format responses

- **API Documentation**: https://github.com/LibraryOfCongress/api.congress.gov
  - Official documentation repository
  - Examples and use cases
  - Data models and endpoints

### API Endpoints (api.congress.gov)
- **/bill**: Bill information, actions, cosponsors
- **/amendment**: Amendment details
- **/member**: Member information and sponsored bills
- **/committee**: Committee information and reports
- **/nomination**: Presidential nominations
- **/treaty**: Treaty information
- **/congressional-record**: Congressional Record entries
- **/summaries**: Bill summaries

### Congress.gov Data Structure
- Bills organized by Congress number (e.g., 118th Congress)
- Chamber designation (House: H.R., S., Senate: S.)
- Bill status tracking through legislative process
- Sponsor and cosponsor relationships
- Actions timeline with dates

---

## GovInfo.gov

### Bulk Data Repository
- **GovInfo Bulk Data**: https://www.govinfo.gov/bulkdata/
  - Official bulk data from U.S. Government Publishing Office
  - XML format (BillStatus, BILLS, CREC, etc.)
  - Comprehensive historical archives

### Available Collections
- **BILLS**: Full bill text in XML format
- **BILLSTATUS**: Bill metadata and status tracking
- **CREC**: Congressional Record (daily proceedings)
- **PLAW**: Public Laws (enacted legislation)
- **STATUTE**: United States Statutes at Large
- **ROLLCALLVOTE**: Roll call vote data
- **CHRG**: Committee hearings
- **CPRT**: Committee prints
- **CRPT**: Committee reports

### GovInfo Repositories
- **GovInfo Link Service**: https://www.govinfo.gov/link-docs
  - Persistent URLs for government documents
  - Link resolution service

- **Sitemap**: https://www.govinfo.gov/sitemaps/bulkdata/
  - Index of all available bulk data
  - Updated daily with new content

### Data Access Methods
- Direct ZIP file downloads (per Congress/collection)
- Individual XML file access via HTTPS
- Sitemap crawling for discovery
- FTP access (legacy, being phased out)

---

## Related Projects & Tools

### unitedstates Project
- **congress-legislators**: https://github.com/unitedstates/congress-legislators
  - Comprehensive historical and current legislator data
  - YAML and JSON formats
  - Biographical info, terms, committee assignments
  - Social media accounts

- **congress**: https://github.com/unitedstates/congress
  - Tools for downloading and parsing congressional data
  - Bill status, votes, amendments
  - Works with govinfo data

### GovTrack
- **GovTrack.us**: https://www.govtrack.us/
  - Citizen-facing legislative tracking site
  - Bulk data exports available

- **GovTrack Data**: https://www.govtrack.us/developers/data
  - CSV exports of votes
  - Per-congress data directories
  - Bill relationships and cosponsorship networks

### ProPublica Congress API
- **ProPublica Congress API**: https://projects.propublica.org/api-docs/congress-api/
  - Alternative API for congressional data
  - Member voting records and statements
  - Committee information
  - Recent votes and bills

### Comparative Legislatures
- **Comparative Agendas Project**: https://www.comparativeagendas.net/
  - Codebook for policy topics
  - Multi-country legislative coding schemes

### Policy Analysis Tools
- **LegiScan**: https://legiscan.com/
  - State legislative tracking
  - API for state bill data
  - All 50 states plus Congress

- **Quorum**: https://www.quorum.us/
  - Commercial legislative tracking and analytics
  - Federal and state coverage

---

## Data Models Overview

### Common Entity Types Across Sources

#### Person/Legislator
```python
{
  "id": "unique_identifier",
  "source": "openstates|congress|govinfo",
  "source_id": "source_specific_id",
  "name": "Full Name",
  "given_name": "First",
  "family_name": "Last",
  "birth_date": "YYYY-MM-DD",
  "party": "Democrat|Republican|Independent",
  "state": "State code",
  "district": "District number or 'Senate'",
  "chamber": "upper|lower|house|senate",
  "roles": [{"term_start": "date", "term_end": "date", "role": "Senator|Representative"}],
  "contact": {"email": "", "phone": "", "office": ""},
  "social_media": {"twitter": "", "facebook": ""},
  "bioguide_id": "Bioguide ID (federal only)",
  "openstates_id": "OpenStates ID (state only)"
}
```

#### Bill
```python
{
  "id": "unique_identifier",
  "source": "openstates|congress|govinfo",
  "source_id": "bill_identifier",
  "jurisdiction": "US|NY|CA etc.",
  "session": "session_identifier",
  "chamber": "house|senate|assembly|upper|lower",
  "bill_number": "HR1234|S456|AB789",
  "title": "Official title",
  "summary": "Bill summary",
  "introduced_date": "YYYY-MM-DD",
  "status": "introduced|passed|enacted|failed",
  "sponsors": [{"person_id": "", "role": "primary|cosponsor"}],
  "actions": [{"date": "", "description": "", "type": ""}],
  "versions": [{"url": "", "type": "Introduced|Engrossed|Enrolled"}],
  "subjects": ["Healthcare", "Education"],
  "full_text_url": "URL to text"
}
```

#### Vote
```python
{
  "id": "unique_identifier",
  "source": "openstates|congress|govinfo",
  "source_id": "vote_identifier",
  "bill_id": "associated_bill_id",
  "chamber": "house|senate",
  "date": "YYYY-MM-DD HH:MM:SS",
  "motion": "Description of vote motion",
  "result": "passed|failed",
  "vote_counts": {"yes": 0, "no": 0, "present": 0, "absent": 0},
  "votes": [{"person_id": "", "vote": "yes|no|present|absent"}]
}
```

#### Committee
```python
{
  "id": "unique_identifier",
  "source": "openstates|congress",
  "chamber": "house|senate|joint",
  "name": "Committee on ...",
  "parent_id": "parent_committee_id (for subcommittees)",
  "members": [{"person_id": "", "role": "chair|vice_chair|member"}]
}
```

### SQL Schema Relationships
- `persons` table: Central entity for all legislators/members
- `bills` table: Legislative proposals with foreign keys to jurisdiction and session
- `sponsors` table: Many-to-many between bills and persons
- `actions` table: Timeline of bill actions
- `votes` table: Vote events with foreign keys to bills
- `vote_records` table: Individual member votes
- `bill_texts` table: Full text storage with version types
- `jurisdictions` table: Federal, state, territory designations
- `sessions` table: Legislative sessions per jurisdiction

---

## API Documentation Links

### OpenStates
- **Main Docs**: https://docs.openstates.org/
- **API Reference**: https://v3.openstates.org/docs
- **Data Dictionary**: https://docs.openstates.org/en/latest/data/index.html

### Congress.gov API
- **Getting Started**: https://api.congress.gov/
- **GitHub Docs**: https://github.com/LibraryOfCongress/api.congress.gov
- **Sign Up**: https://api.congress.gov/sign-up/

### GovInfo.gov
- **Bulk Data Guide**: https://www.govinfo.gov/bulkdata/
- **Developer Resources**: https://www.govinfo.gov/developers
- **Link Service**: https://www.govinfo.gov/link-docs
- **Sitemap Documentation**: https://www.govinfo.gov/sitemap_index.xml

### GovTrack
- **Data Documentation**: https://www.govtrack.us/developers
- **API**: https://www.govtrack.us/developers/api

### ProPublica
- **Congress API**: https://projects.propublica.org/api-docs/congress-api/

### The United States Project
- **Legislators Data**: https://github.com/unitedstates/congress-legislators
- **Congress Tools**: https://github.com/unitedstates/congress

---

## Data Collection Strategy for OpenDiscourse.net

### 1. Federal Data (Congress)
- Primary: api.congress.gov API
- Bulk: GovInfo.gov bulk data (BILLSTATUS, BILLS, ROLLCALLVOTE)
- Legislators: theunitedstates.io congress-legislators
- Supplemental: GovTrack bulk exports

### 2. State Data (50 States + Territories)
- Primary: OpenStates bulk downloads
- Per-state: Individual state legislature websites where OpenStates coverage gaps exist
- Legislators: OpenStates people data

### 3. Update Frequency
- Federal: Daily updates from api.congress.gov
- Bulk: Weekly bulk downloads from OpenStates
- Historical: One-time bulk ingestion from GovInfo.gov archives

### 4. Data Unification
- Use universal schema (see `congress_api/universal_ingest.py`)
- Map source-specific IDs to unified person and bill identifiers
- Maintain source and source_id fields for traceability
- Normalize jurisdiction (federal vs state) and session identifiers

---

## Next Steps for Implementation

1. **Data Ingestion Pipeline**
   - Implement universal_ingest.py for all sources
   - Schedule regular updates
   - Handle incremental updates vs full refreshes

2. **Data Model Classes**
   - Create Python classes for each entity type
   - Implement serialization/deserialization
   - Add validation and business logic

3. **Analysis Modules**
   - NLP: spaCy processing pipeline
   - Embeddings: Sentence transformers for bill vectorization
   - Sentiment: Multi-model sentiment analysis
   - Entity Attribution: NER and resolution
   - Bias Detection: Political bias classification
   - Consistency Tracking: Voting record analysis

4. **Database Schema**
   - Extend schema for analysis results
   - Add embeddings storage (vector columns)
   - Create indexes for common query patterns
   - Set up materialized views for aggregations

5. **API Development**
   - REST API for accessing processed data
   - GraphQL endpoint for complex queries
   - Real-time updates via WebSocket

---

## References & Further Reading

- **Congressional Data Handbook**: https://www.congress.gov/help
- **OpenStates Methodology**: https://docs.openstates.org/en/latest/contributing/scrapers.html
- **Legislative Process**: https://www.congress.gov/legislative-process
- **Bill Status Codes**: https://www.congress.gov/help/field-values/bill-status
- **Federal Register**: https://www.federalregister.gov/developers/api/v1
- **Data.gov Congress Datasets**: https://catalog.data.gov/dataset?q=congress

---

*Last Updated: 2025-10-14*
*Maintained for the OpenDiscourse.net project*
