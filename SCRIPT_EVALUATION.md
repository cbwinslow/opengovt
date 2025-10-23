# OpenGovt Repository - Complete Script Evaluation

**Generated:** October 22, 2025  
**Purpose:** Comprehensive analysis of all scripts, functions, and their interactions

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Core Architecture](#core-architecture)
3. [Module-by-Module Analysis](#module-by-module-analysis)
4. [Data Flow and Interactions](#data-flow-and-interactions)
5. [Function Reference](#function-reference)
6. [Dependencies and Relationships](#dependencies-and-relationships)
7. [Entry Points](#entry-points)

---

## Executive Summary

### Repository Overview

This repository contains **46 Python scripts** totaling **~16,000 lines of code** organized into a comprehensive government data ingestion and analysis framework. The codebase is divided into several major subsystems:

1. **Data Ingestion Pipeline** (`cbw_*.py` modules) - Downloads and processes legislative data
2. **Analysis Framework** (`analysis/`) - NLP, sentiment, bias detection, embeddings
3. **Data Models** (`models/`) - OOP representations of bills, votes, people, committees
4. **API Integration** (`congress_api/`) - Multiple pipeline implementations
5. **Examples** (`examples/`) - Working demonstrations of analysis capabilities
6. **Automation Scripts** (`.github/scripts/`) - AI-powered code review and documentation

### Key Statistics

- **Total Python Files:** 46
- **Total Lines of Code:** ~16,000
- **Classes Defined:** 45+
- **Functions Defined:** 200+
- **External APIs Integrated:** 10+
- **Database Tables:** 12 analysis tables + 4 views

---

## Core Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    EXTERNAL DATA SOURCES                     │
├──────────────────┬──────────────────┬──────────────────────┤
│ Congress.gov API │ GovInfo.gov      │ OpenStates           │
│ ProPublica API   │ GovTrack         │ TheUnitedStates.io   │
└──────────────────┴──────────────────┴──────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              CBW INGESTION PIPELINE (cbw_*.py)               │
├─────────────────────────────────────────────────────────────┤
│ cbw_discovery → cbw_validator → cbw_downloader →            │
│ cbw_extractor → cbw_parser → cbw_db                         │
│                                                              │
│ Support: cbw_config, cbw_utils, cbw_retry, cbw_http         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  POSTGRESQL DATABASE                         │
├─────────────────────────────────────────────────────────────┤
│ Core Tables: bills, votes, legislators, committees          │
│ Analysis Tables: embeddings, sentiment, bias, consistency   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              ANALYSIS MODULES (analysis/)                    │
├─────────────────────────────────────────────────────────────┤
│ embeddings.py → Vector representations (384-768 dims)       │
│ sentiment.py → VADER, TextBlob, DistilBERT analysis         │
│ nlp_processor.py → spaCy entity extraction & NLP            │
│ bias_detector.py → Political bias detection                 │
│ consistency_analyzer.py → Voting pattern analysis           │
└─────────────────────────────────────────────────────────────┘
```

---

## Module-by-Module Analysis

### 1. Core Ingestion Pipeline (cbw_*.py)

#### cbw_main.py (186 lines)
**Purpose:** Main entrypoint and orchestrator for the entire pipeline

**Key Functions:**
- `parse_args()` - CLI argument parsing (start/end congress, flags, DB config)
- `main()` - Orchestrates the entire pipeline execution

**Interactions:**
- Imports all other cbw_* modules
- Creates instances: Config, DiscoveryManager, Validator, DownloadManager, Extractor, ParserNormalizer, DBManager, RetryManager, HTTPControlServer
- Coordinates workflow: discovery → validation → download → extract → postprocess → serve

**Flow:**
1. Parse CLI arguments
2. Create Config object
3. Run discovery to build URL list
4. Optionally validate URLs
5. Download files with retry logic
6. Extract archives
7. Parse and ingest into database
8. Optionally start HTTP control server

---

#### cbw_config.py (54 lines)
**Purpose:** Centralized configuration management

**Classes:**
- `Config` - Configuration container with sensible defaults

**Key Functions:**
- `now_congress()` - Calculate current congress number from date (formula: 1 + (year - 1789) / 2)

**Attributes:**
- `start_congress`, `end_congress` - Congress range
- `outdir`, `bulk_json`, `retry_json` - File paths
- `concurrency`, `retries` - Download parameters
- `collections` - Filter specific data collections
- `do_discovery` - Enable/disable active discovery
- `db_url` - PostgreSQL connection string

**Interactions:** Used by all other modules to access configuration

---

#### cbw_utils.py (141 lines)
**Purpose:** Shared utilities, logging, decorators, JSON helpers

**Key Functions:**
- `configure_logger(name, level)` - Creates rotating file logger with console output
- `adapter_for(logger, label)` - Returns LoggerAdapter with labeled output
- `save_json_atomic(path, data)` - Atomic JSON write (tmp file + rename)
- `load_json_safe(path)` - Load JSON with corruption handling (moves corrupt files)
- `ensure_dirs(*paths)` - Create directories if they don't exist

**Decorators:**
- `@labeled(label)` - Logs entry/exit/duration/exceptions for sync functions
- `@trace_async(label)` - Async version of labeled decorator

**Interactions:** Used by ALL other cbw_ modules for logging and utilities

---

#### cbw_discovery.py (169 lines)
**Purpose:** Discovers and generates URLs for bulk data sources

**Classes:**
- `DiscoveryManager` - Discovers URLs from multiple sources

**Key Functions:**
- `expand_govinfo_templates()` - Expands URL templates across congress range
  - Templates: billstatus, rollcall, bills, plaw, crec
  - Chambers: hr, house, h, senate, s
- `discover_govinfo_index()` - Crawls govinfo.gov index for actual files
- `discover_govtrack()` - Crawls GovTrack.us for bulk data
- `discover_openstates()` - Discovers OpenStates data (downloads page + mirror)
- `build()` - Aggregates all discovered URLs into single dict

**Data Sources:**
- GovInfo.gov bulk data API
- GovTrack.us
- OpenStates.org and mirror
- TheUnitedStates.io legislators

**Output:** Dict with keys:
- `govinfo_templates_expanded`
- `govinfo_index_discovered`
- `govtrack`
- `openstates`
- `congress_legislators`
- `aggregate_urls` - Deduplicated list of all URLs

**Interactions:**
- Uses `cbw_config.Config` for congress range and collections
- Uses `cbw_utils` for logging
- Called by `cbw_main` and `app/pipeline.py`

---

#### cbw_validator.py (48 lines)
**Purpose:** Validates URLs before downloading to save bandwidth

**Classes:**
- `Validator` - Performs HEAD/GET checks on URLs

**Key Functions:**
- `head_ok(url)` - Checks if URL is reachable (HEAD request, fallback to GET)
- `filter_list(urls)` - Filters list to only reachable URLs

**Logic:**
1. Try HEAD request first
2. If HEAD fails or returns 4xx, try small GET request
3. Return True if status < 400

**Interactions:**
- Used by `cbw_main` if `--validate` flag is set
- Standalone utility, no complex dependencies

---

#### cbw_downloader.py (130 lines)
**Purpose:** Async concurrent downloader with resume support and retry logic

**Classes:**
- `DownloadManager` - Manages async downloads with aiohttp

**Key Functions:**
- `_head_info(session, url)` - Gets Content-Length and Accept-Ranges headers
- `_download_single(session, url, dest)` - Downloads single file with:
  - Resume capability (Range header)
  - Retry logic with exponential backoff
  - Progress bars via tqdm
- `download_all(urls)` - Synchronous facade that runs async batch download

**Features:**
- Concurrent downloads (configurable concurrency)
- Resume partially downloaded files
- Automatic retry with backoff (2^attempt seconds, max 30s)
- Progress bars for each download
- Organizes downloads by domain into subdirectories

**Interactions:**
- Requires `aiohttp` library
- Uses `cbw_utils` for logging and directory management
- Returns list of result dicts: `{url, path, ok, bytes, error}`
- Called by `cbw_main` if `--download` flag is set

---

#### cbw_extractor.py (48 lines)
**Purpose:** Extract ZIP and TAR archives

**Classes:**
- `Extractor` - Extracts archives into `<filename>_extracted` directories

**Key Functions:**
- `extract(archive_path, remove_archive)` - Extracts ZIP or TAR files

**Supported Formats:**
- ZIP files (.zip)
- TAR files (.tar, .tar.gz, .tgz)

**Logic:**
1. Create extraction directory (`archive_path + "_extracted"`)
2. Detect format (zipfile.is_zipfile or tarfile.open)
3. Extract all contents
4. Optionally remove original archive
5. Return result dict: `{ok, dest, error}`

**Interactions:**
- Called by `cbw_main` if `--extract` flag is set
- Processes download results from `cbw_downloader`

---

#### cbw_parser.py (103 lines)
**Purpose:** Conservative parsers for XML and JSON legislative files

**Classes:**
- `ParserNormalizer` - Parses bills, votes, and legislators

**Key Functions:**
- `parse_billstatus(xml_path)` - Extracts bill metadata from XML
  - Fields: bill_number, title, sponsor, introduced_date
  - Uses lxml with XPath queries
- `parse_rollcall(xml_path)` - Extracts vote metadata from XML
  - Fields: vote_id, result, date
- `parse_legislators(json_path)` - Parses legislators JSON
  - Fields: name, bioguide, current_party, state

**Design Philosophy:**
- "Conservative" - extracts only common, reliable fields
- Namespace-agnostic XPath queries
- Graceful degradation if lxml not installed
- Returns None or empty list on parse failure

**Interactions:**
- Requires `lxml` for XML parsing (optional)
- Uses `cbw_utils` for logging
- Output consumed by `cbw_db.DBManager`

---

#### cbw_db.py (104 lines)
**Purpose:** Database manager for PostgreSQL operations

**Classes:**
- `DBManager` - Handles DB migrations and upserts

**Key Functions:**
- `connect()` - Establishes psycopg2 connection
- `run_migrations()` - Executes embedded SQL migrations
- `upsert_bill(rec, congress, chamber)` - Inserts or updates bill
- `upsert_vote(rec, congress, chamber)` - Inserts or updates vote
- `upsert_legislator(rec)` - Inserts or updates legislator
- `close()` - Closes DB connection

**Features:**
- UPSERT operations (INSERT ... ON CONFLICT DO UPDATE)
- Unique constraints: (congress, chamber, bill_number), (congress, chamber, vote_id), (bioguide)
- Embedded migration support
- Transaction management with rollback on error

**Schema (from cbw_main.py):**
```sql
TABLE bills (id, source_file, congress, chamber, bill_number, title, sponsor, introduced_date, inserted_at)
TABLE votes (id, source_file, congress, chamber, vote_id, vote_date, result, inserted_at)
TABLE legislators (id, name, bioguide, current_party, state, inserted_at)
```

**Interactions:**
- Requires `psycopg2-binary`
- Used by `cbw_main` if `--postprocess` and `--db` flags are set
- Consumes parsed data from `cbw_parser`

---

#### cbw_retry.py (52 lines)
**Purpose:** Manages retry logic for failed downloads

**Classes:**
- `RetryManager` - Tracks failed URLs with attempt counts

**Key Functions:**
- `_load()` - Loads retry report from JSON
- `add(url, error)` - Adds or updates failure record
- `list_to_retry(max_attempts)` - Returns URLs eligible for retry
- `remove(url)` - Removes URL from failure list

**Data Structure:**
```json
{
  "failures": [
    {
      "url": "...",
      "attempts": 3,
      "first_failed": "2025-10-22T...",
      "last_attempted": "2025-10-22T...",
      "last_error": "HTTP 404"
    }
  ]
}
```

**Interactions:**
- Uses `cbw_utils` for atomic JSON operations
- Called by `cbw_main` to record download failures
- Enables retry scheduling for transient failures

---

#### cbw_http.py (85 lines)
**Purpose:** HTTP control server for TUI and automation

**Classes:**
- `HTTPControlServer` - aiohttp web server with control endpoints

**Endpoints:**
- `GET /status` - Returns discovery timestamp and retry count
- `POST /start` - Starts async pipeline run (download + extract)
- `POST /retry` - Retries failed downloads
- `GET /health` - Health check (returns "ok")
- `GET /metrics` - Prometheus metrics (if prometheus_client installed)

**Key Functions:**
- `make_app()` - Creates aiohttp application with routes
- `handle_status()`, `handle_start()`, `handle_retry()`, `handle_health()` - Route handlers
- `start()` - Starts server
- `stop()` - Stops server gracefully

**Interactions:**
- Requires `aiohttp` and optionally `prometheus_client`
- Takes Pipeline instance as parameter
- Called by `cbw_main` if `--serve` flag is set
- Enables Go TUI integration

---

### 2. Alternative Pipeline Implementations

The repository contains **multiple implementations** of the same pipeline concept for different use cases:

#### Simple Implementations

**congress_bulk_ingest.py (179 lines)**
- Purpose: Simple, self-contained ingestion script
- All-in-one script with no class organization
- Synchronous operations, no retry logic, no database
- Good for simple batch jobs

**congress_bulk_ingest_all.py (484 lines)**
- Extended version with more data sources
- Adds `discover_data_gov_ckan()` for data.gov CKAN API
- Still function-based but more comprehensive

**congress_bulk_ingest_full.py (594 lines)**
- Full-featured functional implementation
- Better error handling and logging
- Collection filtering support

#### Object-Oriented Implementations

**congress_pipeline_oop.py (768 lines)**
- Full OOP design with classes for each component
- Self-contained in single file
- Similar to cbw_* modules

**congress_full_pipeline.py (1,219 lines)**
- Most comprehensive standalone implementation
- Includes HTTPControlServer and Prometheus stubs
- All utilities inline (logging, decorators, JSON helpers)
- Complete end-to-end solution

**congress_bulk_pipeline.py (772 lines)**
- Includes DB schema management
- Post-processing and ingestion
- Retry scheduling with intervals

#### Congress API Implementations (congress_api/)

**congress_api/universal_ingest.py (765 lines)**
- Universal data ingest from multiple sources
- Flexible data source configuration
- Unified parsing interface

**congress_api/cbw_universal_pipeline.py (1,415 lines)**
- Most comprehensive pipeline
- Interactive console mode
- Advanced retry logic

**congress_api/cbw_universal_single_refine.py (552 lines)**
- Refined single-source ingestion
- Optimized for specific use cases

**congress_api/congress_pipeline_oop.py & congress_full_pipeline.py**
- Duplicates of root versions
- Allow import from congress_api package

---

### 3. Application Layer (app/)

#### app/run.py (61 lines)
**Purpose:** Application entrypoint wrapper
- Thin CLI wrapper around Pipeline class
- Imports from `app.pipeline`

#### app/pipeline.py (368 lines)
**Purpose:** Application-level pipeline implementation
- Classes: DiscoveryManager, Validator, DownloadManager, Extractor, ParserNormalizer, RetryManager, Pipeline
- Similar structure to cbw_* modules
- Application-specific organization

#### app/utils.py (129 lines)
**Purpose:** Application utilities (similar to cbw_utils.py)
- Adds `json_logs` parameter for structured logging
- Adds `rotate_logs(keep_days)` function
- Otherwise identical to cbw_utils.py

#### app/db.py (102 lines)
**Purpose:** Database operations
- `run_migrations(conn_str, migrations_dir)` - Runs SQL from directory
- `DBIngestor` class with connect/close and upsert methods
- Migration directory support vs embedded migrations

---

### 4. Data Models (models/)

#### models/person.py (225 lines)
**Classes:**
- `Person` - Represents any person in political system
  - Fields: id, source, source_id, name, given_name, family_name, gender, birth_date, image_url
  - Methods: `to_dict()`, `from_dict()`
  
- `Member` - Legislative member (extends Person concept)
  - Fields: person_id, jurisdiction_id, chamber, district, party, start_date, end_date, current
  - Tracks historical membership records

#### models/bill.py (297 lines)
**Classes:**
- `Bill` - Legislative bill
  - Fields: bill_number, chamber, title, summary, status, subjects, policy_areas
  - Supports Congress.gov, OpenStates, etc.

- `BillAction` - Actions taken on bills
  - Fields: bill_id, action_date, description, action_code, chamber

- `BillText` - Bill text versions
  - Fields: bill_id, version, text, html_url, pdf_url, published_date

- `BillSponsorship` - Sponsors/cosponsors
  - Fields: bill_id, person_id, sponsor_type, is_original_sponsor

#### models/vote.py (170 lines)
**Classes:**
- `Vote` - Legislative vote
  - Fields: bill_id, chamber, vote_date, motion_text, result, vote_type, tallies

- `VoteRecord` - Individual legislator vote
  - Fields: vote_id, person_id, vote_option, vote_weight

#### models/committee.py (130 lines)
**Classes:**
- `Committee` - Legislative committee
  - Fields: name, chamber, committee_type, parent_committee_id

- `CommitteeMembership` - Member-committee relationship
  - Fields: committee_id, person_id, role, start_date, end_date

#### models/jurisdiction.py (139 lines)
**Classes:**
- `Jurisdiction` - Federal or state government
  - Fields: jurisdiction_type, name, state_code, classification

- `Session` - Legislative session
  - Fields: jurisdiction_id, identifier, name, start_date, end_date

---

### 5. Analysis Modules (analysis/)

#### analysis/embeddings.py (339 lines)
**Purpose:** Vector embeddings for semantic analysis

**Classes:**
- `BillEmbeddings` - Embedding container
  - Fields: bill_id, model_name, embedding_vector (numpy array), text_hash
  
- `SpeechEmbeddings` - Speech embedding container
  
- `EmbeddingsGenerator` - Main generator
  - Models: all-MiniLM-L6-v2 (default, 384 dims), legal-bert-base-uncased (768 dims)
  - Methods: `encode()`, `encode_bill()`, `encode_speech()`
  - GPU acceleration support

**Functions:**
- `create_embeddings(texts, model_name)` - Helper
- `compute_bill_similarity_matrix(embeddings)` - Cosine similarity

**Use Cases:**
- Find similar bills
- Topic clustering
- Semantic search
- Politician comparison

---

#### analysis/sentiment.py (358 lines)
**Purpose:** Sentiment analysis of political text

**Classes:**
- `SentimentScore` - Results container
  - Fields: compound_score, positive/negative/neutral scores, sentiment_label, confidence

- `SentimentAnalyzer` - Multi-model analyzer
  - Models: vader (best for political text), textblob, transformers (DistilBERT)
  - Methods: `analyze()`, `batch_analyze()`

**Outputs:**
- Scores: -1 (negative) to 1 (positive)
- Classification: positive, negative, neutral
- Confidence scores

---

#### analysis/nlp_processor.py (373 lines)
**Purpose:** NLP processing with spaCy

**Classes:**
- `Entity` - Named entity
  - Fields: text, label, start, end, confidence

- `ProcessedText` - NLP results
  - Fields: tokens, pos_tags, entities, noun_chunks, key_phrases, sentences

- `NLPProcessor` - spaCy processor
  - Models: en_core_web_sm, en_core_web_lg
  - Methods: `process()`, `extract_entities()`, `extract_key_phrases()`, `batch_process()`

**Capabilities:**
- NER: PERSON, ORG, GPE, LOC, LAW, DATE, MONEY
- POS tagging
- Dependency parsing
- Noun phrase extraction
- Key phrase extraction (TextRank)

---

#### analysis/bias_detector.py (349 lines)
**Purpose:** Political bias detection

**Classes:**
- `BiasScore` - Results
  - Fields: bias_score (-1 to 1), objectivity_score, loaded_language_count

- `BiasDetector` - Analyzer
  - Methods: rule_based and ml-based (future)
  - Detects loaded language, framing

**Bias Indicators:**
- Left keywords: progressive, reform, equality
- Right keywords: conservative, traditional, liberty
- Loaded language detection
- Framing analysis

---

#### analysis/consistency_analyzer.py (406 lines)
**Purpose:** Voting consistency analysis

**Classes:**
- `ConsistencyScore` - Results
  - Fields: overall_consistency, party_line_percentage, flip_flop_count, bipartisan_score

- `VoteRecord` - Vote representation

- `ConsistencyAnalyzer` - Calculator
  - Methods: `analyze_person()`, `calculate_party_line()`, `detect_flip_flops()`, `compare_politicians()`

**Metrics:**
- Overall consistency (0-100%)
- Party-line voting %
- Flip-flop detection
- Bipartisan score
- Inter-politician similarity

---

### 6. Examples (examples/)

#### examples/embeddings_example.py (304 lines)
**Purpose:** Demonstrates embedding generation and similarity search

**Workflow:**
1. Connect to database
2. Fetch bills
3. Generate embeddings (all-MiniLM-L6-v2)
4. Store embeddings
5. Find similar bills (cosine similarity)
6. Store and display results

#### examples/complete_analysis_pipeline.py (420 lines)
**Purpose:** Comprehensive analysis demonstration

**Classes:**
- `PoliticalAnalysisPipeline` - Complete workflow
  - Fetch data (bills, speeches, votes)
  - Generate embeddings
  - Analyze sentiment
  - Extract entities
  - Detect bias
  - Analyze voting consistency
  - Store results

---

### 7. GitHub Automation Scripts (.github/scripts/)

#### .github/scripts/ai-code-review.py (262 lines)
**Purpose:** AI-powered code review
- Security vulnerability detection
- Performance analysis
- Style compliance checking
- Best practice recommendations

#### .github/scripts/ai-test-generator.py (280 lines)
**Purpose:** Automatic test generation
- Unit test generation
- Integration test generation
- Edge case identification

#### .github/scripts/ai-documentation-review.py (297 lines)
**Purpose:** Documentation quality review
- Docstring review
- Completeness checking
- Improvement suggestions

#### .github/scripts/ai-refactor.py (336 lines)
**Purpose:** AI-assisted refactoring
- Code smell detection
- Design pattern suggestions
- Refactoring recommendations

#### .github/scripts/crewai-integration.py (380 lines)
**Purpose:** Multi-agent orchestration
- Agent role definitions
- Task delegation
- Workflow coordination

---

### 8. Additional Scripts

#### congress_bulk_urls.py (368 lines)
**Purpose:** URL generation utility
- Standalone script to generate bulk_urls.json
- Functions: `expand_govinfo_templates()`, `discover_govinfo_index()`, `assemble_bulk_url_dict()`
- Can be run independently for URL discovery

---

## Data Flow and Interactions

### High-Level Data Flow

```
[External APIs] 
    ↓ (HTTP requests)
[cbw_discovery.DiscoveryManager]
    ↓ (generates URL list)
[cbw_validator.Validator]
    ↓ (filters valid URLs)
[cbw_downloader.DownloadManager]
    ↓ (downloads files to disk)
[cbw_extractor.Extractor]
    ↓ (extracts archives)
[cbw_parser.ParserNormalizer]
    ↓ (parses XML/JSON to dicts)
[cbw_db.DBManager]
    ↓ (upserts to PostgreSQL)
[Database Tables]
    ↓ (provides data)
[Analysis Modules]
    ↓ (generates insights)
[Analysis Results Tables]
```

### Module Dependencies

#### Core Pipeline Dependencies
```
cbw_main.py
├── cbw_config.py (Config)
├── cbw_utils.py (logging, decorators, JSON)
├── cbw_discovery.py
│   ├── cbw_config.py
│   └── cbw_utils.py
├── cbw_validator.py
│   └── cbw_utils.py
├── cbw_downloader.py
│   └── cbw_utils.py
├── cbw_extractor.py
│   └── cbw_utils.py
├── cbw_parser.py
│   └── cbw_utils.py
├── cbw_db.py
│   └── cbw_utils.py
├── cbw_retry.py
│   └── cbw_utils.py
└── cbw_http.py
    └── cbw_utils.py
```

#### Analysis Module Dependencies
```
analysis/embeddings.py
├── sentence-transformers (required)
├── torch (optional, for GPU)
└── numpy (required)

analysis/sentiment.py
├── vaderSentiment (optional)
├── textblob (optional)
└── transformers (optional)

analysis/nlp_processor.py
├── spacy (required)
└── pytextrank (optional)

analysis/bias_detector.py
└── (standalone, no external deps)

analysis/consistency_analyzer.py
└── (standalone, no external deps)
```

#### Data Model Interactions
```
Person ←→ Member
  ↓ (person_id)
VoteRecord ←→ Vote
  ↓ (vote_id)
Bill ←→ BillAction
  ↓     BillText
  ↓     BillSponsorship
  ↓
Committee ←→ CommitteeMembership
```

### Database Table Interactions

#### Core Tables (from cbw_main.py)
- `bills` - Referenced by analysis tables
- `votes` - Referenced by consistency_analysis
- `legislators` - Referenced by consistency_analysis, politician_comparisons

#### Analysis Tables (from PROJECT_STRUCTURE.md)
- `bill_embeddings` - Stores 384-768 dim vectors
- `speech_embeddings` - Stores speech vectors
- `sentiment_analysis` - Sentiment scores
- `extracted_entities` - NER results
- `bias_analysis` - Bias scores
- `consistency_analysis` - Voting patterns
- `issue_consistency` - Per-issue patterns
- `position_changes` - Flip-flop tracking
- `bill_similarities` - Similarity matrix
- `text_complexity` - Readability metrics
- `toxicity_analysis` - Hate speech detection
- `politician_comparisons` - Similarity scores

#### Views
- `latest_bill_sentiment` - Latest sentiment per bill
- `latest_bill_bias` - Latest bias per bill
- `politician_consistency_summary` - Aggregated consistency
- `top_similar_bills` - High similarity pairs

---

## Function Reference

### Configuration Functions

| Module | Function | Purpose | Returns |
|--------|----------|---------|---------|
| cbw_config.py | `now_congress()` | Calculate current congress number | int |

### Utility Functions (cbw_utils.py)

| Function | Purpose | Returns |
|----------|---------|---------|
| `configure_logger(name, level)` | Creates rotating file + console logger | logging.Logger |
| `adapter_for(logger, label)` | Creates labeled logger adapter | LoggerAdapter |
| `save_json_atomic(path, data)` | Atomically saves JSON | None |
| `load_json_safe(path)` | Loads JSON with error handling | Any or None |
| `ensure_dirs(*paths)` | Creates directories | None |
| `@labeled(label)` | Decorator for logging | Decorator |
| `@trace_async(label)` | Async logging decorator | Decorator |

### Discovery Functions (cbw_discovery.py)

| Method | Purpose | Returns |
|--------|---------|---------|
| `expand_govinfo_templates()` | Generate URLs from templates | List[str] |
| `discover_govinfo_index()` | Crawl govinfo.gov index | List[str] |
| `discover_govtrack()` | Discover GovTrack data | List[str] |
| `discover_openstates()` | Discover OpenStates data | List[str] |
| `build()` | Aggregate all discovered URLs | Dict[str, Any] |

### Validation Functions (cbw_validator.py)

| Method | Purpose | Returns |
|--------|---------|---------|
| `head_ok(url)` | Check if URL is reachable | bool |
| `filter_list(urls)` | Filter to reachable URLs | List[str] |

### Download Functions (cbw_downloader.py)

| Method | Purpose | Returns |
|--------|---------|---------|
| `_head_info(session, url)` | Get file info | Dict[str, Any] |
| `_download_single(session, url, dest)` | Download with resume/retry | Dict[str, Any] |
| `download_all(urls)` | Batch download | List[Dict[str, Any]] |

### Extraction Functions (cbw_extractor.py)

| Method | Purpose | Returns |
|--------|---------|---------|
| `extract(archive_path, remove_archive)` | Extract ZIP/TAR | Dict[str, Any] |

### Parsing Functions (cbw_parser.py)

| Method | Purpose | Returns |
|--------|---------|---------|
| `parse_billstatus(xml_path)` | Parse bill XML | Dict or None |
| `parse_rollcall(xml_path)` | Parse vote XML | Dict or None |
| `parse_legislators(json_path)` | Parse legislators JSON | List[Dict] |

### Database Functions (cbw_db.py)

| Method | Purpose | Returns |
|--------|---------|---------|
| `connect()` | Establish connection | None |
| `run_migrations()` | Execute migrations | None |
| `upsert_bill(rec, congress, chamber)` | Insert/update bill | int or None |
| `upsert_vote(rec, congress, chamber)` | Insert/update vote | int or None |
| `upsert_legislator(rec)` | Insert/update legislator | int or None |
| `close()` | Close connection | None |

### Retry Functions (cbw_retry.py)

| Method | Purpose | Returns |
|--------|---------|---------|
| `add(url, error)` | Record failure | None |
| `list_to_retry(max_attempts)` | Get retry candidates | List[str] |
| `remove(url)` | Remove from retry list | None |

### HTTP Functions (cbw_http.py)

| Method | Purpose | Returns |
|--------|---------|---------|
| `make_app()` | Create aiohttp app | web.Application |
| `handle_status(request)` | Status endpoint | web.Response |
| `handle_start(request)` | Start pipeline | web.Response |
| `handle_retry(request)` | Retry failures | web.Response |
| `handle_health(request)` | Health check | web.Response |
| `start()` | Start server | None (async) |
| `stop()` | Stop server | None (async) |

### Analysis Functions

#### Embeddings (analysis/embeddings.py)

| Function/Method | Purpose | Returns |
|-----------------|---------|---------|
| `EmbeddingsGenerator.__init__(model_name, device)` | Initialize | None |
| `encode(texts, batch_size, show_progress)` | Generate embeddings | np.ndarray |
| `encode_bill(bill_id, text)` | Create BillEmbeddings | BillEmbeddings |
| `encode_speech(person_id, text)` | Create SpeechEmbeddings | SpeechEmbeddings |
| `create_embeddings(texts, model_name)` | Helper | np.ndarray |
| `compute_bill_similarity_matrix(embeddings)` | Similarity matrix | np.ndarray |

#### Sentiment (analysis/sentiment.py)

| Function/Method | Purpose | Returns |
|-----------------|---------|---------|
| `SentimentAnalyzer.__init__(models)` | Initialize | None |
| `analyze(text, text_id, text_type)` | Analyze sentiment | SentimentScore |
| `batch_analyze(texts, batch_size)` | Batch analysis | List[SentimentScore] |
| `analyze_sentiment(text, model)` | Helper | SentimentScore |

#### NLP (analysis/nlp_processor.py)

| Function/Method | Purpose | Returns |
|-----------------|---------|---------|
| `NLPProcessor.__init__(model_name)` | Load spaCy model | None |
| `process(text)` | Full NLP pipeline | ProcessedText |
| `extract_entities(text, entity_types)` | Entity extraction | List[Entity] |
| `extract_key_phrases(text, top_n)` | Key phrases | List[str] |
| `get_noun_chunks(text)` | Noun phrases | List[str] |
| `batch_process(texts, batch_size)` | Batch processing | List[ProcessedText] |

#### Bias (analysis/bias_detector.py)

| Function/Method | Purpose | Returns |
|-----------------|---------|---------|
| `BiasDetector.__init__(method)` | Initialize | None |
| `analyze(text, text_id, text_type)` | Analyze bias | BiasScore |
| `batch_analyze(texts, batch_size)` | Batch analysis | List[BiasScore] |
| `detect_political_bias(text)` | Helper | BiasScore |

#### Consistency (analysis/consistency_analyzer.py)

| Function/Method | Purpose | Returns |
|-----------------|---------|---------|
| `ConsistencyAnalyzer.__init__()` | Initialize | None |
| `analyze_person(person_id, votes, party)` | Analyze individual | ConsistencyScore |
| `calculate_party_line(votes, party)` | Party-line % | float |
| `detect_flip_flops(votes)` | Position changes | int |
| `calculate_bipartisan_score(votes, party)` | Cross-party score | float |
| `compare_politicians(p1_votes, p2_votes)` | Similarity | float |
| `batch_analyze(vote_records, batch_size)` | Batch analysis | List[ConsistencyScore] |
| `analyze_voting_consistency(person_id, votes, party)` | Helper | ConsistencyScore |

---

## Dependencies and Relationships

### External Library Dependencies

#### Core Pipeline (Required)
- **requests** - HTTP client for synchronous requests
- **psycopg2-binary** - PostgreSQL driver

#### Core Pipeline (Optional)
- **aiohttp** - Async HTTP (required for concurrent downloads)
- **lxml** - XML parsing (required for bill/vote parsing)
- **tqdm** - Progress bars
- **prometheus_client** - Metrics

#### Analysis Modules
- **sentence-transformers** - Embeddings (required for embeddings.py)
- **torch** - Deep learning (optional, for GPU acceleration)
- **numpy** - Arrays (required for embeddings.py)
- **scipy** - Scientific computing (optional)
- **pandas** - Data manipulation (optional)
- **spacy** - NLP (required for nlp_processor.py)
- **vaderSentiment** - Sentiment (optional)
- **textblob** - Simple NLP (optional)
- **transformers** - Advanced NLP (optional)
- **pytextrank** - Key phrases (optional)

### File System Interactions

#### Environment Variables
- `CONGRESS_LOG_DIR` - Log directory (default: ./logs)
- `CONGRESS_OUTDIR` - Output directory (default: ./bulk_data)
- `CONGRESS_BULK_JSON` - Discovery output (default: bulk_urls.json)
- `CONGRESS_RETRY_JSON` - Retry tracking (default: retry_report.json)
- `DATABASE_URL` - PostgreSQL connection string

#### Input/Output Locations
- **Logs**: `./logs/cbw_congress_YYYYMMDD.log` (20MB rotating, 7 backups)
- **Downloads**: `./bulk_data/<domain>/<filename>`
- **Extracted**: `./bulk_data/<domain>/<filename>_extracted/`
- **Discovery**: `bulk_urls.json`
- **Retry tracking**: `retry_report.json`

---

## Entry Points

### Primary Entry Points

1. **cbw_main.py** - Main production entrypoint
   ```bash
   python cbw_main.py --start-congress 118 --end-congress 118 \
     --download --extract --postprocess \
     --db "postgresql://user:pass@localhost:5432/congress"
   ```

2. **app/run.py** - Application wrapper
   ```bash
   python app/run.py
   ```

3. **examples/embeddings_example.py** - Embeddings demo
   ```bash
   python examples/embeddings_example.py
   ```

4. **examples/complete_analysis_pipeline.py** - Full analysis
   ```bash
   python examples/complete_analysis_pipeline.py
   ```

### HTTP Server

```bash
python cbw_main.py --serve --serve-port 8080
```

**Endpoints:**
- `GET /status` - Pipeline status
- `POST /start` - Start download/extraction
- `POST /retry` - Retry failed downloads
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics

### CLI Arguments Reference (cbw_main.py)

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--start-congress` | int | 93 | Starting congress number |
| `--end-congress` | int | current+1 | Ending congress number |
| `--outdir` | str | ./bulk_data | Output directory |
| `--bulk-json` | str | bulk_urls.json | Discovery output |
| `--retry-json` | str | retry_report.json | Retry tracking |
| `--concurrency` | int | 6 | Concurrent downloads |
| `--retries` | int | 5 | Max retry attempts |
| `--collections` | str | "" | Filter collections |
| `--no-discovery` | flag | False | Disable discovery |
| `--validate` | flag | False | Validate URLs |
| `--download` | flag | False | Enable download |
| `--extract` | flag | False | Enable extraction |
| `--postprocess` | flag | False | Enable DB ingestion |
| `--db` | str | "" | DB connection string |
| `--serve` | flag | False | Start HTTP server |
| `--serve-port` | int | 8080 | Server port |
| `--dry-run` | flag | False | Show sample only |
| `--limit` | int | 0 | Limit URL count |

---

## Interaction Patterns

### Pattern 1: Basic Ingestion Workflow
```
User runs: python cbw_main.py --download --extract --postprocess --db "..."

Flow:
1. cbw_main.main() parses args
2. Creates Config object
3. DiscoveryManager.build() generates URLs
4. DownloadManager.download_all() downloads files
5. Extractor.extract() extracts archives
6. ParserNormalizer parses XML/JSON
7. DBManager upserts to database
```

### Pattern 2: Analysis Workflow
```
User runs: python examples/complete_analysis_pipeline.py

Flow:
1. Fetch bills/speeches/votes from database
2. EmbeddingsGenerator.encode() creates vectors
3. SentimentAnalyzer.analyze() scores sentiment
4. NLPProcessor.process() extracts entities
5. BiasDetector.analyze() detects bias
6. ConsistencyAnalyzer.analyze_person() scores consistency
7. Store all results in analysis tables
```

### Pattern 3: HTTP Control Workflow
```
User runs: python cbw_main.py --serve
External tool calls: POST /start

Flow:
1. HTTPControlServer starts on port 8080
2. Receives POST /start request
3. Spawns async task: pipeline.run_once_async()
4. Pipeline executes discovery → download → extract
5. Returns {"status": "started"}
6. External tool can poll GET /status
```

---

## Conclusion

This repository represents a comprehensive government data analysis framework with:

### Key Strengths
- **Multiple pipeline implementations** for different use cases (simple scripts, OOP, comprehensive)
- **Modular design** with clear separation of concerns
- **Production-ready features** (logging, retry logic, progress bars, HTTP API)
- **Extensive analysis capabilities** (embeddings, sentiment, NLP, bias, consistency)
- **Flexible configuration** (CLI args, environment variables, database support)
- **Complete data models** for bills, votes, people, committees
- **Working examples** demonstrating real-world usage
- **AI-powered automation** (code review, test generation, documentation)

### Architecture Highlights
- **Decorator-based logging** ensures every function is traced
- **Atomic JSON operations** prevent corruption
- **Async downloads with resume** minimize bandwidth waste
- **Conservative parsing** handles schema variations gracefully
- **UPSERT operations** enable idempotent ingestion
- **Multi-model analysis** provides comprehensive insights

### Data Sources Supported
- Congress.gov API
- GovInfo.gov bulk data
- GovTrack.us
- OpenStates.org
- ProPublica API
- TheUnitedStates.io legislators
- Data.gov CKAN (in some implementations)

### Scale and Performance
- **Concurrent downloads** (configurable, default 6)
- **Batch processing** in analysis modules
- **GPU acceleration** for embeddings (optional)
- **Rotating logs** prevent disk overflow
- **Resume capability** for interrupted downloads

The codebase is well-organized, thoroughly documented, and ready for production use in analyzing legislative data from federal and state sources. The multiple implementations provide flexibility for different deployment scenarios, from simple one-off scripts to production pipelines with monitoring and control APIs.

---

**Document Version:** 1.0  
**Last Updated:** October 22, 2025  
**Total Scripts Analyzed:** 46  
**Total Functions Documented:** 200+  
**Total Classes Documented:** 45+
