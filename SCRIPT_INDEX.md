# OpenGovt - Quick Script Reference Index

**Auto-generated:** <REGENERATE_TIMESTAMP>

This is a quick reference guide to all scripts in the repository. 
For comprehensive analysis, see [SCRIPT_EVALUATION.md](SCRIPT_EVALUATION.md).

## Quick Stats

- **Total Python Files:** 47
- **Total Lines of Code:** ~16,657
- **Total Classes:** 103
- **Total Functions:** 164

## Alternative Implementations

| Script | Lines | Classes | Functions |
|--------|-------|---------|-----------|
| congress_bulk_ingest.py | 180 | 0 | 9 |
| congress_bulk_ingest_all.py | 485 | 0 | 13 |
| congress_bulk_ingest_full.py | 595 | 0 | 16 |
| congress_bulk_pipeline.py | 773 | 0 | 25 |
| congress_bulk_urls.py | 369 | 0 | 8 |
| congress_full_pipeline.py | 1220 | 10 | 11 |
| congress_pipeline_oop.py | 769 | 9 | 2 |

**Total:** 7 files, 4391 lines, 19 classes, 84 functions

## Analysis Modules (analysis/)

| Script | Lines | Classes | Functions |
|--------|-------|---------|-----------|
| analysis/__init__.py | 33 | 0 | 0 |
| analysis/bias_detector.py | 350 | 2 | 1 |
| analysis/consistency_analyzer.py | 407 | 3 | 1 |
| analysis/embeddings.py | 340 | 3 | 2 |
| analysis/nlp_processor.py | 374 | 3 | 1 |
| analysis/sentiment.py | 359 | 2 | 1 |

**Total:** 6 files, 1863 lines, 13 classes, 6 functions

## Application Layer (app/)

| Script | Lines | Classes | Functions |
|--------|-------|---------|-----------|
| app/db.py | 103 | 1 | 1 |
| app/pipeline.py | 369 | 7 | 0 |
| app/run.py | 62 | 0 | 2 |
| app/utils.py | 130 | 0 | 7 |

**Total:** 4 files, 664 lines, 8 classes, 10 functions

## Congress API (congress_api/)

| Script | Lines | Classes | Functions |
|--------|-------|---------|-----------|
| congress_api/congress_full_pipeline.py | 1220 | 10 | 11 |
| congress_api/congress_pipeline_oop.py | 769 | 9 | 2 |
| congress_api/universal_ingest.py | 766 | 1 | 11 |

**Total:** 3 files, 2755 lines, 20 classes, 24 functions

## Core Pipeline (cbw_*.py)

| Script | Lines | Classes | Functions |
|--------|-------|---------|-----------|
| cbw_config.py | 55 | 1 | 1 |
| cbw_db.py | 105 | 1 | 0 |
| cbw_discovery.py | 170 | 1 | 0 |
| cbw_downloader.py | 131 | 1 | 0 |
| cbw_extractor.py | 49 | 1 | 0 |
| cbw_http.py | 86 | 1 | 0 |
| cbw_main.py | 187 | 0 | 2 |
| cbw_parser.py | 104 | 1 | 0 |
| cbw_retry.py | 53 | 1 | 0 |
| cbw_utils.py | 142 | 0 | 7 |
| cbw_validator.py | 49 | 1 | 0 |
| congress_api/cbw_universal_pipeline.py | 1416 | 10 | 10 |
| congress_api/cbw_universal_single_refine.py | 553 | 2 | 11 |

**Total:** 13 files, 3100 lines, 21 classes, 31 functions

## Data Models (models/)

| Script | Lines | Classes | Functions |
|--------|-------|---------|-----------|
| models/__init__.py | 28 | 0 | 0 |
| models/bill.py | 298 | 4 | 0 |
| models/committee.py | 131 | 2 | 0 |
| models/jurisdiction.py | 140 | 2 | 0 |
| models/person.py | 226 | 2 | 0 |
| models/vote.py | 171 | 2 | 0 |

**Total:** 6 files, 994 lines, 12 classes, 0 functions

## Examples (examples/)

| Script | Lines | Classes | Functions |
|--------|-------|---------|-----------|
| examples/complete_analysis_pipeline.py | 421 | 1 | 1 |
| examples/embeddings_example.py | 305 | 0 | 7 |

**Total:** 2 files, 726 lines, 1 classes, 8 functions

## GitHub Automation (.github/scripts/)

| Script | Lines | Classes | Functions |
|--------|-------|---------|-----------|
| .github/scripts/ai-code-review.py | 263 | 1 | 0 |
| .github/scripts/ai-documentation-review.py | 298 | 1 | 0 |
| .github/scripts/ai-refactor.py | 337 | 1 | 0 |
| .github/scripts/ai-test-generator.py | 281 | 1 | 0 |
| .github/scripts/crewai-integration.py | 381 | 4 | 0 |

**Total:** 5 files, 1560 lines, 8 classes, 0 functions

## Other Scripts

| Script | Lines | Classes | Functions |
|--------|-------|---------|-----------|
| generate_docs.py | 604 | 1 | 1 |

**Total:** 1 files, 604 lines, 1 classes, 1 functions

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

## Regenerating Documentation

To regenerate this documentation after adding/removing/modifying files:

```bash
python generate_docs.py
```

For detailed documentation, see [SCRIPT_EVALUATION.md](SCRIPT_EVALUATION.md).