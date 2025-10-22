# OpenGovt Repository - Comprehensive File Guide

**Date Created:** 2025-10-22  
**Purpose:** Complete documentation of all files in the opengovt repository, their purposes, interactions, inputs, outputs, and relationships.

---

## Table of Contents

1. [Repository Overview](#repository-overview)
2. [Core Pipeline Modules (cbw_*.py)](#core-pipeline-modules)
3. [Congress Ingestion Scripts](#congress-ingestion-scripts)
4. [Analysis Modules](#analysis-modules)
5. [Data Models](#data-models)
6. [Application Framework](#application-framework)
7. [Examples and Usage](#examples-and-usage)
8. [Documentation Files](#documentation-files)
9. [Configuration Files](#configuration-files)
10. [Database Migrations](#database-migrations)
11. [Data Flow Architecture](#data-flow-architecture)
12. [File Relationships and Dependencies](#file-relationships-and-dependencies)

---

## Repository Overview

The **OpenGovt** repository is a comprehensive system for discovering, downloading, extracting, parsing, and analyzing U.S. legislative data from multiple government sources. It provides:

- **Data Ingestion Pipeline**: Automated discovery and download of federal and state legislative data
- **Analysis Framework**: NLP, sentiment analysis, bias detection, embeddings, and consistency analysis
- **Database Integration**: PostgreSQL schema with migrations for storing and querying legislative data
- **API and Control**: HTTP control server for pipeline management
- **Monitoring**: Prometheus metrics and logging infrastructure

**Primary Data Sources:**
- Congress.gov API (Federal)
- GovInfo.gov Bulk Data (Federal)
- ProPublica Congress API (Federal)
- GovTrack (Federal)
- OpenStates (State legislatures - 50+ states)
- TheUnitedStates.io (Legislators data)

---

## Core Pipeline Modules

These are the main orchestration modules prefixed with `cbw_` that work together to form the complete ingestion pipeline.

### cbw_main.py

**Name:** cbw_main.py  
**Date:** 2025-10-02  
**Version:** 1.0  
**Summary:** Main CLI entrypoint that orchestrates the entire pipeline

**Description:**  
The main entry point for running the end-to-end congressional data pipeline. Wires together all cbw_* modules and provides a command-line interface for discovery, validation, downloading, extraction, parsing, and database ingestion.

**Inputs:**
- Command-line arguments:
  - `--start-congress`: Starting congress number (default: 93)
  - `--end-congress`: Ending congress number (default: current + 1)
  - `--outdir`: Output directory for downloads (default: ./bulk_data)
  - `--bulk-json`: Path to discovery output JSON (default: bulk_urls.json)
  - `--retry-json`: Path to retry report JSON (default: retry_report.json)
  - `--concurrency`: Number of concurrent downloads (default: 6)
  - `--retries`: Number of retry attempts (default: 5)
  - `--collections`: Comma-separated list of collections to discover
  - `--no-discovery`: Skip discovery phase
  - `--validate`: Run HEAD validation on URLs
  - `--download`: Execute download phase
  - `--extract`: Extract downloaded archives
  - `--postprocess`: Parse and ingest into database
  - `--db`: PostgreSQL connection string
  - `--serve`: Start HTTP control server
  - `--serve-port`: Port for HTTP server (default: 8080)
  - `--dry-run`: Show discovery results without downloading
  - `--limit`: Limit number of URLs to process

**Outputs:**
- `bulk_urls.json`: Discovered URLs organized by source
- `retry_report.json`: Failed download tracking
- Downloaded files in `outdir/`
- Extracted files in `outdir/*_extracted/`
- Database tables populated (bills, votes, legislators)
- Log files in `./logs/`

**Parameters:**
- Orchestrates: DiscoveryManager, Validator, DownloadManager, Extractor, ParserNormalizer, DBManager, RetryManager, HTTPControlServer

**Changelog:**
- 1.0: Initial release with full orchestration capabilities

**Related Files:**
- Uses: All cbw_*.py modules
- Outputs: bulk_urls.json, retry_report.json
- Creates: Database tables via embedded migrations

---

### cbw_config.py

**Name:** cbw_config.py  
**Date:** 2025-10-02  
**Version:** 1.0  
**Summary:** Central configuration object with defaults

**Description:**  
Encapsulates all configuration parameters used across the pipeline. Provides default values and environment variable support for directories, connection strings, and operational parameters.

**Inputs:**
- Constructor parameters or CLI args
- Environment variables:
  - `CONGRESS_LOG_DIR`: Log directory path
  - `CONGRESS_OUTDIR`: Output directory path
  - `CONGRESS_BULK_JSON`: Bulk URLs JSON path
  - `CONGRESS_RETRY_JSON`: Retry report JSON path

**Outputs:**
- Config instance with validated parameters
- Computed current congress number based on current date

**Parameters:**
- `start_congress`: Beginning congress number
- `end_congress`: Ending congress number (None = current + 1)
- `outdir`: Output directory
- `bulk_json`: Discovery output file
- `retry_json`: Retry tracking file
- `concurrency`: Concurrent download limit
- `retries`: Retry attempt limit
- `collections`: List of collection types to discover
- `do_discovery`: Enable/disable discovery phase
- `db_url`: PostgreSQL connection string
- `log_level`: Logging verbosity level

**Changelog:**
- 1.0: Initial configuration object

**Related Files:**
- Used by: All cbw_*.py modules
- Depends on: None (base configuration)

---

### cbw_utils.py

**Name:** cbw_utils.py  
**Date:** 2025-10-02  
**Version:** 1.0  
**Summary:** Logging, decorators, JSON helpers, and utility functions

**Description:**  
Centralized utilities providing logging configuration with rotating file handlers, diagnostic decorators for function entry/exit/exception tracking, atomic JSON read/write operations, and directory management helpers.

**Inputs:**
- Environment variable: `CONGRESS_LOG_DIR`
- Function decorators applied to other modules

**Outputs:**
- Configured logger instances
- Rotating log files in LOG_DIR
- Atomic JSON file operations
- Directory creation

**Parameters:**
- `configure_logger(name, level)`: Create/configure logger
- `adapter_for(logger, label)`: Create labeled logger adapter
- `save_json_atomic(path, data)`: Atomic JSON write
- `load_json_safe(path)`: Safe JSON read with corruption handling
- `ensure_dirs(*paths)`: Create directories if missing
- `@labeled(label)`: Decorator for sync functions
- `@trace_async(label)`: Decorator for async functions

**Changelog:**
- 1.0: Initial split-out from monolith with labeled logging and atomic operations

**Related Files:**
- Used by: All cbw_*.py modules
- Creates: Log files in ./logs/ directory
- Outputs: Rotating log files with dates

---

### cbw_discovery.py

**Name:** cbw_discovery.py  
**Date:** 2025-10-02  
**Version:** 1.0  
**Summary:** URL discovery manager for government data sources

**Description:**  
Generates template-based URLs for known bulk data endpoints and crawls index pages to discover exact filenames. Supports multiple data sources including GovInfo.gov, GovTrack, OpenStates, and TheUnitedStates.io.

**Inputs:**
- Config object with:
  - start_congress, end_congress
  - collections filter (optional)
  - do_discovery flag

**Outputs:**
- Dictionary containing:
  - `govinfo_templates_expanded`: Template-generated URLs
  - `govinfo_index_discovered`: Crawled index URLs
  - `govtrack`: GovTrack data URLs
  - `openstates`: OpenStates data URLs
  - `congress_legislators`: Legislators JSON URLs
  - `aggregate_urls`: Combined deduplicated list

**Parameters:**
- `GOVINFO_INDEX`: Base URL for GovInfo index
- `GOVINFO_TEMPLATES`: URL templates by collection type
- `GOVINFO_CHAMBERS`: Chamber identifiers (hr, house, senate, s)
- `OPENSTATES_DOWNLOADS`: OpenStates download page
- `OPENSTATES_MIRROR`: OpenStates mirror site
- `THEUNITEDSTATES_LEGISLATORS`: Legislators JSON URLs

**Methods:**
- `expand_govinfo_templates()`: Generate URLs from templates
- `discover_govinfo_index()`: Crawl GovInfo index
- `discover_govtrack()`: Crawl GovTrack directories
- `discover_openstates()`: Discover OpenStates files
- `build()`: Execute full discovery and return results

**Changelog:**
- 1.0: Initial discovery manager with multi-source support

**Related Files:**
- Used by: cbw_main.py
- Outputs to: bulk_urls.json
- Depends on: cbw_config.py, cbw_utils.py

---

### cbw_validator.py

**Name:** cbw_validator.py  
**Date:** 2025-10-02  
**Version:** 1.0  
**Summary:** URL validation via HEAD/GET requests

**Description:**  
Performs lightweight HEAD requests to verify URLs are reachable before initiating large downloads. Falls back to small GET requests if HEAD is blocked. Filters unreachable URLs to save bandwidth.

**Inputs:**
- List of candidate URLs to validate
- Timeout value (default: 20 seconds)

**Outputs:**
- Filtered list of reachable URLs (status < 400)
- Debug logs for failed validations

**Parameters:**
- `timeout`: Request timeout in seconds
- `head_ok(url)`: Returns True if URL is reachable
- `filter_list(urls)`: Filters list to reachable URLs only

**Changelog:**
- 1.0: Initial validation implementation

**Related Files:**
- Used by: cbw_main.py
- Depends on: cbw_utils.py, requests library

---

### cbw_downloader.py

**Name:** cbw_downloader.py  
**Date:** 2025-10-02  
**Version:** 1.0  
**Summary:** Async concurrent downloader with resume capability

**Description:**  
Uses aiohttp to download files concurrently with configurable concurrency limits. Supports HTTP range requests for resuming partial downloads. Includes progress bars via tqdm and exponential backoff retry logic.

**Inputs:**
- List of URLs to download
- Output directory path
- Concurrency limit (default: 6)
- Retry limit (default: 5)

**Outputs:**
- Downloaded files organized by domain in output directory
- List of result dictionaries:
  ```python
  {
    "url": str,
    "path": str,
    "ok": bool,
    "bytes": int,
    "error": str or None
  }
  ```

**Parameters:**
- `outdir`: Base output directory
- `concurrency`: Max simultaneous downloads
- `retries`: Max retry attempts per file
- `_head_info()`: Get Content-Length and Accept-Ranges
- `_download_single()`: Download one URL with retries
- `download_all()`: Orchestrate concurrent downloads

**Changelog:**
- 1.0: Initial async downloader with resume and retry

**Related Files:**
- Used by: cbw_main.py
- Depends on: cbw_utils.py, aiohttp, tqdm
- Outputs to: {outdir}/{domain}/{filename}

---

### cbw_extractor.py

**Name:** cbw_extractor.py  
**Date:** 2025-10-02  
**Version:** 1.0  
**Summary:** Archive extraction for zip and tar files

**Description:**  
Extracts downloaded archive files (zip, tar, tar.gz, tgz) into sibling directories with "_extracted" suffix. Optionally removes archive after extraction.

**Inputs:**
- Path to archive file
- `remove_archive` flag (default: False)

**Outputs:**
- Extracted files in {archive_path}_extracted/
- Result dictionary:
  ```python
  {
    "ok": bool,
    "dest": str,  # if successful
    "error": str  # if failed
  }
  ```

**Parameters:**
- `base_out`: Base output directory
- `extract(archive_path, remove_archive)`: Extract one archive

**Changelog:**
- 1.0: Initial extraction helper with safety logging

**Related Files:**
- Used by: cbw_main.py
- Depends on: cbw_utils.py, zipfile, tarfile
- Creates: {archive}_extracted/ directories

---

### cbw_parser.py

**Name:** cbw_parser.py  
**Date:** 2025-10-02  
**Version:** 1.0  
**Summary:** Conservative parsers for XML billstatus, rollcall, and legislators JSON

**Description:**  
Extracts common fields from government data files using lxml for XML parsing. Conservative approach returns flattened dictionaries suitable for database upserts. Designed to be extended with specific XPath expressions.

**Inputs:**
- File paths to XML or JSON files
- Typical files:
  - billstatus XML files
  - rollcall vote XML files
  - legislators JSON files

**Outputs:**
- Parsed dictionaries with normalized fields
- Bill records: `{source_file, bill_number, title, sponsor, introduced_date}`
- Vote records: `{source_file, vote_id, result, date}`
- Legislator records: `{name, bioguide, current_party, state, source_file}`

**Parameters:**
- `parse_billstatus(xml_path)`: Parse bill status XML
- `parse_rollcall(xml_path)`: Parse vote rollcall XML
- `parse_legislators(json_path)`: Parse legislators JSON

**Changelog:**
- 1.0: Initial conservative parsers; extensible with detailed XPaths

**Related Files:**
- Used by: cbw_main.py
- Depends on: cbw_utils.py, lxml, json
- Processes files from: cbw_extractor.py output

---

### cbw_db.py

**Name:** cbw_db.py  
**Date:** 2025-10-02  
**Version:** 1.0  
**Summary:** Database manager for migrations and upserts

**Description:**  
Provides DBManager class to run SQL migrations and perform upsert operations on bills, votes, and legislators. Uses psycopg2 with parameterized queries to prevent SQL injection.

**Inputs:**
- PostgreSQL connection string
- List of migrations (name, sql) tuples
- Parsed record dictionaries from cbw_parser.py

**Outputs:**
- Database schema creation
- Upserted records in tables:
  - bills (id, source_file, congress, chamber, bill_number, title, sponsor, introduced_date)
  - votes (id, source_file, congress, chamber, vote_id, vote_date, result)
  - legislators (id, name, bioguide, current_party, state)
- Returns: Record IDs after upsert

**Parameters:**
- `conn_str`: PostgreSQL connection string
- `migrations`: List of (name, sql) tuples
- `connect()`: Establish database connection
- `run_migrations()`: Execute all migrations
- `upsert_bill(rec, congress, chamber)`: Insert/update bill
- `upsert_vote(rec, congress, chamber)`: Insert/update vote
- `upsert_legislator(rec)`: Insert/update legislator
- `close()`: Close connection

**Changelog:**
- 1.0: Initial DB manager split-out

**Related Files:**
- Used by: cbw_main.py
- Depends on: cbw_utils.py, psycopg2
- Requires: PostgreSQL database
- Schema defined in: cbw_main.py (embedded migrations)

---

### cbw_retry.py

**Name:** cbw_retry.py  
**Date:** 2025-10-02  
**Version:** 1.0  
**Summary:** Retry manager for tracking failed downloads

**Description:**  
Maintains a JSON file tracking failed download attempts with timestamps, error messages, and attempt counts. Provides utilities to add failures, list retry candidates, and remove successful retries.

**Inputs:**
- Path to retry report JSON file
- Failed URL and error message

**Outputs:**
- Updated retry_report.json with structure:
  ```json
  {
    "failures": [
      {
        "url": "...",
        "attempts": 3,
        "first_failed": "2025-10-22T...",
        "last_attempted": "2025-10-22T...",
        "last_error": "..."
      }
    ]
  }
  ```

**Parameters:**
- `path`: Path to retry JSON file
- `add(url, error)`: Record failed attempt
- `list_to_retry(max_attempts)`: Get URLs with attempts < max
- `remove(url)`: Remove successful retry

**Changelog:**
- 1.0: Initial retry tracking implementation

**Related Files:**
- Used by: cbw_main.py, cbw_downloader.py
- Depends on: cbw_utils.py
- Outputs to: retry_report.json

---

### cbw_http.py

**Name:** cbw_http.py  
**Date:** 2025-10-02  
**Version:** 1.0  
**Summary:** HTTP control server for pipeline management

**Description:**  
Provides aiohttp-based HTTP server exposing REST endpoints for controlling the pipeline, checking status, and exposing Prometheus metrics. Designed for integration with TUI or automation tools.

**Inputs:**
- Pipeline instance (optional)
- Host and port configuration

**Outputs:**
- HTTP endpoints:
  - GET `/status`: Pipeline status and retry count
  - POST `/start`: Trigger pipeline run
  - POST `/retry`: Retry failed downloads
  - GET `/health`: Health check
  - GET `/metrics`: Prometheus metrics

**Parameters:**
- `pipeline`: Pipeline instance with run methods
- `host`: Bind address (default: 0.0.0.0)
- `port`: Bind port (default: 8080)
- `make_app()`: Create aiohttp application
- `start()`: Start HTTP server
- `stop()`: Stop HTTP server

**Changelog:**
- 1.0: Initial control server for TUI integration

**Related Files:**
- Used by: cbw_main.py
- Depends on: cbw_utils.py, aiohttp, prometheus_client
- Integrates with: cbw_tui.go (Go TUI)

---

## Congress Ingestion Scripts

These scripts provide alternative and specialized pipeline implementations.

### congress_bulk_pipeline.py

**Name:** congress_bulk_pipeline.py  
**Date:** 2025-10-01  
**Version:** 1.0  
**Summary:** Single-file end-to-end pipeline implementation

**Description:**  
All-in-one script combining discovery, download, extract, parse, and ingest functionality. Predecessor to the modular cbw_* architecture. Includes scheduling, retry logic, and dry-run mode.

**Inputs:**
- CLI arguments similar to cbw_main.py
- Environment variables for configuration

**Outputs:**
- bulk_urls.json
- retry_report.json
- Downloaded and extracted files
- Database ingestion

**Parameters:**
- Comprehensive CLI with all pipeline options
- Embedded discovery, validation, download, extraction, parsing

**Changelog:**
- 1.0: Initial monolithic pipeline

**Related Files:**
- Superseded by: cbw_main.py and modular cbw_*.py files
- Similar functionality but less modular

---

### congress_bulk_ingest.py

**Name:** congress_bulk_ingest.py  
**Date:** Various  
**Version:** Multiple variants  
**Summary:** Simplified ingestion script

**Description:**  
Streamlined script focusing on bulk data ingestion without full discovery. Useful for re-processing downloaded data.

**Inputs:**
- Downloaded bulk data files
- Database connection string

**Outputs:**
- Parsed data ingested into database

**Related Files:**
- Variant: congress_bulk_ingest_all.py (process all files)
- Variant: congress_bulk_ingest_full.py (full processing)

---

### congress_bulk_urls.py

**Name:** congress_bulk_urls.py  
**Summary:** URL generation and discovery utility

**Description:**  
Focused script for generating bulk data URLs without downloading. Useful for planning and validation.

**Inputs:**
- Congress range
- Collection types

**Outputs:**
- List of URLs to stdout or file

**Related Files:**
- Used independently or as reference for discovery logic

---

### congress_pipeline_oop.py

**Name:** congress_pipeline_oop.py  
**Summary:** Object-oriented pipeline implementation

**Description:**  
OOP refactoring of pipeline functionality with class-based architecture. Intermediate design between monolithic and modular approaches.

**Inputs:**
- Configuration objects
- Pipeline control parameters

**Outputs:**
- Pipeline execution results
- Structured logging

**Related Files:**
- Similar to: cbw_main.py architecture
- Alternative implementation approach

---

### congress_full_pipeline.py

**Name:** congress_full_pipeline.py  
**Summary:** Complete pipeline with all features

**Description:**  
Full-featured pipeline including advanced parsing, validation, and database operations. Comprehensive implementation with extensive error handling.

**Inputs:**
- Full configuration set
- All pipeline options

**Outputs:**
- Complete data processing pipeline
- Detailed logs and reports

**Related Files:**
- Similar scope to cbw_main.py but different organization

---

## Congress API Scripts

Located in `congress_api/` directory.

### congress_api/cbw_universal_pipeline.py

**Name:** cbw_universal_pipeline.py  
**Summary:** Universal data source pipeline

**Description:**  
Adapter pipeline supporting multiple data source APIs with normalized output. Handles API differences transparently.

**Inputs:**
- API configuration
- Data source selection

**Outputs:**
- Normalized data records
- Unified schema

**Related Files:**
- Works with: cbw_universal_single_refine.py
- Uses: universal_ingest.py

---

### congress_api/universal_ingest.py

**Name:** universal_ingest.py  
**Summary:** Universal data ingestion module

**Description:**  
Provides unified ingestion interface for multiple data sources including Congress.gov API, OpenStates API, and bulk downloads.

**Inputs:**
- API credentials
- Data source specifications

**Outputs:**
- Ingested records
- Processing logs

**Related Files:**
- Used by: cbw_universal_pipeline.py
- Depends on: Data source-specific adapters

---

## Analysis Modules

Located in `analysis/` directory. These modules provide advanced NLP and machine learning capabilities.

### analysis/embeddings.py

**Name:** embeddings.py  
**Date:** 2025-10-14  
**Version:** 1.0  
**Summary:** Vector embeddings generation using transformer models

**Description:**  
Creates dense vector representations (embeddings) of bill text and speeches using sentence transformer models. Enables semantic similarity search, clustering, and topic analysis. Supports multiple models including general-purpose and legal-domain-specific transformers.

**Inputs:**
- Text strings (bill summaries, full text, speeches)
- Model selection (default: all-MiniLM-L6-v2)
- Batch processing options

**Outputs:**
- `BillEmbeddings` objects:
  - bill_id: int
  - model_name: str
  - embedding_vector: numpy array (384-768 dimensions)
  - text_hash: str (for caching)
  - created_at: datetime
  - metadata: dict
- `SpeechEmbeddings` objects (similar structure for speeches)

**Parameters:**
- `EmbeddingsGenerator` class:
  - `__init__(model_name, use_gpu)`: Initialize with model
  - `generate_bill_embedding(text, bill_id)`: Create bill embedding
  - `generate_speech_embedding(text, person_id)`: Create speech embedding
  - `batch_generate(texts, batch_size)`: Process multiple texts
  - `compute_similarity(emb1, emb2)`: Calculate cosine similarity
- Models available:
  - `all-MiniLM-L6-v2`: Fast, 384 dimensions
  - `all-mpnet-base-v2`: High quality, 768 dimensions
  - `nlpaueb/legal-bert-base-uncased`: Legal text specialized

**Changelog:**
- 1.0: Initial implementation with sentence transformers
- Supports GPU acceleration when available
- Graceful fallback if dependencies missing

**Related Files:**
- Database table: `bill_embeddings`, `speech_embeddings`
- Used by: examples/embeddings_example.py
- Depends on: sentence-transformers, torch, numpy
- Related: analysis/nlp_processor.py for text preprocessing

**Use Cases:**
- Find similar bills across congresses
- Topic clustering
- Semantic search
- Bill recommendation
- Cross-jurisdiction comparison

---

### analysis/sentiment.py

**Name:** sentiment.py  
**Date:** 2025-10-14  
**Version:** 1.0  
**Summary:** Multi-model sentiment analysis for political text

**Description:**  
Performs sentiment analysis on legislative text using multiple models: VADER (optimized for political text), TextBlob, and transformer-based models. Provides compound scores, positive/negative/neutral breakdowns, and confidence levels.

**Inputs:**
- Text strings (bills, speeches, statements)
- Model selection (vader, textblob, transformers)
- Text type indicator (bill, speech, statement)

**Outputs:**
- `SentimentScore` objects:
  - text_id: int (bill_id or speech_id)
  - text_type: str (bill, speech, statement)
  - compound_score: float (-1 to 1)
  - positive_score: float (0 to 1)
  - negative_score: float (0 to 1)
  - neutral_score: float (0 to 1)
  - model_name: str
  - sentiment_label: str (positive, negative, neutral)
  - confidence: float
  - analyzed_at: datetime
  - text_length: int

**Parameters:**
- `SentimentAnalyzer` class:
  - `__init__(models=['vader'])`: Initialize with model list
  - `analyze(text, text_id, text_type)`: Analyze sentiment
  - `analyze_batch(texts)`: Process multiple texts
  - `get_dominant_sentiment(score)`: Get label from scores
- Supported models:
  - `vader`: VADER sentiment (best for political text)
  - `textblob`: TextBlob sentiment
  - `transformers`: DistilBERT-based (slower, more accurate)

**Changelog:**
- 1.0: Initial multi-model implementation
- VADER optimized for political language
- Support for batch processing

**Related Files:**
- Database table: `sentiment_analysis`
- Database view: `latest_bill_sentiment`
- Used by: examples/complete_analysis_pipeline.py
- Depends on: vaderSentiment, textblob, transformers (optional)

**Use Cases:**
- Detect tone of legislation (positive/negative framing)
- Track sentiment over time
- Compare sentiment across parties
- Identify controversial bills

---

### analysis/nlp_processor.py

**Name:** nlp_processor.py  
**Date:** 2025-10-14  
**Version:** 1.0  
**Summary:** NLP processing with spaCy for entity extraction and text analysis

**Description:**  
Provides natural language processing capabilities using spaCy including named entity recognition (NER), part-of-speech tagging, dependency parsing, and key phrase extraction. Extracts structured information from unstructured legislative text.

**Inputs:**
- Text strings (any length)
- Language model selection (en_core_web_sm or en_core_web_lg)
- Processing options (entities, pos_tags, dependencies)

**Outputs:**
- `ProcessedText` objects:
  - entities: List[Entity] - extracted named entities
  - key_phrases: List[str] - important phrases
  - sentences: List[str] - sentence boundaries
  - tokens: List[dict] - tokenized text with POS tags
  - metadata: dict
- `Entity` objects:
  - text: str - entity text
  - label: str - entity type (PERSON, ORG, GPE, LAW, DATE, etc.)
  - start: int - character position
  - end: int - character position
  - confidence: float

**Parameters:**
- `NLPProcessor` class:
  - `__init__(model='en_core_web_sm')`: Initialize with spaCy model
  - `process(text)`: Full NLP processing
  - `extract_entities(text)`: Get named entities
  - `extract_key_phrases(text)`: Get important phrases
  - `get_pos_tags(text)`: Get part-of-speech tags
  - `process_batch(texts)`: Process multiple texts efficiently

**Changelog:**
- 1.0: Initial spaCy-based implementation
- Entity extraction for legal concepts
- Efficient batch processing

**Related Files:**
- Database table: `extracted_entities`
- Used by: analysis/bias_detector.py, analysis/consistency_analyzer.py
- Depends on: spacy, en_core_web_sm model
- Related: analysis/embeddings.py for semantic analysis

**Entity Types Recognized:**
- PERSON: Politicians, sponsors
- ORG: Organizations, agencies, committees
- GPE: Geographic/political entities (states, countries)
- LAW: Referenced laws and bills
- DATE: Dates and time expressions
- MONEY: Monetary amounts
- CARDINAL: Numbers

**Use Cases:**
- Extract bill sponsors and co-sponsors
- Identify referenced laws and bills
- Extract policy areas and topics
- Build knowledge graphs
- Track entity mentions over time

---

### analysis/bias_detector.py

**Name:** bias_detector.py  
**Date:** 2025-10-14  
**Version:** 1.0  
**Summary:** Political bias detection and objectivity scoring

**Description:**  
Analyzes text for political bias using rule-based methods and optional ML models. Detects loaded language, framing techniques, objectivity levels, and political leaning. Provides bias scores on scale from -1 (left) to +1 (right).

**Inputs:**
- Text strings (bills, speeches, statements)
- Text ID and type
- Analysis depth (basic, detailed)

**Outputs:**
- `BiasScore` objects:
  - text_id: int
  - text_type: str
  - bias_score: float (-1 to 1, left to right)
  - objectivity_score: float (0 to 1, 0=subjective, 1=objective)
  - loaded_language_count: int
  - framing_indicators: dict
  - confidence: float
  - model_name: str
  - analyzed_at: datetime
  - metadata: dict (specific bias indicators found)

**Parameters:**
- `BiasDetector` class:
  - `__init__(method='rule_based')`: Initialize detector
  - `detect_bias(text, text_id, text_type)`: Analyze bias
  - `calculate_objectivity(text)`: Measure objectivity
  - `detect_loaded_language(text)`: Find biased terms
  - `analyze_framing(text)`: Detect framing techniques
  - `batch_analyze(texts)`: Process multiple texts

**Changelog:**
- 1.0: Initial rule-based implementation
- Loaded language dictionary
- Framing analysis

**Related Files:**
- Database table: `bias_analysis`
- Database view: `latest_bill_bias`
- Used by: examples/complete_analysis_pipeline.py
- Depends on: analysis/nlp_processor.py
- Related: analysis/sentiment.py

**Bias Indicators:**
- Loaded adjectives and adverbs
- Emotional language
- Absolute statements
- Partisan framing
- Rhetorical devices

**Use Cases:**
- Assess bill objectivity
- Compare framing across parties
- Track language evolution
- Identify propaganda techniques
- Educational transparency tools

---

### analysis/consistency_analyzer.py

**Name:** consistency_analyzer.py  
**Date:** 2025-10-14  
**Version:** 1.0  
**Summary:** Voting consistency and pattern analysis

**Description:**  
Analyzes voting patterns of legislators to detect consistency, flip-flops, party-line voting, and bipartisan cooperation. Tracks position changes over time and calculates similarity between legislators.

**Inputs:**
- Vote records for legislators
- Historical voting data
- Issue/topic classifications

**Outputs:**
- `ConsistencyScore` objects:
  - person_id: int
  - overall_consistency: float (0 to 1)
  - party_line_percentage: float
  - flip_flop_count: int
  - bipartisan_cooperation_score: float
  - issue_consistency: dict (by issue area)
  - analyzed_period: tuple (start_date, end_date)
  - vote_count: int
  - metadata: dict
- `VoteRecord` objects for tracking

**Parameters:**
- `ConsistencyAnalyzer` class:
  - `__init__(db_connection)`: Initialize with database
  - `analyze_legislator(person_id, start_date, end_date)`: Analyze one legislator
  - `calculate_consistency(votes)`: Calculate consistency score
  - `detect_flip_flops(votes, issue)`: Find position changes
  - `calculate_similarity(person1_id, person2_id)`: Compare legislators
  - `find_bipartisan_votes(person_id)`: Find cross-party cooperation
  - `batch_analyze_legislature(congress_number)`: Analyze entire congress

**Changelog:**
- 1.0: Initial consistency analysis
- Issue-based tracking
- Flip-flop detection algorithm

**Related Files:**
- Database tables: `consistency_analysis`, `issue_consistency`, `position_changes`, `politician_comparisons`
- Database view: `politician_consistency_summary`
- Used by: examples/complete_analysis_pipeline.py
- Depends on: models/vote.py, models/person.py

**Metrics Calculated:**
- Overall consistency (0-1 scale)
- Party-line voting percentage
- Issue-specific consistency
- Flip-flop frequency
- Bipartisan cooperation score
- Voting similarity with other legislators

**Use Cases:**
- Voter education (track representative consistency)
- Political research
- Predict future votes
- Identify swing voters
- Find bipartisan opportunities
- Campaign analytics

---

## Data Models

Located in `models/` directory. These define the data structures used throughout the application.

### models/bill.py

**Name:** bill.py  
**Date:** 2025-10-14  
**Version:** 1.0  
**Summary:** Bill data models for federal and state legislation

**Description:**  
Defines dataclass models for representing legislative bills from any jurisdiction. Provides unified representation across different data sources (OpenStates, Congress.gov, GovInfo). Includes related classes for bill actions, text versions, and sponsorships.

**Data Classes:**
- `Bill`: Main bill representation
  - Core fields: id, source, source_id, bill_number, chamber
  - Content: title, summary, official_title, short_title
  - Status: status, introduced_date, updated_at
  - Classification: subjects, policy_areas
  - Relationships: companion_bill_ids, jurisdiction_id, session_id
  - Federal-specific: congress_number
  - Metadata: raw_data dict

- `BillAction`: Legislative actions on bills
  - Fields: action_date, description, chamber, action_type
  - Tracks: committee referrals, votes, amendments, passage

- `BillText`: Full text versions
  - Fields: version_code, version_name, text_content, url, published_date
  - Versions: Introduced, Engrossed, Enrolled, etc.

- `BillSponsorship`: Sponsor and cosponsor information
  - Fields: person_id, sponsorship_type, is_primary
  - Types: Sponsor, Cosponsor

**Inputs:**
- Raw data from APIs or database
- Parsed XML/JSON from bulk downloads

**Outputs:**
- Structured bill objects for database storage
- JSON serialization via to_dict() methods
- Database ORM mapping

**Relationships:**
- References: models/person.py (sponsors)
- References: models/jurisdiction.py (jurisdiction, session)
- Referenced by: analysis modules for bill analysis

**Use Cases:**
- Unified bill representation across sources
- Database persistence
- API responses
- Analysis pipeline input

---

### models/person.py

**Name:** person.py  
**Date:** 2025-10-14  
**Version:** 1.0  
**Summary:** Person and legislator data models

**Description:**  
Represents individuals including legislators, politicians, and government officials. Supports multiple terms, party affiliations, and role changes over time.

**Data Classes:**
- `Person`: General person representation
  - Identification: id, name, bioguide_id, additional_ids
  - Demographics: birth_date, gender
  - Contact: email, phone, website, social_media
  - Metadata: source, source_id, raw_data

- `Member`: Legislative member (extends Person concept)
  - Current role: chamber, state, district, party
  - Terms: list of Term objects with date ranges
  - Positions: committee memberships, leadership roles
  - Contact: official addresses and social media

**Inputs:**
- TheUnitedStates.io legislators JSON
- Congress.gov API member data
- OpenStates legislator data

**Outputs:**
- Normalized person/member records
- Database persistence
- API responses with full member details

**Relationships:**
- Referenced by: models/bill.py (sponsorships)
- Referenced by: models/vote.py (vote records)
- Referenced by: models/committee.py (memberships)
- Used in: analysis/consistency_analyzer.py

**Key Features:**
- Multi-term tracking
- Party affiliation history
- Unified ID mapping (bioguide, OpenStates ID, etc.)
- Social media integration

---

### models/vote.py

**Name:** vote.py  
**Date:** 2025-10-14  
**Version:** 1.0  
**Summary:** Vote and voting record models

**Description:**  
Represents legislative votes (rollcalls) and individual legislator voting records. Tracks vote outcomes, individual positions, and vote metadata.

**Data Classes:**
- `Vote`: Legislative vote/rollcall
  - Identification: id, source, source_id, vote_id
  - Context: bill_id, session_id, jurisdiction_id
  - Details: motion, description, vote_date, chamber
  - Results: result (passed/failed), vote_counts
  - Breakdown: yea_count, nay_count, not_voting_count, present_count

- `VoteRecord`: Individual legislator's vote
  - Fields: person_id, vote_id, position
  - Positions: Yea, Nay, Not Voting, Present, Absent
  - Metadata: recorded_at

**Inputs:**
- Rollcall XML from GovInfo
- Congress.gov API vote data
- OpenStates vote data

**Outputs:**
- Vote records for analysis
- Database storage
- Voting history queries

**Relationships:**
- References: models/bill.py (vote on bill)
- References: models/person.py (who voted)
- Used by: analysis/consistency_analyzer.py

**Use Cases:**
- Voting record tracking
- Consistency analysis
- Party-line voting detection
- Bipartisan cooperation metrics

---

### models/committee.py

**Name:** committee.py  
**Date:** 2025-10-14  
**Version:** 1.0  
**Summary:** Committee and membership models

**Description:**  
Represents legislative committees, subcommittees, and their memberships. Tracks committee jurisdictions and member roles.

**Data Classes:**
- `Committee`: Legislative committee
  - Identification: id, source, source_id, code
  - Details: name, chamber, committee_type
  - Hierarchy: parent_committee_id (for subcommittees)
  - Jurisdiction: jurisdiction_id, session_id

- `CommitteeMembership`: Member assignment to committee
  - Fields: person_id, committee_id, role
  - Roles: Chair, Ranking Member, Member
  - Period: start_date, end_date

**Inputs:**
- Committee data from various sources
- Membership rosters

**Outputs:**
- Committee structures
- Membership tracking
- Historical committee records

**Relationships:**
- References: models/person.py (members)
- References: models/jurisdiction.py (jurisdiction)

---

### models/jurisdiction.py

**Name:** jurisdiction.py  
**Date:** 2025-10-14  
**Version:** 1.0  
**Summary:** Jurisdiction and session models

**Description:**  
Represents governmental jurisdictions (federal, states, territories) and their legislative sessions.

**Data Classes:**
- `Jurisdiction`: Governmental entity
  - Identification: id, jurisdiction_type, code
  - Details: name, official_name
  - Types: federal, state, territory, local
  - Geography: state_code, region

- `Session`: Legislative session
  - Identification: id, jurisdiction_id, name
  - Period: start_date, end_date
  - Details: session_type (regular, special)
  - Federal: congress_number

**Inputs:**
- OpenStates jurisdiction data
- Congress session information

**Outputs:**
- Jurisdiction and session lookups
- Context for bills and votes

**Relationships:**
- Referenced by: models/bill.py, models/vote.py, models/committee.py

---

## Application Framework

Located in `app/` directory. Core application infrastructure.

### app/pipeline.py

**Name:** pipeline.py  
**Date:** 2025-10-02  
**Version:** 1.0  
**Summary:** Pipeline orchestration classes

**Description:**  
Contains DiscoveryManager, Validator, DownloadManager, Extractor, ParserNormalizer, RetryManager, HTTPControlServer, and Pipeline orchestration classes. Alternative organization to cbw_* modules with more OOP structure.

**Classes:**
- All major pipeline components
- Pipeline orchestrator class
- Integration with app/db.py and app/utils.py

**Inputs:**
- Configuration objects
- CLI parameters

**Outputs:**
- Orchestrated pipeline execution
- Database ingestion
- HTTP control endpoints

**Related Files:**
- Uses: app/db.py, app/utils.py
- Alternative to: cbw_*.py modules
- Used by: app/run.py

---

### app/db.py

**Name:** db.py  
**Date:** 2025-10-02  
**Version:** 1.0  
**Summary:** Database utilities and ingestion

**Description:**  
Database connection management, migration runner, and ingestion utilities. Provides DBIngestor class for upserting parsed data.

**Functions:**
- `run_migrations(conn_str, migrations)`: Execute SQL migrations
- `DBIngestor`: Class for database operations
  - Connection pooling
  - Batch upserts
  - Transaction management

**Inputs:**
- PostgreSQL connection string
- Parsed data records
- SQL migration files

**Outputs:**
- Database schema creation
- Ingested records
- Transaction logs

**Related Files:**
- Used by: app/pipeline.py, cbw_main.py
- Uses: app/db/migrations/*.sql
- Depends on: psycopg2

---

### app/utils.py

**Name:** utils.py  
**Date:** 2025-10-02  
**Version:** 1.0  
**Summary:** Application utilities and helpers

**Description:**  
Shared utility functions for logging, file operations, decorators, and common tasks. Similar to cbw_utils.py but for app/ framework.

**Functions:**
- Logging configuration
- File I/O helpers
- Decorators for tracing
- JSON operations
- Directory management

**Related Files:**
- Used by: app/pipeline.py, app/db.py, app/run.py
- Similar to: cbw_utils.py

---

### app/run.py

**Name:** run.py  
**Date:** 2025-10-02  
**Version:** 1.0  
**Summary:** Application entry point

**Description:**  
Main entry point for running the application framework version of the pipeline. Alternative to cbw_main.py.

**Inputs:**
- CLI arguments
- Environment variables

**Outputs:**
- Pipeline execution
- Logs and reports

**Related Files:**
- Uses: app/pipeline.py, app/db.py, app/utils.py
- Alternative to: cbw_main.py

---

## Database Migrations

Located in `app/db/migrations/` directory.

### app/db/migrations/001_init.sql

**Name:** 001_init.sql  
**Date:** 2025-10-14  
**Version:** 1.0  
**Summary:** Initial database schema

**Description:**  
Creates base tables for legislative data including bills, votes, legislators, committees, and jurisdictions.

**Tables Created:**
- `bills`: Legislative bills with metadata
- `votes`: Rollcall votes
- `legislators`: Politician information
- `committees`: Committee structures
- `jurisdictions`: Governmental entities
- `sessions`: Legislative sessions
- `bill_actions`: Actions on bills
- `vote_records`: Individual voting records
- `committee_memberships`: Committee member assignments

**Schema Features:**
- Primary keys and indexes
- Foreign key constraints
- Unique constraints for deduplication
- Timestamps for audit trail

**Related Files:**
- Used by: app/db.py, cbw_db.py
- Extended by: 002_analysis_tables.sql

---

### app/db/migrations/002_analysis_tables.sql

**Name:** 002_analysis_tables.sql  
**Date:** 2025-10-14  
**Version:** 1.0  
**Summary:** Analysis and machine learning tables

**Description:**  
Creates tables for storing analysis results including embeddings, sentiment analysis, bias detection, consistency metrics, and derived analytics.

**Tables Created (12 tables):**
1. `bill_embeddings`: Vector embeddings for bills
   - Fields: bill_id, model_name, embedding_vector, vector_dimension
   - Uses: pgvector extension for similarity search

2. `speech_embeddings`: Vector embeddings for speeches
   - Fields: person_id, speech_id, model_name, embedding_vector

3. `sentiment_analysis`: Sentiment analysis results
   - Fields: text_id, text_type, compound_score, positive_score, negative_score, neutral_score

4. `extracted_entities`: Named entities from NLP
   - Fields: text_id, text_type, entity_text, entity_label, entity_position

5. `bias_analysis`: Bias detection results
   - Fields: text_id, text_type, bias_score, objectivity_score, loaded_language_count

6. `consistency_analysis`: Voting consistency metrics
   - Fields: person_id, overall_consistency, party_line_percentage, flip_flop_count

7. `issue_consistency`: Per-issue consistency
   - Fields: person_id, issue_area, consistency_score, vote_count

8. `position_changes`: Tracked position flip-flops
   - Fields: person_id, issue_area, old_position, new_position, change_date

9. `bill_similarities`: Computed bill similarities
   - Fields: bill_id_1, bill_id_2, similarity_score, model_name

10. `text_complexity`: Readability metrics
    - Fields: text_id, flesch_score, gunning_fog, avg_sentence_length

11. `toxicity_analysis`: Hate speech detection
    - Fields: text_id, toxicity_score, threat_score, obscenity_score

12. `politician_comparisons`: Voting similarity matrix
    - Fields: person_id_1, person_id_2, similarity_score, vote_overlap_count

**Views Created (4 views):**
1. `latest_bill_sentiment`: Most recent sentiment per bill
2. `latest_bill_bias`: Most recent bias score per bill
3. `politician_consistency_summary`: Aggregated consistency metrics
4. `top_similar_bills`: High-similarity bill pairs

**Indexes:**
- Vector similarity indexes (if pgvector available)
- Composite indexes for common queries
- Foreign key indexes

**Related Files:**
- Depends on: 001_init.sql
- Used by: analysis/*.py modules
- Creates schema for: Embeddings, sentiment, bias, consistency analysis

---

## Examples and Usage

Located in `examples/` directory. Demonstration scripts showing how to use the framework.

### examples/embeddings_example.py

**Name:** embeddings_example.py  
**Date:** 2025-10-14  
**Summary:** Example of using embeddings for bill similarity

**Description:**  
Demonstrates how to generate bill embeddings, compute similarity scores, and perform semantic search. Shows complete workflow from text to vector to similarity ranking.

**Workflow:**
1. Initialize EmbeddingsGenerator
2. Load bills from database
3. Generate embeddings for bills
4. Store embeddings in database
5. Compute pairwise similarities
6. Find most similar bills
7. Display results

**Inputs:**
- Database connection
- Bill texts from database

**Outputs:**
- Generated embeddings
- Similarity scores
- Top-N similar bills

**Related Files:**
- Uses: analysis/embeddings.py
- Queries: Database tables (bills, bill_embeddings)
- Demonstrates: Semantic search, clustering

---

### examples/complete_analysis_pipeline.py

**Name:** complete_analysis_pipeline.py  
**Date:** 2025-10-14  
**Summary:** Full analysis pipeline demonstration

**Description:**  
Comprehensive example showing all analysis modules working together. Processes bills through embeddings, sentiment analysis, NLP entity extraction, bias detection, and consistency analysis.

**Pipeline Steps:**
1. Load bills from database
2. Generate embeddings
3. Perform sentiment analysis
4. Extract named entities
5. Detect political bias
6. Analyze voting consistency
7. Store all results in database
8. Generate summary report

**Inputs:**
- Database connection with bills and votes
- Configuration for analysis modules

**Outputs:**
- All analysis tables populated
- Summary statistics
- Visualization-ready data

**Related Files:**
- Uses: All analysis/*.py modules
- Demonstrates: End-to-end analysis workflow
- Shows: Integration between modules

---

## Documentation Files

Located in `docs/` directory. Comprehensive project documentation.

### docs/GOVERNMENT_DATA_RESOURCES.md

**Name:** GOVERNMENT_DATA_RESOURCES.md  
**Summary:** Complete list of government data APIs and repositories

**Contents:**
- Federal data sources (10+)
  - Congress.gov API
  - GovInfo.gov Bulk Data
  - ProPublica Congress API
  - GovTrack
  - TheUnitedStates.io
  - OpenSecrets
  - VoteSmart
  - Data.gov
  
- State data sources (50+ states)
  - OpenStates API
  - State-specific portals
  - State legislature websites

- API documentation
  - Authentication methods
  - Rate limits
  - Endpoint descriptions
  - Response formats

**Use Cases:**
- Finding data sources
- API integration planning
- Understanding data availability

---

### docs/ANALYSIS_MODULES.md

**Name:** ANALYSIS_MODULES.md  
**Summary:** Analysis module documentation and API reference

**Contents:**
- Module overviews
- API documentation
- Usage examples
- Configuration options
- Performance considerations
- Model selection guides

**Modules Documented:**
- Embeddings generation
- Sentiment analysis
- NLP processing
- Bias detection
- Consistency analysis

**Related Files:**
- Documents: analysis/*.py modules
- Examples in: examples/

---

### docs/QUICK_START.md

**Name:** QUICK_START.md  
**Summary:** Step-by-step setup and usage guide

**Contents:**
1. Installation instructions
2. Environment setup
3. Database configuration
4. First pipeline run
5. Analysis examples
6. Troubleshooting

**Sections:**
- Prerequisites
- Installation
- Configuration
- Basic usage
- Advanced features
- Common issues

---

### docs/SQL_QUERIES.md

**Name:** SQL_QUERIES.md  
**Summary:** Query templates and optimization guide

**Contents:**
- Common query patterns
- View definitions
- Performance optimization
- Index recommendations
- Complex queries for analysis

**Query Categories:**
- Bill queries
- Vote analysis
- Legislator queries
- Similarity searches
- Time-series analysis
- Aggregate statistics

**Related Files:**
- Queries for: Database tables from migrations
- Used with: PostgreSQL database

---

### docs/API_ENDPOINTS.md

**Name:** API_ENDPOINTS.md  
**Summary:** Government API reference and usage

**Contents:**
- Detailed API documentation
- Request/response examples
- Error handling
- Best practices
- Rate limiting strategies

**APIs Documented:**
- Congress.gov API
- OpenStates API
- ProPublica API
- GovTrack API

---

### docs/IMPLEMENTATION_SUMMARY.md

**Name:** IMPLEMENTATION_SUMMARY.md  
**Summary:** Complete project overview and architecture

**Contents:**
- Project goals
- Architecture overview
- Component descriptions
- Technology stack
- Implementation decisions
- Future roadmap

---

## Configuration Files

### requirements.txt

**Name:** requirements.txt  
**Summary:** Base Python dependencies

**Dependencies:**
```
requests - HTTP client
aiohttp - Async HTTP client
tqdm - Progress bars
psycopg2-binary - PostgreSQL driver
lxml - XML parsing
prometheus-client - Metrics
```

**Purpose:** Core pipeline dependencies

---

### requirements-analysis.txt

**Name:** requirements-analysis.txt  
**Summary:** Analysis module dependencies

**Dependencies:**
```
spacy>=3.7.0 - NLP processing
sentence-transformers>=2.2.0 - Embeddings
transformers>=4.30.0 - Advanced NLP
torch>=2.0.0 - Deep learning
vaderSentiment>=3.3.2 - Sentiment analysis
textblob>=0.17.1 - Text analysis
numpy, scipy, pandas - Data processing
```

**Post-install:**
```bash
python -m spacy download en_core_web_sm
```

**Purpose:** Machine learning and NLP analysis

---

### docker-compose.yml

**Name:** docker-compose.yml  
**Summary:** Docker composition for full stack

**Services:**
1. **postgres**: PostgreSQL 15 database
   - Port: 5432
   - Volume: pgdata
   - Credentials: congress/congress

2. **pipeline**: Python pipeline container
   - Depends on: postgres
   - Ports: 8000 (metrics), 8080 (control)
   - Volumes: bulk_data, logs

**Usage:**
```bash
docker-compose up --build
```

**Related Files:**
- Uses: Dockerfile
- Configures: Full application stack

---

### Dockerfile

**Name:** Dockerfile  
**Summary:** Container image for pipeline

**Base:** Python 3.11
**Installs:** requirements.txt dependencies
**Exposes:** Ports 8000, 8080
**Entry:** cbw_main.py

---

### .gitignore

**Name:** .gitignore  
**Summary:** Git ignore rules

**Ignored:**
- Python artifacts (__pycache__, *.pyc)
- Virtual environments (.venv, venv/)
- Data files (bulk_data/, *.zip)
- Logs (logs/, *.log)
- Analysis artifacts (*.pkl, *.model)
- IDE files (.vscode/, .idea/)
- OS files (.DS_Store)

---

### package.json

**Name:** package.json  
**Summary:** Node.js dependencies for testing infrastructure

**Purpose:** Test automation and generation
**Scripts:** Test generators and automation

---

### prometheus/prometheus.yml

**Name:** prometheus.yml  
**Summary:** Prometheus metrics configuration

**Scrape Targets:**
- Pipeline metrics endpoint (:8000/metrics)

**Purpose:** Monitoring and observability

---

## Other Supporting Files

### cbw_tui.go

**Name:** cbw_tui.go  
**Date:** 2025-10-02  
**Summary:** Terminal UI in Go for pipeline control

**Description:**  
Provides interactive terminal interface for controlling the pipeline, viewing status, and monitoring progress. Written in Go using bubbletea framework.

**Features:**
- Real-time status display
- Start/stop pipeline
- Retry failed downloads
- View logs
- Metrics display

**Inputs:**
- HTTP control API endpoints (cbw_http.py)
- Keyboard commands

**Outputs:**
- Terminal UI display
- API requests to pipeline

**Related Files:**
- Calls: cbw_http.py endpoints
- Alternative: go-tui/main.go (expanded version)

---

### go-tui/main.go

**Name:** go-tui/main.go  
**Summary:** Expanded Go TUI application

**Description:**  
Full-featured terminal UI with additional features and improved interface.

**Related Files:**
- Similar to: cbw_tui.go
- Enhanced version with more features

---

### setup.sh

**Name:** setup.sh  
**Summary:** Setup script for repository

**Purpose:**
- Install dependencies
- Configure environment
- Download models
- Initialize database

**Usage:**
```bash
bash setup.sh
```

---

### test-*.js, test-*.ts

**Name:** test-generator.js, test-setup.ts, vitest.config.*.js  
**Summary:** Test infrastructure and configuration

**Purpose:**
- Test generation
- Test automation
- Backend/frontend test configuration

---

### sample_bulk_urls.json

**Name:** sample_bulk_urls.json  
**Summary:** Example discovery output

**Contents:**
- Sample URL structure
- Example of bulk_urls.json format

**Purpose:** Documentation and testing

---

### sample_retry_report.json

**Name:** sample_retry_report.json  
**Summary:** Example retry report

**Contents:**
- Sample failure tracking
- Example of retry_report.json format

**Purpose:** Documentation and testing

---

## Data Flow Architecture

### Complete Data Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                              │
├─────────────────────────────────────────────────────────────────┤
│ Federal: Congress.gov │ GovInfo.gov │ ProPublica │ GovTrack     │
│ State: OpenStates (50+) │ State portals                         │
│ Reference: TheUnitedStates.io                                   │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DISCOVERY PHASE                               │
│  Module: cbw_discovery.py                                       │
│  Output: bulk_urls.json                                         │
├─────────────────────────────────────────────────────────────────┤
│  • expand_govinfo_templates() - Generate template URLs          │
│  • discover_govinfo_index() - Crawl index pages                 │
│  • discover_govtrack() - Crawl GovTrack                         │
│  • discover_openstates() - Find state data                      │
│  Output: Aggregated URL list (1000s of URLs)                   │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    VALIDATION PHASE (Optional)                   │
│  Module: cbw_validator.py                                       │
├─────────────────────────────────────────────────────────────────┤
│  • HEAD requests to verify URLs                                 │
│  • Filter unreachable endpoints                                 │
│  Output: Validated URL list                                     │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DOWNLOAD PHASE                                │
│  Module: cbw_downloader.py                                      │
│  Output: ./bulk_data/{domain}/{files}                           │
├─────────────────────────────────────────────────────────────────┤
│  • Concurrent downloads (async with aiohttp)                    │
│  • Resume support via Range headers                             │
│  • Retry logic with exponential backoff                         │
│  • Progress bars per file                                       │
│  • Record failures in retry_report.json                         │
│  Output: Downloaded archives and files                          │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    EXTRACTION PHASE                              │
│  Module: cbw_extractor.py                                       │
│  Output: ./bulk_data/{domain}/{file}_extracted/                 │
├─────────────────────────────────────────────────────────────────┤
│  • Extract ZIP archives                                         │
│  • Extract TAR/GZ archives                                      │
│  • Organize in _extracted directories                           │
│  Output: Extracted XML, JSON, CSV files                         │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PARSING PHASE                                 │
│  Module: cbw_parser.py                                          │
├─────────────────────────────────────────────────────────────────┤
│  • parse_billstatus() - Extract bill metadata                   │
│  • parse_rollcall() - Extract vote information                  │
│  • parse_legislators() - Extract member data                    │
│  Output: Normalized Python dictionaries                         │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DATABASE INGESTION                            │
│  Module: cbw_db.py                                              │
│  Output: PostgreSQL tables                                      │
├─────────────────────────────────────────────────────────────────┤
│  • run_migrations() - Create schema                             │
│  • upsert_bill() - Insert/update bills                          │
│  • upsert_vote() - Insert/update votes                          │
│  • upsert_legislator() - Insert/update legislators              │
│  Output: Populated database tables                              │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ANALYSIS PHASE                                │
│  Modules: analysis/*.py                                         │
│  Output: Analysis tables                                        │
├─────────────────────────────────────────────────────────────────┤
│  • EmbeddingsGenerator - Generate vectors (384-768 dims)        │
│  • SentimentAnalyzer - Analyze sentiment (-1 to +1)             │
│  • NLPProcessor - Extract entities and key phrases              │
│  • BiasDetector - Detect political bias                         │
│  • ConsistencyAnalyzer - Analyze voting patterns                │
│  Output: bill_embeddings, sentiment_analysis, etc.              │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    QUERY & VISUALIZATION                         │
│  Queries: docs/SQL_QUERIES.md                                   │
│  Views: latest_bill_sentiment, politician_consistency_summary   │
├─────────────────────────────────────────────────────────────────┤
│  • Similarity searches                                          │
│  • Time-series analysis                                         │
│  • Legislator comparisons                                       │
│  • Bias trends                                                  │
│  Output: Insights, dashboards, APIs                             │
└─────────────────────────────────────────────────────────────────┘
```

### Module Interaction Diagram

```
cbw_main.py (Orchestrator)
    │
    ├─→ cbw_config.py ──→ Configuration for all modules
    │
    ├─→ cbw_utils.py ──→ Logging, decorators, JSON helpers
    │       │
    │       └─→ Used by ALL modules
    │
    ├─→ cbw_discovery.py
    │       │
    │       ├─→ Reads: cbw_config.py
    │       └─→ Writes: bulk_urls.json
    │
    ├─→ cbw_validator.py (optional)
    │       │
    │       └─→ Filters: bulk_urls.json URLs
    │
    ├─→ cbw_downloader.py
    │       │
    │       ├─→ Reads: Validated URLs
    │       ├─→ Writes: ./bulk_data/{files}
    │       └─→ Updates: cbw_retry.py on failures
    │
    ├─→ cbw_extractor.py
    │       │
    │       ├─→ Reads: Downloaded archives
    │       └─→ Writes: {archive}_extracted/
    │
    ├─→ cbw_parser.py
    │       │
    │       └─→ Reads: Extracted XML/JSON files
    │
    ├─→ cbw_db.py
    │       │
    │       ├─→ Reads: Parsed dictionaries
    │       └─→ Writes: Database tables
    │
    ├─→ cbw_retry.py
    │       │
    │       ├─→ Reads/Writes: retry_report.json
    │       └─→ Tracks: Failed downloads
    │
    └─→ cbw_http.py (optional)
            │
            └─→ Exposes: HTTP control API

Analysis Modules (independent, run after ingestion):
    │
    ├─→ analysis/embeddings.py
    │       └─→ Reads: bills table → Writes: bill_embeddings
    │
    ├─→ analysis/sentiment.py
    │       └─→ Reads: bills table → Writes: sentiment_analysis
    │
    ├─→ analysis/nlp_processor.py
    │       └─→ Reads: bills table → Writes: extracted_entities
    │
    ├─→ analysis/bias_detector.py
    │       └─→ Reads: bills table → Writes: bias_analysis
    │
    └─→ analysis/consistency_analyzer.py
            └─→ Reads: votes table → Writes: consistency_analysis
```

---

## File Relationships and Dependencies

### Dependency Hierarchy

```
Level 0 (No dependencies):
  - cbw_config.py
  - cbw_utils.py
  - models/*.py (data classes)

Level 1 (Depends on Level 0):
  - cbw_discovery.py
  - cbw_validator.py
  - cbw_downloader.py
  - cbw_extractor.py
  - cbw_parser.py
  - cbw_db.py
  - cbw_retry.py
  - cbw_http.py

Level 2 (Orchestration):
  - cbw_main.py (uses all Level 1 modules)
  - app/pipeline.py (alternative orchestration)

Level 3 (Analysis - runs after ingestion):
  - analysis/embeddings.py
  - analysis/sentiment.py
  - analysis/nlp_processor.py
  - analysis/bias_detector.py
  - analysis/consistency_analyzer.py

Level 4 (Examples and demos):
  - examples/embeddings_example.py
  - examples/complete_analysis_pipeline.py
```

### Input/Output File Relationships

```
Discovery Output → Download Input:
  bulk_urls.json → cbw_downloader.py

Download Output → Extraction Input:
  ./bulk_data/{domain}/{archive} → cbw_extractor.py

Extraction Output → Parsing Input:
  ./bulk_data/{domain}/{archive}_extracted/*.xml → cbw_parser.py
  ./bulk_data/{domain}/{archive}_extracted/*.json → cbw_parser.py

Parsing Output → Database Input:
  Dictionaries → cbw_db.py → PostgreSQL tables

Download Failures → Retry Input:
  retry_report.json → cbw_retry.py → Retry candidates

Database Tables → Analysis Input:
  bills table → analysis modules → analysis tables
  votes table → consistency_analyzer → consistency_analysis
```

### Cross-Module Function Calls

```
cbw_main.py calls:
  ├─→ Config()
  ├─→ DiscoveryManager.build()
  ├─→ Validator.filter_list()
  ├─→ DownloadManager.download_all()
  ├─→ Extractor.extract()
  ├─→ ParserNormalizer.parse_*()
  ├─→ DBManager.upsert_*()
  ├─→ RetryManager.add()
  └─→ HTTPControlServer.start()

Analysis pipeline calls:
  ├─→ EmbeddingsGenerator.generate_*()
  ├─→ SentimentAnalyzer.analyze()
  ├─→ NLPProcessor.process()
  ├─→ BiasDetector.detect_bias()
  └─→ ConsistencyAnalyzer.analyze_legislator()
```

---

## Quick Reference: Common Tasks

### 1. Run Full Pipeline

```bash
# Discovery only (dry run)
python cbw_main.py --start-congress 118 --end-congress 118 --dry-run

# Full pipeline with download, extract, and database
export DATABASE_URL="postgresql://user:pass@localhost:5432/congress"
python cbw_main.py \
  --start-congress 118 \
  --end-congress 118 \
  --download \
  --extract \
  --postprocess \
  --db "$DATABASE_URL"
```

### 2. Run Analysis

```bash
# Install analysis dependencies
pip install -r requirements-analysis.txt
python -m spacy download en_core_web_sm

# Run embeddings
python examples/embeddings_example.py

# Run complete analysis
python examples/complete_analysis_pipeline.py
```

### 3. Start HTTP Control Server

```bash
python cbw_main.py --serve --serve-port 8080
```

### 4. Use Docker

```bash
docker-compose up --build
```

### 5. Query Database

```bash
# View similar bills
psql $DATABASE_URL -c "SELECT * FROM top_similar_bills LIMIT 10;"

# View legislator consistency
psql $DATABASE_URL -c "SELECT * FROM politician_consistency_summary;"
```

---

## Technology Stack Summary

**Languages:**
- Python 3.11+ (primary)
- Go (TUI)
- SQL (PostgreSQL)
- JavaScript/TypeScript (testing)

**Python Libraries:**
- **Network**: requests, aiohttp
- **Database**: psycopg2-binary
- **Parsing**: lxml, json
- **NLP**: spacy, sentence-transformers, transformers
- **ML**: torch, numpy, scipy, pandas
- **Sentiment**: vaderSentiment, textblob
- **Utilities**: tqdm, prometheus-client

**Infrastructure:**
- **Database**: PostgreSQL 15
- **Container**: Docker, docker-compose
- **Monitoring**: Prometheus
- **Logging**: Python logging with rotation

**Data Sources:**
- Congress.gov, GovInfo.gov, ProPublica, GovTrack
- OpenStates, TheUnitedStates.io
- 50+ state legislature portals

---

## Project Statistics

- **Total Files**: 60+ source files
- **Python Modules**: 40+
- **Database Tables**: 21 (9 base + 12 analysis)
- **Database Views**: 4
- **Documentation Files**: 10+
- **Lines of Code**: ~25,000+
  - Python: ~20,000
  - SQL: ~1,000
  - Documentation: ~5,000+
- **Data Sources**: 10+ documented APIs
- **ML Models**: 10+ NLP/sentiment/embedding models supported

---

## Glossary

**Terms:**
- **Bill**: Legislative proposal (federal or state)
- **Congress**: Two-year legislative period (e.g., 118th Congress)
- **Chamber**: House or Senate (federal), Upper/Lower (state)
- **Rollcall**: Recorded vote with individual positions
- **Bioguide**: Biographical Directory ID for legislators
- **GovInfo**: Official government document repository
- **Embedding**: Vector representation of text (384-768 dimensions)
- **Sentiment Score**: Measure of positive/negative tone (-1 to 1)
- **Bias Score**: Measure of political lean (-1=left, +1=right)
- **Consistency Score**: Measure of voting pattern stability (0-1)

---

**Document Version:** 1.0  
**Last Updated:** 2025-10-22  
**Maintained For:** OpenGovt Project  
**Repository:** github.com/cbwinslow/opengovt

