# Quick Start Guide for OpenGovt Analysis

This guide will get you up and running with the OpenGovt analysis platform for the OpenDiscourse.net project.

## Prerequisites

- Python 3.8+
- PostgreSQL 12+
- 8GB+ RAM (for embeddings models)
- Optional: CUDA-capable GPU for faster processing

## Step 1: Clone and Setup

```bash
# Clone the repository
git clone https://github.com/cbwinslow/opengovt.git
cd opengovt

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install base dependencies
pip install -r requirements.txt

# Install analysis dependencies
pip install -r requirements-analysis.txt
```

## Step 2: Download Required Models

```bash
# spaCy English model (required for NLP)
python -m spacy download en_core_web_sm

# Optional: Larger model for better accuracy
python -m spacy download en_core_web_lg

# NLTK data
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"
```

## Step 3: Database Setup

```bash
# Set database connection string
export DATABASE_URL="postgresql://user:password@localhost:5432/congress"

# Create database (if it doesn't exist)
createdb congress

# Run migrations
psql $DATABASE_URL -f app/db/migrations/001_init.sql
psql $DATABASE_URL -f app/db/migrations/002_analysis_tables.sql
```

## Step 4: Ingest Data

### Option A: Using existing scripts

```bash
# Discover and download data
python cbw_main.py \
  --start-congress 118 \
  --end-congress 118 \
  --download \
  --extract \
  --postprocess \
  --db "$DATABASE_URL"
```

### Option B: Using universal ingest

```bash
# Ingest OpenStates data
python congress_api/universal_ingest.py \
  --openstates path/to/openstates/*.json \
  --db "$DATABASE_URL"

# Ingest govinfo data
python congress_api/universal_ingest.py \
  --govinfo path/to/govinfo/ \
  --db "$DATABASE_URL"
```

## Step 5: Run Analysis

### Quick Test with Examples

```bash
# Generate embeddings and find similar bills
python examples/embeddings_example.py

# Run complete analysis pipeline
python examples/complete_analysis_pipeline.py
```

### Custom Analysis Script

```python
from analysis.embeddings import EmbeddingsGenerator
from analysis.sentiment import SentimentAnalyzer
from analysis.nlp_processor import NLPProcessor
from analysis.bias_detector import BiasDetector
import psycopg2

# Connect to database
conn = psycopg2.connect("postgresql://user:pass@localhost/congress")

# Fetch a bill
cursor = conn.cursor()
cursor.execute("""
    SELECT b.id, b.bill_number, bt.content
    FROM bills b
    JOIN bill_texts bt ON b.id = bt.bill_id
    LIMIT 1
""")
bill_id, bill_number, bill_text = cursor.fetchone()

# Initialize analyzers
embeddings_gen = EmbeddingsGenerator()
sentiment_analyzer = SentimentAnalyzer()
nlp_processor = NLPProcessor()
bias_detector = BiasDetector()

# Run analyses
print(f"Analyzing {bill_number}...")

# Generate embedding
embedding = embeddings_gen.encode_bill(bill_text, bill_id)
print(f"Embedding dimension: {len(embedding.embedding_vector)}")

# Analyze sentiment
sentiment = sentiment_analyzer.analyze(bill_text)
print(f"Sentiment: {sentiment.sentiment_label} ({sentiment.compound_score:.3f})")

# Extract entities
result = nlp_processor.process(bill_text)
print(f"Found {len(result.entities)} entities")

# Detect bias
bias = bias_detector.detect(bill_text)
print(f"Bias: {bias.overall_bias} (objectivity: {bias.objectivity_score:.3f})")

conn.close()
```

## Step 6: Query Analysis Results

```sql
-- Connect to database
psql $DATABASE_URL

-- View latest sentiment scores
SELECT * FROM latest_bill_sentiment LIMIT 10;

-- Find similar bills
SELECT * FROM top_similar_bills LIMIT 10;

-- Get politician consistency summary
SELECT * FROM politician_consistency_summary
WHERE current_party = 'Democrat'
ORDER BY overall_consistency DESC;

-- Find bills with entities
SELECT
    b.bill_number,
    b.title,
    string_agg(DISTINCT ee.entity_text, ', ') as entities
FROM bills b
JOIN extracted_entities ee ON b.id = ee.text_id
WHERE ee.entity_label = 'PERSON'
GROUP BY b.id, b.bill_number, b.title
LIMIT 10;
```

## Common Workflows

### Workflow 1: Find Bills Similar to a Topic

```python
from analysis.embeddings import EmbeddingsGenerator
import psycopg2
import numpy as np

# Topic query
topic = "healthcare reform and insurance coverage"

# Connect and fetch embeddings
conn = psycopg2.connect(DB_URL)
generator = EmbeddingsGenerator()

# Encode topic
topic_embedding = generator.encode([topic])[0]

# Fetch all bill embeddings
cursor = conn.cursor()
cursor.execute("""
    SELECT bill_id, embedding_vector
    FROM bill_embeddings
    WHERE model_name = 'all-MiniLM-L6-v2'
""")

# Calculate similarities
similarities = []
for bill_id, embedding_vector in cursor.fetchall():
    sim = generator.compute_similarity(
        topic_embedding,
        np.array(embedding_vector)
    )
    similarities.append((bill_id, sim))

# Sort and display top 10
similarities.sort(key=lambda x: x[1], reverse=True)
for bill_id, sim in similarities[:10]:
    cursor.execute("SELECT bill_number, title FROM bills WHERE id = %s", (bill_id,))
    bill_number, title = cursor.fetchone()
    print(f"{bill_number}: {title[:60]}... (similarity: {sim:.3f})")

conn.close()
```

### Workflow 2: Track Politician Consistency

```python
from analysis.consistency_analyzer import ConsistencyAnalyzer, VoteRecord
import psycopg2
from datetime import datetime

conn = psycopg2.connect(DB_URL)
analyzer = ConsistencyAnalyzer()

# Fetch votes for a legislator
cursor = conn.cursor()
cursor.execute("""
    SELECT v.id, v.bill_id, vr.vote_choice, v.vote_date, b.title
    FROM votes v
    JOIN vote_records vr ON v.id = vr.vote_id
    JOIN bills b ON v.bill_id = b.id
    WHERE vr.member_name = 'Senator Smith'
    ORDER BY v.vote_date
""")

votes = []
for vote_id, bill_id, choice, date, title in cursor.fetchall():
    votes.append(VoteRecord(
        vote_id=vote_id,
        bill_id=bill_id,
        person_id=1,  # Look up person_id
        vote_choice=choice,
        vote_date=date,
        bill_title=title,
    ))

# Analyze consistency
score = analyzer.analyze_voting_consistency(
    person_id=1,
    votes=votes,
    party='Democrat'
)

print(f"Overall consistency: {score.overall_consistency:.2f}")
print(f"Party line voting: {score.party_line_voting:.2%}")
print(f"Position changes: {len(score.position_changes)}")

conn.close()
```

### Workflow 3: Batch Analysis Pipeline

```python
from analysis.sentiment import SentimentAnalyzer
from analysis.nlp_processor import NLPProcessor
import psycopg2

conn = psycopg2.connect(DB_URL)
sentiment_analyzer = SentimentAnalyzer()
nlp_processor = NLPProcessor()

# Fetch unanalyzed bills
cursor = conn.cursor()
cursor.execute("""
    SELECT b.id, b.bill_number, bt.content
    FROM bills b
    JOIN bill_texts bt ON b.id = bt.bill_id
    LEFT JOIN sentiment_analysis sa ON b.id = sa.text_id AND sa.text_type = 'bill'
    WHERE sa.id IS NULL
    LIMIT 100
""")

bills = cursor.fetchall()

print(f"Processing {len(bills)} bills...")

for bill_id, bill_number, content in bills:
    print(f"Analyzing {bill_number}...")
    
    # Sentiment
    sentiment = sentiment_analyzer.analyze(content, text_id=bill_id, text_type='bill')
    
    # Store sentiment
    cursor.execute("""
        INSERT INTO sentiment_analysis
            (text_id, text_type, model_name, compound_score,
             sentiment_label, confidence, analyzed_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        sentiment.text_id, sentiment.text_type, sentiment.model_name,
        sentiment.compound_score, sentiment.sentiment_label,
        sentiment.confidence, sentiment.analyzed_at
    ))
    
    # Extract entities
    result = nlp_processor.process(content[:5000], text_id=bill_id, text_type='bill')
    
    # Store entities
    for entity in result.entities:
        cursor.execute("""
            INSERT INTO extracted_entities
                (text_id, text_type, entity_text, entity_label,
                 start_char, end_char, extracted_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            result.text_id, result.text_type, entity.text, entity.label,
            entity.start_char, entity.end_char, result.processed_at
        ))
    
    conn.commit()

print("Analysis complete!")
conn.close()
```

## Performance Tips

### For Large Datasets

1. **Use batch processing**: Process bills in batches of 100-1000
2. **Enable GPU**: Set `device='cuda'` for embeddings (10-100x faster)
3. **Parallel processing**: Use multiprocessing for CPU-bound tasks
4. **Cache models**: Initialize analyzers once and reuse

### For Memory Constraints

1. **Use smaller models**: `en_core_web_sm` instead of `en_core_web_lg`
2. **Process in chunks**: Don't load all data into memory at once
3. **Disable unused features**: Disable spaCy components you don't need
4. **Truncate long texts**: Limit text to first 5000 characters

### For Database Performance

1. **Batch inserts**: Insert multiple rows at once
2. **Disable autocommit**: Use transactions
3. **Create indexes**: On frequently queried columns
4. **Vacuum regularly**: Run `VACUUM ANALYZE` periodically

## Troubleshooting

### Issue: spaCy model not found

```bash
# Download the model
python -m spacy download en_core_web_sm
```

### Issue: Out of memory with embeddings

```python
# Use a smaller model or reduce batch size
generator = EmbeddingsGenerator(model_name='all-MiniLM-L6-v2')
embeddings = generator.encode_bills_batch(bills, batch_size=4)
```

### Issue: Slow processing

```python
# Disable unused spaCy components
processor = NLPProcessor(disable=['parser', 'tagger'])

# Or truncate text
text = bill_text[:5000]  # First 5000 chars only
```

### Issue: Database connection errors

```bash
# Check connection string format
export DATABASE_URL="postgresql://user:password@host:port/database"

# Test connection
psql $DATABASE_URL -c "SELECT 1"
```

## Next Steps

1. **Explore the documentation**: See `docs/ANALYSIS_MODULES.md` for detailed API reference
2. **Read the resources guide**: Check `docs/GOVERNMENT_DATA_RESOURCES.md` for data sources
3. **Review example scripts**: Look at `examples/` directory for more use cases
4. **Customize analysis**: Extend the modules for your specific needs
5. **Build visualizations**: Create dashboards using the analysis results

## Support Resources

- **GitHub Issues**: https://github.com/cbwinslow/opengovt/issues
- **Documentation**: See `docs/` directory
- **Examples**: See `examples/` directory
- **API Reference**: See module docstrings

---

*Last Updated: 2025-10-14*
*Part of the OpenDiscourse.net project*
