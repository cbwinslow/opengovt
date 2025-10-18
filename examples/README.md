# Examples

This directory contains example scripts demonstrating the analysis framework.

## Scripts

### embeddings_example.py
**Purpose**: Demonstrate embeddings generation and similarity search

**Features**:
- Load bills from database
- Generate embeddings using sentence transformers
- Find similar bills using cosine similarity
- Store embeddings and similarities in database

**Usage**:
```bash
export DATABASE_URL="postgresql://user:pass@localhost:5432/congress"
python embeddings_example.py
```

### complete_analysis_pipeline.py
**Purpose**: Complete end-to-end analysis pipeline

**Features**:
- Sentiment analysis
- Entity extraction
- Bias detection
- Embeddings generation
- Store all results in database

**Usage**:
```bash
export DATABASE_URL="postgresql://user:pass@localhost:5432/congress"
python complete_analysis_pipeline.py
```

## Prerequisites

1. Database with bills data (run from project root):
```bash
psql $DATABASE_URL -f app/db/migrations/001_init.sql
psql $DATABASE_URL -f app/db/migrations/002_analysis_tables.sql
```

2. Install dependencies (run from project root):
```bash
pip install -r requirements-analysis.txt
python -m spacy download en_core_web_sm
```

3. Ingest some data first (using main ingestion pipeline)

## Customization

These scripts serve as templates. You can:
- Modify analysis parameters
- Add additional analyses
- Change database queries
- Adjust batch sizes for performance

## Documentation

- **Analysis Modules**: `../docs/ANALYSIS_MODULES.md`
- **Quick Start**: `../docs/QUICK_START.md`
- **SQL Queries**: `../docs/SQL_QUERIES.md`
