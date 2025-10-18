# OpenGovt Analysis Framework - Project Structure

```
opengovt/
│
├── docs/                                    📚 Comprehensive Documentation
│   ├── GOVERNMENT_DATA_RESOURCES.md        # Complete list of APIs & repos
│   ├── ANALYSIS_MODULES.md                 # Module docs & API reference
│   ├── QUICK_START.md                      # Step-by-step setup guide
│   ├── SQL_QUERIES.md                      # Query templates & optimization
│   ├── API_ENDPOINTS.md                    # Government API reference
│   └── IMPLEMENTATION_SUMMARY.md           # Complete project overview
│
├── models/                                  🏗️ Data Models
│   ├── README.md                           # Models documentation
│   ├── __init__.py                         # Package exports
│   ├── person.py                           # Person, Member classes
│   ├── bill.py                             # Bill, BillAction, BillText, BillSponsorship
│   ├── vote.py                             # Vote, VoteRecord classes
│   ├── committee.py                        # Committee, CommitteeMembership
│   └── jurisdiction.py                     # Jurisdiction, Session classes
│
├── analysis/                                🧠 Analysis Modules
│   ├── README.md                           # Analysis documentation
│   ├── __init__.py                         # Package exports
│   ├── embeddings.py                       # Vector representations (384-768 dims)
│   │   ├── EmbeddingsGenerator            # Main class
│   │   ├── BillEmbeddings                 # Bill embedding container
│   │   └── SpeechEmbeddings               # Speech embedding container
│   │
│   ├── sentiment.py                        # Sentiment analysis
│   │   ├── SentimentAnalyzer              # Multi-model analyzer
│   │   └── SentimentScore                 # Results container
│   │
│   ├── nlp_processor.py                    # NLP processing
│   │   ├── NLPProcessor                   # spaCy-based processor
│   │   ├── Entity                         # Entity representation
│   │   └── ProcessedText                  # Results container
│   │
│   ├── bias_detector.py                    # Political bias detection
│   │   ├── BiasDetector                   # Bias analyzer
│   │   └── BiasScore                      # Results container
│   │
│   └── consistency_analyzer.py             # Voting consistency
│       ├── ConsistencyAnalyzer            # Pattern analyzer
│       ├── ConsistencyScore               # Results container
│       └── VoteRecord                     # Vote representation
│
├── examples/                                💻 Working Examples
│   ├── README.md                           # Examples documentation
│   ├── embeddings_example.py               # Similarity search workflow
│   └── complete_analysis_pipeline.py       # Full pipeline demo
│
├── app/db/migrations/                       🗄️ Database Migrations
│   ├── 001_init.sql                        # Base tables (bills, votes, legislators)
│   └── 002_analysis_tables.sql             # Analysis tables + views
│       ├── Tables (12):
│       │   ├── bill_embeddings            # Embedding vectors
│       │   ├── speech_embeddings          # Speech vectors
│       │   ├── sentiment_analysis         # Sentiment results
│       │   ├── extracted_entities         # NER results
│       │   ├── bias_analysis              # Bias detection results
│       │   ├── consistency_analysis       # Voting consistency
│       │   ├── issue_consistency          # Per-issue consistency
│       │   ├── position_changes           # Position tracking
│       │   ├── bill_similarities          # Similarity scores
│       │   ├── text_complexity            # Complexity metrics
│       │   ├── toxicity_analysis          # Hate speech detection
│       │   └── politician_comparisons     # Voting similarity
│       │
│       └── Views (4):
│           ├── latest_bill_sentiment      # Latest sentiment per bill
│           ├── latest_bill_bias           # Latest bias per bill
│           ├── politician_consistency_summary
│           └── top_similar_bills          # High similarity pairs
│
├── requirements.txt                         ⚙️ Base Dependencies
├── requirements-analysis.txt                📦 Analysis Dependencies
│   ├── spacy>=3.7.0                        # NLP processing
│   ├── sentence-transformers>=2.2.0        # Embeddings
│   ├── transformers>=4.30.0                # Advanced NLP
│   ├── torch>=2.0.0                        # Deep learning
│   ├── vaderSentiment>=3.3.2              # Sentiment
│   ├── textblob>=0.17.1                   # Text analysis
│   ├── numpy, scipy, pandas              # Data processing
│   └── tqdm                               # Progress bars
│
└── .gitignore                               🚫 Ignore Rules
    ├── Python artifacts                    # __pycache__, *.pyc
    ├── Analysis artifacts                  # *.pkl, *.model
    └── Data files                          # bulk_data/, *.zip
```

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                              │
├─────────────────────────────────────────────────────────────────┤
│ Federal: Congress.gov API │ GovInfo.gov │ ProPublica │ GovTrack │
│ State: OpenStates (50+) │ OpenLegislation (NY) │ State Sites   │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    INGESTION PIPELINE                            │
│  (existing: cbw_main.py, universal_ingest.py)                   │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    POSTGRESQL DATABASE                           │
│  Base: bills, votes, legislators, committees                    │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ANALYSIS MODULES                              │
├─────────────────────────────────────────────────────────────────┤
│ Embeddings → Vector representations (384-768 dims)              │
│ Sentiment  → Positive/Negative/Neutral classification           │
│ NLP        → Entity extraction, POS tagging                     │
│ Bias       → Political bias detection, objectivity              │
│ Consistency→ Voting patterns, flip-flops                        │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ANALYSIS TABLES                               │
│  bill_embeddings, sentiment_analysis, extracted_entities,       │
│  bias_analysis, consistency_analysis, etc.                      │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    QUERIES & VISUALIZATION                       │
│  SQL queries → Views → APIs → Dashboards                        │
│  (for OpenDiscourse.net)                                        │
└─────────────────────────────────────────────────────────────────┘
```

## Analysis Capabilities

### 🔍 Embeddings & Similarity
- **Models**: sentence-transformers (all-MiniLM-L6-v2, all-mpnet-base-v2)
- **Dimensions**: 384-768
- **Use Cases**: Find similar bills, topic clustering, semantic search
- **Performance**: GPU acceleration available, batch processing

### 📊 Sentiment Analysis
- **Models**: VADER (political text), TextBlob, DistilBERT
- **Output**: Positive/Negative/Neutral + confidence scores
- **Scale**: -1 (negative) to +1 (positive)
- **Best For**: Bill summaries, speeches, statements

### 🏷️ Entity Extraction
- **Model**: spaCy (en_core_web_sm/lg)
- **Entities**: PERSON, ORG, GPE, LOC, LAW, DATE, etc.
- **Features**: POS tagging, dependency parsing, key phrases
- **Output**: Entity text, label, position, confidence

### ⚖️ Bias Detection
- **Methods**: Rule-based + ML (optional)
- **Scale**: -1 (left) to +1 (right)
- **Metrics**: Overall bias, objectivity, loaded language
- **Features**: Framing analysis, rhetorical devices

### 📈 Consistency Analysis
- **Metrics**: Overall consistency, party-line voting %
- **Tracking**: Position changes, flip-flops, issue consistency
- **Comparison**: Politician voting similarity
- **Bipartisan**: Cross-party collaboration score

## Quick Commands

```bash
# Setup
pip install -r requirements.txt requirements-analysis.txt
python -m spacy download en_core_web_sm
psql $DATABASE_URL -f app/db/migrations/002_analysis_tables.sql

# Generate embeddings
python examples/embeddings_example.py

# Run full analysis
python examples/complete_analysis_pipeline.py

# Query results
psql $DATABASE_URL -c "SELECT * FROM top_similar_bills LIMIT 10;"
psql $DATABASE_URL -c "SELECT * FROM politician_consistency_summary;"
```

## Statistics

- **Files Created**: 28
- **Lines of Code**: ~20,000
  - Python: ~15,000
  - SQL: ~500
  - Documentation: ~5,000
- **Database Tables**: 12 analysis tables + 4 views
- **Data Sources**: 10+ APIs documented
- **Models Supported**: 10+ NLP/ML models

## Technologies

**Languages**: Python, SQL, Markdown
**Frameworks**: spaCy, sentence-transformers, transformers
**Database**: PostgreSQL
**Models**: VADER, TextBlob, DistilBERT, spaCy, sentence-transformers
**Data Processing**: numpy, pandas, scipy

---

*Created: 2025-10-14 for OpenDiscourse.net project*
