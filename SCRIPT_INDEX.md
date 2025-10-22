# OpenGovt - Quick Script Reference Index

This is a quick reference guide to all scripts in the repository. For comprehensive analysis, see [SCRIPT_EVALUATION.md](SCRIPT_EVALUATION.md).

## Core Pipeline Modules (cbw_*.py)

| Script | Lines | Purpose | Key Classes/Functions |
|--------|-------|---------|----------------------|
| cbw_main.py | 186 | Main entrypoint and orchestrator | `main()`, `parse_args()` |
| cbw_config.py | 54 | Configuration management | `Config`, `now_congress()` |
| cbw_utils.py | 141 | Logging, decorators, utilities | `configure_logger()`, `@labeled`, `@trace_async` |
| cbw_discovery.py | 169 | URL discovery from multiple sources | `DiscoveryManager` |
| cbw_validator.py | 48 | URL validation (HEAD/GET checks) | `Validator` |
| cbw_downloader.py | 130 | Async concurrent downloader | `DownloadManager` |
| cbw_extractor.py | 48 | Archive extraction (ZIP/TAR) | `Extractor` |
| cbw_parser.py | 103 | XML/JSON parsers | `ParserNormalizer` |
| cbw_db.py | 104 | Database operations | `DBManager` |
| cbw_retry.py | 52 | Retry logic management | `RetryManager` |
| cbw_http.py | 85 | HTTP control server | `HTTPControlServer` |

**Total:** 11 modules, ~1,120 lines

## Alternative Pipeline Implementations

| Script | Lines | Type | Description |
|--------|-------|------|-------------|
| congress_bulk_ingest.py | 179 | Functional | Simple standalone script |
| congress_bulk_ingest_all.py | 484 | Functional | Extended with more sources |
| congress_bulk_ingest_full.py | 594 | Functional | Full-featured version |
| congress_pipeline_oop.py | 768 | OOP | Object-oriented single file |
| congress_full_pipeline.py | 1,219 | OOP | Most comprehensive standalone |
| congress_bulk_pipeline.py | 772 | OOP | With DB schema management |
| congress_bulk_urls.py | 368 | Utility | URL generation only |

**Total:** 7 implementations, ~4,384 lines

## Congress API Implementations (congress_api/)

| Script | Lines | Description |
|--------|-------|-------------|
| universal_ingest.py | 765 | Multi-source universal ingest |
| cbw_universal_pipeline.py | 1,415 | Most comprehensive pipeline |
| cbw_universal_single_refine.py | 552 | Refined single-source |
| congress_pipeline_oop.py | 768 | OOP pipeline (duplicate) |
| congress_full_pipeline.py | 1,219 | Full pipeline (duplicate) |

**Total:** 5 implementations, ~4,719 lines

## Application Layer (app/)

| Script | Lines | Purpose |
|--------|-------|---------|
| app/run.py | 61 | Application entrypoint |
| app/pipeline.py | 368 | Pipeline implementation |
| app/utils.py | 129 | Application utilities |
| app/db.py | 102 | Database operations |

**Total:** 4 modules, ~660 lines

## Data Models (models/)

| Script | Lines | Classes | Description |
|--------|-------|---------|-------------|
| models/person.py | 225 | Person, Member | People and membership |
| models/bill.py | 297 | Bill, BillAction, BillText, BillSponsorship | Bills and related |
| models/vote.py | 170 | Vote, VoteRecord | Votes and records |
| models/committee.py | 130 | Committee, CommitteeMembership | Committees |
| models/jurisdiction.py | 139 | Jurisdiction, Session | Jurisdictions and sessions |
| models/__init__.py | 27 | - | Package exports |

**Total:** 6 modules, 11 classes, ~988 lines

## Analysis Modules (analysis/)

| Script | Lines | Purpose | Key Classes |
|--------|-------|---------|-------------|
| analysis/embeddings.py | 339 | Vector embeddings | EmbeddingsGenerator, BillEmbeddings, SpeechEmbeddings |
| analysis/sentiment.py | 358 | Sentiment analysis | SentimentAnalyzer, SentimentScore |
| analysis/nlp_processor.py | 373 | NLP processing | NLPProcessor, ProcessedText, Entity |
| analysis/bias_detector.py | 349 | Bias detection | BiasDetector, BiasScore |
| analysis/consistency_analyzer.py | 406 | Voting consistency | ConsistencyAnalyzer, ConsistencyScore |
| analysis/__init__.py | 32 | - | Package exports |

**Total:** 6 modules, 12+ classes, ~1,857 lines

## Examples (examples/)

| Script | Lines | Purpose |
|--------|-------|---------|
| examples/embeddings_example.py | 304 | Embeddings demo |
| examples/complete_analysis_pipeline.py | 420 | Full analysis workflow |

**Total:** 2 examples, ~724 lines

## GitHub Automation Scripts (.github/scripts/)

| Script | Lines | Purpose |
|--------|-------|---------|
| ai-code-review.py | 262 | AI code review |
| ai-test-generator.py | 280 | Test generation |
| ai-documentation-review.py | 297 | Documentation review |
| ai-refactor.py | 336 | Refactoring suggestions |
| crewai-integration.py | 380 | Multi-agent orchestration |

**Total:** 5 scripts, ~1,555 lines

## Quick Stats

- **Total Python Files:** 46
- **Total Lines of Code:** ~16,000
- **Core Pipeline:** 11 modules
- **Alternative Implementations:** 7 versions
- **Data Models:** 11 classes
- **Analysis Modules:** 6 modules with 12+ classes
- **Automation Scripts:** 5 AI-powered tools

## Common Workflows

### 1. Basic Data Ingestion
```bash
python cbw_main.py --start-congress 118 --end-congress 118 \
  --download --extract --postprocess \
  --db "postgresql://localhost/congress"
```

### 2. Generate Embeddings
```bash
python examples/embeddings_example.py
```

### 3. Full Analysis
```bash
python examples/complete_analysis_pipeline.py
```

### 4. Start Control Server
```bash
python cbw_main.py --serve --serve-port 8080
```

## Key Entry Points

1. **Production Pipeline:** `cbw_main.py`
2. **Application Layer:** `app/run.py`
3. **Simple Ingestion:** `congress_bulk_ingest.py`
4. **Analysis Demo:** `examples/complete_analysis_pipeline.py`
5. **Embeddings Demo:** `examples/embeddings_example.py`

## Module Dependencies

- **Core:** cbw_utils.py is used by all other cbw_* modules
- **Config:** cbw_config.py provides configuration to all modules
- **Discovery:** Generates URLs consumed by downloader
- **Downloader:** Produces files consumed by extractor
- **Extractor:** Produces files consumed by parser
- **Parser:** Produces dicts consumed by database manager
- **Analysis:** Consumes data from database, produces insights

## External Dependencies

**Required:**
- requests, psycopg2-binary

**Optional but Recommended:**
- aiohttp, lxml, tqdm

**Analysis:**
- sentence-transformers, spacy, vaderSentiment, textblob, transformers

For detailed documentation, see [SCRIPT_EVALUATION.md](SCRIPT_EVALUATION.md).
