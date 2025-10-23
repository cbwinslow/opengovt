# Implementation Guide: Building a Political Analysis System

## Overview

This guide provides practical, step-by-step instructions for implementing a comprehensive political analysis system using the techniques and methodologies covered in this research folder.

## 1. System Architecture

### 1.1 Overall Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     DATA INGESTION LAYER                      │
├──────────────────────────────────────────────────────────────┤
│  Congress.gov API  │  Twitter API  │  ProPublica  │ GovTrack │
│  RSS Feeds         │  Web Scrapers │  Press Releases        │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────────┐
│                    PROCESSING PIPELINE                        │
├──────────────────────────────────────────────────────────────┤
│  Text Cleaning  │  NLP Processing  │  Embedding Generation   │
│  Sentiment      │  Toxicity Check  │  Entity Extraction      │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────────┐
│                      STORAGE LAYER                            │
├──────────────────────────────────────────────────────────────┤
│  PostgreSQL (Structured)  │  pgvector (Embeddings)           │
│  Redis (Cache)            │  S3 (Documents)                  │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────────┐
│                     ANALYSIS ENGINE                           │
├──────────────────────────────────────────────────────────────┤
│  Bias Detection  │  Consistency  │  Impact Measurement       │
│  Similarity      │  Trends       │  Predictions              │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────────┐
│                         API LAYER                             │
├──────────────────────────────────────────────────────────────┤
│  REST API  │  GraphQL  │  WebSocket (Real-time)              │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                         │
├──────────────────────────────────────────────────────────────┤
│  Web Dashboard  │  Mobile App  │  Visualizations             │
└──────────────────────────────────────────────────────────────┘
```

### 1.2 Technology Stack

```python
TECH_STACK = {
    'backend': {
        'language': 'Python 3.10+',
        'framework': 'FastAPI / Django',
        'async': 'asyncio, aiohttp'
    },
    'database': {
        'primary': 'PostgreSQL 14+',
        'vector': 'pgvector extension',
        'cache': 'Redis',
        'object_storage': 'MinIO / AWS S3'
    },
    'nlp': {
        'framework': 'spaCy, Hugging Face Transformers',
        'models': 'BERT, sentence-transformers, VADER',
        'gpu': 'CUDA-enabled for production'
    },
    'api': {
        'rest': 'FastAPI',
        'graphql': 'Strawberry GraphQL',
        'websocket': 'FastAPI WebSocket'
    },
    'frontend': {
        'framework': 'React / Next.js',
        'visualization': 'D3.js, Plotly',
        'ui': 'Tailwind CSS'
    },
    'infrastructure': {
        'containerization': 'Docker',
        'orchestration': 'Kubernetes / Docker Compose',
        'ci_cd': 'GitHub Actions',
        'monitoring': 'Prometheus, Grafana'
    }
}
```

## 2. Step-by-Step Implementation

### 2.1 Phase 1: Foundation (Weeks 1-2)

#### Setup Development Environment

```bash
# Create project structure
mkdir political-analysis-platform
cd political-analysis-platform

# Initialize git
git init

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install fastapi uvicorn sqlalchemy psycopg2-binary \
    spacy sentence-transformers transformers \
    tweepy vaderSentiment detoxify \
    redis celery prometheus-client

# Download spaCy model
python -m spacy download en_core_web_lg

# Create directory structure
mkdir -p {src,tests,docs,data,scripts,config}
mkdir -p src/{api,models,services,workers,utils}
```

#### Database Setup

```sql
-- Create database
CREATE DATABASE political_analysis;

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS pgvector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- For similarity search

-- Create base tables (see 01-sql-vector-databases.md for full schema)
CREATE TABLE politicians (
    id SERIAL PRIMARY KEY,
    bioguide_id VARCHAR(7) UNIQUE,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    party VARCHAR(50),
    state VARCHAR(2),
    chamber VARCHAR(20),
    twitter_handle VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE bills (
    id SERIAL PRIMARY KEY,
    bill_number VARCHAR(20),
    congress INTEGER,
    title TEXT,
    summary TEXT,
    embedding vector(768),  -- Using pgvector
    created_at TIMESTAMP DEFAULT NOW()
);

-- Add indexes
CREATE INDEX ON bills USING ivfflat (embedding vector_cosine_ops);
```

#### Configuration Management

```python
# config/settings.py
from pydantic import BaseSettings

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://user:pass@localhost/political_analysis"
    REDIS_URL: str = "redis://localhost:6379"
    
    # APIs
    CONGRESS_API_KEY: str
    TWITTER_BEARER_TOKEN: str
    PROPUBLICA_API_KEY: str
    
    # ML Models
    EMBEDDING_MODEL: str = "all-mpnet-base-v2"
    SENTIMENT_MODEL: str = "cardiffnlp/twitter-roberta-base-sentiment"
    
    # Processing
    BATCH_SIZE: int = 32
    MAX_WORKERS: int = 4
    
    class Config:
        env_file = ".env"

settings = Settings()
```

### 2.2 Phase 2: Data Ingestion (Weeks 3-4)

#### Congressional Data Ingestion

```python
# src/services/congress_ingester.py
import aiohttp
from datetime import datetime
from src.models.database import get_db
from src.models.bill import Bill

class CongressDataIngester:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.congress.gov/v3"
    
    async def ingest_bills(self, congress: int):
        """Ingest bills from Congress API"""
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/bill/{congress}"
            headers = {"X-Api-Key": self.api_key}
            
            async with session.get(url, headers=headers) as resp:
                data = await resp.json()
                
                bills = data.get('bills', [])
                
                db = next(get_db())
                for bill_data in bills:
                    bill = Bill(
                        bill_number=bill_data['number'],
                        congress=congress,
                        title=bill_data['title'],
                        summary=bill_data.get('summary', '')
                    )
                    db.add(bill)
                
                db.commit()
                
                return len(bills)
```

#### Twitter Data Collection

```python
# src/services/twitter_collector.py
import tweepy
from typing import List
from src.models.tweet import Tweet

class TwitterCollector:
    def __init__(self, bearer_token: str):
        self.client = tweepy.Client(bearer_token=bearer_token)
    
    async def collect_politician_tweets(self, username: str, days: int = 7):
        """Collect recent tweets from a politician"""
        user = self.client.get_user(username=username)
        
        tweets = self.client.get_users_tweets(
            id=user.data.id,
            max_results=100,
            tweet_fields=['created_at', 'public_metrics', 'entities'],
            start_time=datetime.now() - timedelta(days=days)
        )
        
        stored_tweets = []
        db = next(get_db())
        
        for tweet in tweets.data:
            tweet_obj = Tweet(
                tweet_id=tweet.id,
                politician_id=self._get_politician_id(username),
                text=tweet.text,
                created_at=tweet.created_at,
                like_count=tweet.public_metrics['like_count'],
                retweet_count=tweet.public_metrics['retweet_count']
            )
            db.add(tweet_obj)
            stored_tweets.append(tweet_obj)
        
        db.commit()
        return stored_tweets
```

### 2.3 Phase 3: NLP Pipeline (Weeks 5-6)

#### Text Processing Service

```python
# src/services/text_processor.py
import spacy
from sentence_transformers import SentenceTransformer
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

class TextProcessingService:
    def __init__(self):
        self.nlp = spacy.load("en_core_web_lg")
        self.embedder = SentenceTransformer('all-mpnet-base-v2')
        self.sentiment_analyzer = SentimentIntensityAnalyzer()
    
    def process_document(self, text: str) -> dict:
        """Complete NLP processing pipeline"""
        
        # spaCy processing
        doc = self.nlp(text)
        
        # Generate embedding
        embedding = self.embedder.encode(text)
        
        # Sentiment analysis
        sentiment = self.sentiment_analyzer.polarity_scores(text)
        
        # Entity extraction
        entities = [
            {
                'text': ent.text,
                'label': ent.label_,
                'start': ent.start_char,
                'end': ent.end_char
            }
            for ent in doc.ents
        ]
        
        return {
            'embedding': embedding.tolist(),
            'sentiment': sentiment,
            'entities': entities,
            'tokens': [token.text for token in doc],
            'sentences': [sent.text for sent in doc.sents]
        }
```

#### Background Workers (Celery)

```python
# src/workers/tasks.py
from celery import Celery
from src.services.text_processor import TextProcessingService

celery_app = Celery('political_analysis', broker='redis://localhost:6379')

@celery_app.task
def process_bill_text(bill_id: int):
    """Background task to process bill text"""
    processor = TextProcessingService()
    
    db = next(get_db())
    bill = db.query(Bill).filter(Bill.id == bill_id).first()
    
    if bill:
        result = processor.process_document(bill.summary)
        
        # Store embedding
        bill.embedding = result['embedding']
        
        # Store entities
        for ent in result['entities']:
            entity = Entity(
                bill_id=bill.id,
                text=ent['text'],
                label=ent['label']
            )
            db.add(entity)
        
        db.commit()
    
    return f"Processed bill {bill_id}"
```

### 2.4 Phase 4: Analysis Services (Weeks 7-8)

#### Similarity Search Service

```python
# src/services/similarity_service.py
from typing import List
from src.models.database import get_db
from src.models.bill import Bill

class SimilarityService:
    def find_similar_bills(self, bill_id: int, limit: int = 10) -> List[dict]:
        """Find similar bills using vector similarity"""
        db = next(get_db())
        
        target_bill = db.query(Bill).filter(Bill.id == bill_id).first()
        
        if not target_bill:
            return []
        
        # Use pgvector cosine similarity
        similar_bills = db.execute(f"""
            SELECT 
                id,
                bill_number,
                title,
                1 - (embedding <=> :target_embedding) as similarity
            FROM bills
            WHERE id != :bill_id
            ORDER BY embedding <=> :target_embedding
            LIMIT :limit
        """, {
            'target_embedding': target_bill.embedding,
            'bill_id': bill_id,
            'limit': limit
        }).fetchall()
        
        return [
            {
                'id': row.id,
                'bill_number': row.bill_number,
                'title': row.title,
                'similarity': float(row.similarity)
            }
            for row in similar_bills
        ]
```

#### Bias Detection Service

```python
# src/services/bias_detector.py
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

class BiasDetectionService:
    def __init__(self):
        self.tokenizer = AutoTokenizer.from_pretrained('bert-base-uncased')
        # Would use fine-tuned model in production
        self.model = AutoModelForSequenceClassification.from_pretrained(
            'bert-base-uncased',
            num_labels=3
        )
    
    def detect_bias(self, text: str) -> dict:
        """Detect political bias in text"""
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            max_length=512,
            truncation=True
        )
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
        
        labels = ['left', 'center', 'right']
        scores = probs[0].tolist()
        
        return {
            'bias_distribution': dict(zip(labels, scores)),
            'predicted_bias': labels[scores.index(max(scores))],
            'confidence': max(scores)
        }
```

### 2.5 Phase 5: API Development (Weeks 9-10)

#### REST API with FastAPI

```python
# src/api/main.py
from fastapi import FastAPI, Depends, HTTPException
from typing import List
from src.services.similarity_service import SimilarityService
from src.services.bias_detector import BiasDetectionService
from src.models.schemas import BillResponse, SimilarityResponse

app = FastAPI(title="Political Analysis API")

@app.get("/bills/{bill_id}", response_model=BillResponse)
async def get_bill(bill_id: int):
    """Get bill details"""
    db = next(get_db())
    bill = db.query(Bill).filter(Bill.id == bill_id).first()
    
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    
    return bill

@app.get("/bills/{bill_id}/similar", response_model=List[SimilarityResponse])
async def get_similar_bills(bill_id: int, limit: int = 10):
    """Find similar bills"""
    service = SimilarityService()
    return service.find_similar_bills(bill_id, limit)

@app.post("/analyze/bias")
async def analyze_bias(text: str):
    """Analyze political bias of text"""
    detector = BiasDetectionService()
    return detector.detect_bias(text)

@app.get("/politicians/{politician_id}/metrics")
async def get_politician_metrics(politician_id: int):
    """Get comprehensive politician metrics"""
    # Implementation from 03-political-metrics.md
    profile_gen = PoliticianProfileGenerator()
    return profile_gen.generate_complete_profile(politician_id)
```

### 2.6 Phase 6: Frontend Development (Weeks 11-12)

#### React Dashboard Component

```jsx
// src/frontend/components/PoliticianDashboard.jsx
import React, { useState, useEffect } from 'react';
import { LineChart, BarChart } from './Charts';

export default function PoliticianDashboard({ politicianId }) {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    fetchMetrics();
  }, [politicianId]);
  
  const fetchMetrics = async () => {
    const response = await fetch(`/api/politicians/${politicianId}/metrics`);
    const data = await response.json();
    setMetrics(data);
    setLoading(false);
  };
  
  if (loading) return <div>Loading...</div>;
  
  return (
    <div className="dashboard">
      <h1>{metrics.basic_info.name}</h1>
      
      <div className="metrics-grid">
        <MetricCard 
          title="Overall Score"
          value={metrics.overall_score.overall}
          grade={metrics.overall_score.grade}
        />
        
        <MetricCard 
          title="Transparency"
          value={metrics.transparency.transparency_index}
          grade={metrics.transparency.grade}
        />
        
        <MetricCard 
          title="Consistency"
          value={metrics.consistency.overall_consistency}
        />
      </div>
      
      <div className="charts">
        <BiasVisualization data={metrics.bias_analysis} />
        <ImpactChart data={metrics.impact} />
      </div>
    </div>
  );
}
```

## 3. Deployment

### 3.1 Docker Compose Setup

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: ankane/pgvector
    environment:
      POSTGRES_DB: political_analysis
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: secretpassword
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
  
  api:
    build: .
    command: uvicorn src.api.main:app --host 0.0.0.0 --port 8000
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://admin:secretpassword@postgres/political_analysis
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis
  
  worker:
    build: .
    command: celery -A src.workers.tasks worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql://admin:secretpassword@postgres/political_analysis
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis
  
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - api

volumes:
  postgres_data:
```

### 3.2 Kubernetes Deployment (Production)

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: political-analysis-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: political-analysis-api
  template:
    metadata:
      labels:
        app: political-analysis-api
    spec:
      containers:
      - name: api
        image: your-registry/political-analysis-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secrets
              key: url
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
```

## 4. Performance Optimization

### 4.1 Caching Strategy

```python
# src/utils/cache.py
import redis
import json
from functools import wraps

redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

def cache_result(expire_seconds=3600):
    """Cache decorator for expensive operations"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Create cache key
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Check cache
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Store in cache
            redis_client.setex(
                cache_key,
                expire_seconds,
                json.dumps(result)
            )
            
            return result
        return wrapper
    return decorator
```

### 4.2 Database Optimization

```sql
-- Partitioning for large tables
CREATE TABLE tweets (
    id BIGINT,
    politician_id INTEGER,
    text TEXT,
    created_at TIMESTAMP
) PARTITION BY RANGE (created_at);

CREATE TABLE tweets_2024 PARTITION OF tweets
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

-- Materialized views for expensive queries
CREATE MATERIALIZED VIEW politician_summary AS
SELECT 
    p.id,
    p.name,
    COUNT(DISTINCT b.id) as bills_sponsored,
    COUNT(DISTINCT v.id) as votes_cast,
    AVG(m.transparency_index) as avg_transparency
FROM politicians p
LEFT JOIN bills b ON b.sponsor_id = p.id
LEFT JOIN votes v ON v.politician_id = p.id
LEFT JOIN politician_metrics m ON m.politician_id = p.id
GROUP BY p.id, p.name;

-- Refresh periodically
REFRESH MATERIALIZED VIEW politician_summary;
```

## 5. Monitoring and Logging

### 5.1 Prometheus Metrics

```python
# src/utils/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
api_requests = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint'])
processing_time = Histogram('processing_seconds', 'Time spent processing')
active_workers = Gauge('active_workers', 'Number of active workers')

# Use in code
@api_requests.labels(method='GET', endpoint='/bills').count()
@processing_time.time()
def get_bills():
    # Implementation
    pass
```

### 5.2 Structured Logging

```python
# src/utils/logger.py
import logging
import json
from datetime import datetime

class StructuredLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        handler = logging.StreamHandler()
        handler.setFormatter(self.JSONFormatter())
        self.logger.addHandler(handler)
    
    class JSONFormatter(logging.Formatter):
        def format(self, record):
            log_obj = {
                'timestamp': datetime.utcnow().isoformat(),
                'level': record.levelname,
                'message': record.getMessage(),
                'module': record.module,
                'function': record.funcName
            }
            return json.dumps(log_obj)
    
    def info(self, message, **kwargs):
        self.logger.info(message, extra=kwargs)
```

## 6. Testing Strategy

### 6.1 Unit Tests

```python
# tests/test_bias_detector.py
import pytest
from src.services.bias_detector import BiasDetectionService

def test_bias_detection():
    detector = BiasDetectionService()
    
    # Test clearly biased text
    result = detector.detect_bias("Socialist healthcare destroys freedom")
    assert result['predicted_bias'] in ['left', 'right']
    assert result['confidence'] > 0.5

def test_neutral_text():
    detector = BiasDetectionService()
    
    result = detector.detect_bias("The bill was passed by the committee")
    assert result['predicted_bias'] == 'center'
```

### 6.2 Integration Tests

```python
# tests/test_api.py
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_get_bill():
    response = client.get("/bills/1")
    assert response.status_code == 200
    assert "bill_number" in response.json()

def test_similar_bills():
    response = client.get("/bills/1/similar?limit=5")
    assert response.status_code == 200
    assert len(response.json()) <= 5
```

## 7. Best Practices

### 7.1 Code Organization

```
src/
├── api/              # API endpoints
│   ├── routes/
│   ├── dependencies.py
│   └── main.py
├── models/           # Database models
│   ├── bill.py
│   ├── politician.py
│   └── database.py
├── services/         # Business logic
│   ├── bias_detector.py
│   ├── similarity.py
│   └── twitter_collector.py
├── workers/          # Background tasks
│   └── tasks.py
├── utils/            # Utilities
│   ├── cache.py
│   ├── logger.py
│   └── metrics.py
└── config/           # Configuration
    └── settings.py
```

### 7.2 Error Handling

```python
class PoliticalAnalysisError(Exception):
    """Base exception for political analysis errors"""
    pass

class DataNotFoundError(PoliticalAnalysisError):
    """Raised when requested data is not found"""
    pass

class AnalysisError(PoliticalAnalysisError):
    """Raised when analysis fails"""
    pass

# Use in code
try:
    bill = get_bill(bill_id)
except DataNotFoundError:
    logger.error(f"Bill {bill_id} not found")
    raise HTTPException(status_code=404, detail="Bill not found")
```

## 8. Security Considerations

### 8.1 API Authentication

```python
# src/api/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token"""
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=["HS256"]
        )
        return payload
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
```

### 8.2 Rate Limiting

```python
# src/api/middleware.py
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/bills")
@limiter.limit("100/hour")
async def get_bills(request: Request):
    # Implementation
    pass
```

## 9. Maintenance and Updates

### 9.1 Model Updates

```python
# scripts/update_models.py
def update_embedding_model():
    """Update to newer embedding model"""
    new_model = SentenceTransformer('all-mpnet-base-v2-updated')
    
    db = next(get_db())
    bills = db.query(Bill).all()
    
    for bill in bills:
        # Regenerate embedding
        new_embedding = new_model.encode(bill.summary)
        bill.embedding = new_embedding.tolist()
    
    db.commit()
    print(f"Updated embeddings for {len(bills)} bills")
```

### 9.2 Data Refresh Schedule

```python
# Use Celery Beat for scheduled tasks
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    'update-tweets-daily': {
        'task': 'src.workers.tasks.collect_tweets',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily
    },
    'calculate-metrics-weekly': {
        'task': 'src.workers.tasks.calculate_all_metrics',
        'schedule': crontab(day_of_week=1, hour=3, minute=0),  # Monday 3 AM
    },
}
```

## 10. Resources and Documentation

### Essential Reading
- FastAPI Documentation: https://fastapi.tiangolo.com/
- Hugging Face Transformers: https://huggingface.co/docs/transformers/
- pgvector Documentation: https://github.com/pgvector/pgvector
- Celery Documentation: https://docs.celeryproject.org/

### Community Resources
- r/MachineLearning
- Hugging Face Forums
- FastAPI Discord

---

**Last Updated**: 2025-10-23
**Next**: [08-case-studies.md](08-case-studies.md)
