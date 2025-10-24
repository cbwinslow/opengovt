# SQL and Vector Databases for Political Analysis

## Overview

This document explores how SQL and vector databases are used to analyze political data at scale, including voting records, legislative documents, speeches, and social media content.

## 1. SQL Databases for Political Data

### 1.1 Why SQL for Political Analysis?

SQL databases excel at:
- **Structured data**: Votes, sponsors, committees, dates
- **Relational queries**: Finding voting patterns, co-sponsorships
- **Aggregations**: Counting votes, calculating percentages
- **Time-series analysis**: Tracking changes over time
- **ACID compliance**: Data integrity for critical political records

### 1.2 Schema Design for Political Data

#### Core Tables

```sql
-- Politicians/Members
CREATE TABLE politicians (
    id SERIAL PRIMARY KEY,
    bioguide_id VARCHAR(7) UNIQUE,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    party VARCHAR(50),
    state VARCHAR(2),
    district VARCHAR(10),
    chamber VARCHAR(20), -- 'house' or 'senate'
    term_start DATE,
    term_end DATE,
    twitter_handle VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Bills
CREATE TABLE bills (
    id SERIAL PRIMARY KEY,
    bill_number VARCHAR(20),
    congress INTEGER,
    bill_type VARCHAR(10),
    title TEXT,
    summary TEXT,
    introduced_date DATE,
    status VARCHAR(50),
    UNIQUE (congress, bill_type, bill_number)
);

-- Votes
CREATE TABLE votes (
    id SERIAL PRIMARY KEY,
    politician_id INTEGER REFERENCES politicians(id),
    bill_id INTEGER REFERENCES bills(id),
    vote VARCHAR(20), -- 'Yea', 'Nay', 'Present', 'Not Voting'
    vote_date TIMESTAMP,
    roll_call_number INTEGER
);

-- Sponsorships
CREATE TABLE bill_sponsorships (
    id SERIAL PRIMARY KEY,
    bill_id INTEGER REFERENCES bills(id),
    politician_id INTEGER REFERENCES politicians(id),
    sponsorship_type VARCHAR(20), -- 'primary' or 'cosponsor'
    date_added DATE
);
```

### 1.3 Advanced Analytical Queries

#### Voting Consistency Analysis

```sql
-- Calculate how often a politician votes with their party
WITH party_votes AS (
    SELECT 
        v.politician_id,
        v.bill_id,
        v.vote,
        p.party,
        -- Determine party majority vote
        MODE() WITHIN GROUP (ORDER BY v2.vote) 
            FILTER (WHERE p2.party = p.party) as party_position
    FROM votes v
    JOIN politicians p ON v.politician_id = p.id
    JOIN votes v2 ON v.bill_id = v2.bill_id
    JOIN politicians p2 ON v2.politician_id = p2.id
    GROUP BY v.politician_id, v.bill_id, v.vote, p.party
)
SELECT 
    politician_id,
    COUNT(*) as total_votes,
    SUM(CASE WHEN vote = party_position THEN 1 ELSE 0 END) as votes_with_party,
    ROUND(100.0 * SUM(CASE WHEN vote = party_position THEN 1 ELSE 0 END) / COUNT(*), 2) as party_loyalty_pct
FROM party_votes
GROUP BY politician_id
ORDER BY party_loyalty_pct DESC;
```

#### Flip-Flop Detection

```sql
-- Find politicians who changed positions on similar bills
WITH similar_bills AS (
    SELECT 
        b1.id as bill_id_1,
        b2.id as bill_id_2,
        similarity(b1.title, b2.title) as title_similarity
    FROM bills b1
    JOIN bills b2 ON b1.congress < b2.congress
    WHERE similarity(b1.title, b2.title) > 0.7
),
position_changes AS (
    SELECT 
        v1.politician_id,
        sb.bill_id_1,
        sb.bill_id_2,
        v1.vote as earlier_vote,
        v2.vote as later_vote,
        b1.title as bill_1_title,
        b2.title as bill_2_title
    FROM similar_bills sb
    JOIN votes v1 ON sb.bill_id_1 = v1.bill_id
    JOIN votes v2 ON sb.bill_id_2 = v2.bill_id AND v1.politician_id = v2.politician_id
    JOIN bills b1 ON sb.bill_id_1 = b1.id
    JOIN bills b2 ON sb.bill_id_2 = b2.id
    WHERE v1.vote != v2.vote
        AND v1.vote IN ('Yea', 'Nay')
        AND v2.vote IN ('Yea', 'Nay')
)
SELECT * FROM position_changes;
```

#### Bipartisan Cooperation Analysis

```sql
-- Find politicians who frequently co-sponsor bills with opposite party
SELECT 
    p1.id as politician_id,
    p1.first_name || ' ' || p1.last_name as politician_name,
    p1.party,
    COUNT(DISTINCT bs2.bill_id) as cross_party_cosponsorships,
    COUNT(DISTINCT bs1.bill_id) as total_cosponsorships,
    ROUND(100.0 * COUNT(DISTINCT bs2.bill_id) / COUNT(DISTINCT bs1.bill_id), 2) as bipartisan_pct
FROM politicians p1
JOIN bill_sponsorships bs1 ON p1.id = bs1.politician_id
JOIN bill_sponsorships bs2 ON bs1.bill_id = bs2.bill_id
JOIN politicians p2 ON bs2.politician_id = p2.id
WHERE p1.party != p2.party
    AND p1.party IN ('Democrat', 'Republican')
    AND p2.party IN ('Democrat', 'Republican')
GROUP BY p1.id, p1.first_name, p1.last_name, p1.party
ORDER BY bipartisan_pct DESC;
```

### 1.4 Time-Series Analysis with Window Functions

```sql
-- Track voting pattern changes over time
SELECT 
    politician_id,
    DATE_TRUNC('month', vote_date) as month,
    AVG(CASE WHEN vote = 'Yea' THEN 1.0 ELSE 0.0 END) as yes_vote_rate,
    LAG(AVG(CASE WHEN vote = 'Yea' THEN 1.0 ELSE 0.0 END)) 
        OVER (PARTITION BY politician_id ORDER BY DATE_TRUNC('month', vote_date)) as prev_month_rate
FROM votes
WHERE vote IN ('Yea', 'Nay')
GROUP BY politician_id, DATE_TRUNC('month', vote_date)
ORDER BY politician_id, month;
```

## 2. Vector Databases for Semantic Search

### 2.1 Why Vector Databases?

Vector databases enable:
- **Semantic search**: Find similar bills by meaning, not just keywords
- **Clustering**: Group similar legislative documents
- **Recommendation**: "Politicians who voted for this also voted for..."
- **Similarity scoring**: Measure how close two positions are

### 2.2 Vector Database Options

#### Option 1: pgvector (PostgreSQL Extension)

**Pros:**
- Native PostgreSQL integration
- No separate infrastructure needed
- ACID compliance
- Mature SQL ecosystem

**Cons:**
- Slower for very large datasets (>1M vectors)
- Limited to L2 and cosine similarity

**Setup:**

```sql
-- Install extension
CREATE EXTENSION vector;

-- Add vector column to bills table
ALTER TABLE bills ADD COLUMN embedding vector(384);

-- Create index for fast similarity search
CREATE INDEX ON bills USING ivfflat (embedding vector_cosine_ops);
```

**Queries:**

```sql
-- Find similar bills using cosine similarity
SELECT 
    id,
    title,
    1 - (embedding <=> :query_embedding) as similarity
FROM bills
ORDER BY embedding <=> :query_embedding
LIMIT 10;
```

#### Option 2: Pinecone

**Pros:**
- Purpose-built for vector search
- Extremely fast at scale
- Managed service (no ops)
- Metadata filtering

**Cons:**
- Separate service to manage
- Additional cost
- Data duplication from main DB

**Python Example:**

```python
import pinecone
from sentence_transformers import SentenceTransformer

# Initialize
pinecone.init(api_key="YOUR_API_KEY", environment="us-west1-gcp")
index = pinecone.Index("political-bills")

# Create embeddings
model = SentenceTransformer('all-MiniLM-L6-v2')
bill_embedding = model.encode("Healthcare reform bill text...")

# Insert
index.upsert([
    ("bill-117-hr-1234", bill_embedding.tolist(), {
        "congress": 117,
        "title": "Healthcare Reform Act",
        "sponsor": "Rep. Smith"
    })
])

# Query
results = index.query(
    vector=query_embedding.tolist(),
    top_k=10,
    include_metadata=True,
    filter={"congress": 117}
)
```

#### Option 3: Weaviate

**Pros:**
- Built-in vectorization (no external embedding service)
- GraphQL API
- Multi-modal support (text, images)
- Strong filtering capabilities

**Cons:**
- Requires separate hosting
- More complex setup

**Schema Example:**

```json
{
  "class": "PoliticalBill",
  "vectorizer": "text2vec-transformers",
  "moduleConfig": {
    "text2vec-transformers": {
      "poolingStrategy": "masked_mean",
      "model": "sentence-transformers/all-MiniLM-L6-v2"
    }
  },
  "properties": [
    {"name": "billNumber", "dataType": ["string"]},
    {"name": "title", "dataType": ["text"]},
    {"name": "summary", "dataType": ["text"]},
    {"name": "congress", "dataType": ["int"]},
    {"name": "sponsor", "dataType": ["string"]}
  ]
}
```

### 2.3 Hybrid Approach: SQL + Vectors

Most production systems use both:

```python
class PoliticalAnalysisDB:
    def __init__(self, postgres_url, pinecone_api_key):
        self.pg = psycopg2.connect(postgres_url)
        self.pinecone = pinecone.Index("bills")
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
    
    def add_bill(self, bill_data):
        # 1. Store structured data in PostgreSQL
        with self.pg.cursor() as cur:
            cur.execute("""
                INSERT INTO bills (bill_number, title, summary, congress)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (bill_data['number'], bill_data['title'], 
                  bill_data['summary'], bill_data['congress']))
            bill_id = cur.fetchone()[0]
        
        # 2. Store embedding in vector DB
        embedding = self.embedder.encode(bill_data['summary'])
        self.pinecone.upsert([
            (f"bill-{bill_id}", embedding.tolist(), {
                "bill_id": bill_id,
                "congress": bill_data['congress']
            })
        ])
        
        self.pg.commit()
    
    def find_similar_bills(self, query_text, congress=None, limit=10):
        # 1. Find similar vectors
        query_embedding = self.embedder.encode(query_text)
        vector_results = self.pinecone.query(
            vector=query_embedding.tolist(),
            top_k=limit,
            filter={"congress": congress} if congress else None
        )
        
        # 2. Fetch full data from PostgreSQL
        bill_ids = [int(r.metadata['bill_id']) for r in vector_results.matches]
        with self.pg.cursor() as cur:
            cur.execute("""
                SELECT * FROM bills WHERE id = ANY(%s)
            """, (bill_ids,))
            bills = cur.fetchall()
        
        return bills
```

## 3. Case Studies

### 3.1 FiveThirtyEight's Congress Tracker

**Technologies:**
- PostgreSQL for votes and member data
- Python + pandas for analysis
- R for statistical modeling
- D3.js for visualization

**Key Metrics:**
- Trump Score: How often members vote with Trump
- Pivotal Votes: Members who changed outcomes
- Party Unity: Voting with party percentage

**Source:** https://projects.fivethirtyeight.com/congress-trump-score/

### 3.2 ProPublica's Represent API

**Technologies:**
- PostgreSQL database
- RESTful API (Python/Django)
- Real-time vote ingestion from Congress.gov

**Features:**
- Member profiles with voting records
- Bill tracking and sponsorship
- Committee assignments
- Financial disclosures

**API Example:**

```bash
curl "https://api.propublica.org/congress/v1/117/senate/members.json" \
  -H "X-API-Key: YOUR_API_KEY"
```

**Source:** https://projects.propublica.org/api-docs/congress-api/

### 3.3 GovTrack's Bill Similarity Engine

**Technologies:**
- PostgreSQL + full-text search
- TF-IDF vectorization
- Cosine similarity scoring

**Approach:**
1. Extract bill text from XML
2. Generate TF-IDF vectors
3. Calculate pairwise similarities
4. Store in similarity matrix table

**Query Pattern:**

```sql
SELECT 
    b2.bill_number,
    b2.title,
    bs.similarity_score
FROM bill_similarities bs
JOIN bills b2 ON bs.bill_id_2 = b2.id
WHERE bs.bill_id_1 = :target_bill_id
ORDER BY bs.similarity_score DESC
LIMIT 10;
```

### 3.4 VoteSmart's Political Courage Test

**Technologies:**
- MySQL database
- Issue position tracking
- Vote-to-position matching algorithm

**Methodology:**
1. Categorize bills by issue (healthcare, immigration, etc.)
2. Map votes to positions (pro/anti)
3. Calculate consistency within issue areas
4. Flag position changes over time

## 4. Performance Optimization

### 4.1 Indexing Strategies

```sql
-- Compound indexes for common queries
CREATE INDEX idx_votes_politician_date ON votes(politician_id, vote_date);
CREATE INDEX idx_bills_congress_type ON bills(congress, bill_type);

-- Partial indexes for active records
CREATE INDEX idx_active_politicians ON politicians(id) 
WHERE term_end > CURRENT_DATE;

-- GiST index for similarity searches (PostgreSQL)
CREATE INDEX idx_bills_title_similarity ON bills 
USING gist (title gist_trgm_ops);
```

### 4.2 Query Optimization

```sql
-- Use CTEs for complex queries
WITH recent_votes AS (
    SELECT * FROM votes 
    WHERE vote_date > NOW() - INTERVAL '1 year'
),
party_positions AS (
    SELECT bill_id, party, MODE() WITHIN GROUP (ORDER BY vote) as party_vote
    FROM recent_votes rv
    JOIN politicians p ON rv.politician_id = p.id
    GROUP BY bill_id, party
)
SELECT ... FROM recent_votes ...;

-- Materialize frequently-accessed aggregations
CREATE MATERIALIZED VIEW politician_stats AS
SELECT 
    politician_id,
    COUNT(*) as total_votes,
    SUM(CASE WHEN vote = 'Yea' THEN 1 ELSE 0 END) as yes_votes,
    AVG(CASE WHEN vote = 'Yea' THEN 1 ELSE 0 END) as yes_percentage
FROM votes
GROUP BY politician_id;

CREATE INDEX ON politician_stats(politician_id);
```

### 4.3 Partitioning for Large Datasets

```sql
-- Partition votes by year
CREATE TABLE votes_2023 PARTITION OF votes
FOR VALUES FROM ('2023-01-01') TO ('2024-01-01');

CREATE TABLE votes_2024 PARTITION OF votes
FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
```

## 5. Real-World Implementation Patterns

### 5.1 Lambda Architecture for Political Data

```
┌─────────────────┐
│  Data Sources   │
│ Congress.gov    │
│ Twitter API     │
│ GovTrack        │
└────────┬────────┘
         │
    ┌────▼─────┐
    │ Ingestion│
    │  Layer   │
    └────┬─────┘
         │
    ┌────▼─────┐
    │  Batch   │──────► PostgreSQL (structured data)
    │ Processing│
    └──────────┘
         │
    ┌────▼─────┐
    │  Stream  │──────► Redis (real-time)
    │Processing│
    └──────────┘
         │
    ┌────▼─────┐
    │  Serving │──────► API Layer
    │  Layer   │
    └──────────┘
```

### 5.2 ETL Pipeline Example

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'political-analytics',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'retries': 3,
    'retry_delay': timedelta(minutes=5)
}

dag = DAG(
    'political_data_pipeline',
    default_args=default_args,
    schedule_interval='@daily'
)

def extract_votes():
    """Fetch votes from Congress.gov API"""
    # Implementation
    pass

def transform_votes():
    """Normalize and enrich vote data"""
    # Implementation
    pass

def load_votes():
    """Load into PostgreSQL"""
    # Implementation
    pass

def generate_embeddings():
    """Create vector embeddings for bills"""
    # Implementation
    pass

extract = PythonOperator(task_id='extract', python_callable=extract_votes, dag=dag)
transform = PythonOperator(task_id='transform', python_callable=transform_votes, dag=dag)
load = PythonOperator(task_id='load', python_callable=load_votes, dag=dag)
embed = PythonOperator(task_id='embed', python_callable=generate_embeddings, dag=dag)

extract >> transform >> load >> embed
```

## 6. References and Further Reading

### Academic Papers
1. **"Congressional Bill Similarity Using Deep Neural Networks"** - ACL 2019
2. **"Predicting Legislative Roll Calls with Vector Representations"** - Political Analysis 2020
3. **"Embedding Political Discourse for Stance Detection"** - EMNLP 2021

### Industry Resources
- **ProPublica Congress API**: https://projects.propublica.org/api-docs/congress-api/
- **GovTrack Data Downloads**: https://www.govtrack.us/developers
- **pgvector Documentation**: https://github.com/pgvector/pgvector
- **Pinecone Political Use Cases**: https://www.pinecone.io/learn/

### Open Source Projects
- **OpenStates**: State legislative data (https://github.com/openstates/openstates)
- **unitedstates/congress**: Congressional data scrapers (https://github.com/unitedstates/congress)
- **Congress.gov API**: Official API (https://api.congress.gov/)

### Tutorials
- **Building a Political Analysis Dashboard**: DataCamp
- **Vector Search for Legislative Documents**: Pinecone Blog
- **Advanced PostgreSQL for Analytics**: PostgreSQL Wiki

---

**Last Updated**: 2025-10-23
**Next**: [02-nlp-text-analysis.md](02-nlp-text-analysis.md)
