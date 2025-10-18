# Analysis Modules Documentation

This document describes the analysis modules for NLP, embeddings, sentiment analysis, bias detection, and voting consistency analysis.

## Table of Contents
- [Overview](#overview)
- [Installation](#installation)
- [Modules](#modules)
- [Database Schema](#database-schema)
- [Examples](#examples)
- [API Reference](#api-reference)

---

## Overview

The analysis package provides comprehensive tools for analyzing legislative text and politician behavior:

- **Embeddings**: Vector representations of bills for similarity search
- **Sentiment Analysis**: Detect sentiment (positive/negative/neutral) in text
- **NLP Processing**: Entity extraction, POS tagging, complexity analysis
- **Bias Detection**: Identify political bias and loaded language
- **Consistency Analysis**: Track voting patterns and position changes

---

## Installation

### Basic Installation

```bash
# Install base requirements
pip install -r requirements.txt

# Install analysis dependencies
pip install -r requirements-analysis.txt
```

### Download Required Models

```bash
# spaCy language model
python -m spacy download en_core_web_sm

# Optional: Larger model with word vectors
python -m spacy download en_core_web_lg

# NLTK data
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"
```

### Database Setup

Run the analysis tables migration:

```bash
psql -U user -d congress -f app/db/migrations/002_analysis_tables.sql
```

---

## Modules

### 1. Embeddings (`analysis/embeddings.py`)

Generate vector representations of text for similarity search.

**Key Classes:**
- `EmbeddingsGenerator`: Main class for generating embeddings
- `BillEmbeddings`: Container for bill embedding data
- `SpeechEmbeddings`: Container for speech/statement embeddings

**Models Supported:**
- `all-MiniLM-L6-v2` (default): Fast, efficient, 384-dimensional
- `all-mpnet-base-v2`: Higher quality, 768-dimensional
- `nlpaueb/legal-bert-base-uncased`: Specialized for legal text

**Example:**
```python
from analysis.embeddings import EmbeddingsGenerator

# Initialize
generator = EmbeddingsGenerator(model_name='all-MiniLM-L6-v2')

# Generate embedding for a bill
bill_text = "A bill to provide healthcare..."
embedding = generator.encode_bill(bill_text, bill_id=123)

# Find similar bills
similar = generator.find_similar_bills(
    embedding.embedding_vector,
    all_bill_embeddings,
    top_k=5
)
```

### 2. Sentiment Analysis (`analysis/sentiment.py`)

Analyze sentiment in legislative text.

**Key Classes:**
- `SentimentAnalyzer`: Multi-model sentiment analyzer
- `SentimentScore`: Container for sentiment results

**Models Supported:**
- `vader`: Best for social media and political text (default)
- `textblob`: General-purpose sentiment
- `transformers`: Deep learning-based (DistilBERT)

**Example:**
```python
from analysis.sentiment import SentimentAnalyzer

# Initialize
analyzer = SentimentAnalyzer(models=['vader'])

# Analyze a bill
bill_text = "A bill to provide healthcare..."
score = analyzer.analyze(bill_text, text_id=123, text_type='bill')

print(f"Sentiment: {score.sentiment_label}")
print(f"Compound score: {score.compound_score}")
```

### 3. NLP Processing (`analysis/nlp_processor.py`)

Extract entities and linguistic features from text.

**Key Classes:**
- `NLPProcessor`: spaCy-based NLP processor
- `ProcessedText`: Container for NLP results
- `Entity`: Named entity representation

**Features:**
- Named Entity Recognition (NER)
- Part-of-speech tagging
- Dependency parsing
- Key phrase extraction
- Complexity analysis

**Example:**
```python
from analysis.nlp_processor import NLPProcessor

# Initialize
processor = NLPProcessor(model_name='en_core_web_sm')

# Process text
bill_text = "Senator Smith introduced a bill..."
result = processor.process(bill_text, text_id=123, text_type='bill')

# Access entities
for entity in result.entities:
    print(f"{entity.text}: {entity.label}")

# Extract political entities
political = processor.extract_political_entities(bill_text)
print(f"People: {[e.text for e in political['people']]}")
print(f"Organizations: {[e.text for e in political['organizations']]}")
```

### 4. Bias Detection (`analysis/bias_detector.py`)

Detect political bias and analyze framing.

**Key Classes:**
- `BiasDetector`: Political bias analyzer
- `BiasScore`: Container for bias analysis results

**Features:**
- Partisan language detection
- Loaded language identification
- Emotional appeal detection
- Objectivity scoring
- Framing analysis
- Rhetorical device detection

**Example:**
```python
from analysis.bias_detector import BiasDetector

# Initialize
detector = BiasDetector()

# Analyze text
statement = "We must fight corporate greed..."
score = detector.detect(statement, text_id=123, text_type='statement')

print(f"Overall bias: {score.overall_bias}")
print(f"Objectivity: {score.objectivity_score}")

# Analyze framing
framing = detector.analyze_framing(statement)
print(f"Problem frames: {framing['problem_frames']}")
```

### 5. Consistency Analysis (`analysis/consistency_analyzer.py`)

Analyze voting consistency and position changes.

**Key Classes:**
- `ConsistencyAnalyzer`: Voting pattern analyzer
- `ConsistencyScore`: Container for consistency results
- `VoteRecord`: Individual vote representation

**Features:**
- Overall voting consistency
- Party-line voting percentage
- Issue-specific consistency
- Position change detection
- Flip-flop identification
- Politician comparison
- Bipartisan score

**Example:**
```python
from analysis.consistency_analyzer import ConsistencyAnalyzer, VoteRecord
from datetime import datetime

# Initialize
analyzer = ConsistencyAnalyzer()

# Create vote records
votes = [
    VoteRecord(1, 101, 1, 'yes', datetime(2023, 1, 15), 'healthcare', 'yes'),
    VoteRecord(2, 102, 1, 'yes', datetime(2023, 2, 20), 'healthcare', 'yes'),
    # ... more votes
]

# Analyze consistency
score = analyzer.analyze_voting_consistency(
    person_id=1,
    votes=votes,
    party='Democrat'
)

print(f"Overall consistency: {score.overall_consistency:.2f}")
print(f"Party line voting: {score.party_line_voting:.2%}")
print(f"Position changes: {len(score.position_changes)}")
```

---

## Database Schema

### Analysis Tables

The `002_analysis_tables.sql` migration creates the following tables:

1. **bill_embeddings**: Store bill text embeddings
2. **speech_embeddings**: Store speech/statement embeddings
3. **sentiment_analysis**: Sentiment analysis results
4. **extracted_entities**: Named entities from text
5. **bias_analysis**: Political bias detection results
6. **consistency_analysis**: Voting consistency scores
7. **issue_consistency**: Per-issue consistency tracking
8. **position_changes**: Position change tracking
9. **bill_similarities**: Bill similarity scores
10. **text_complexity**: Text complexity metrics
11. **toxicity_analysis**: Hate speech/toxic language detection
12. **politician_comparisons**: Politician voting similarity

### Useful Views

- `latest_bill_sentiment`: Latest sentiment for each bill
- `latest_bill_bias`: Latest bias analysis for each bill
- `politician_consistency_summary`: Consistency summary for all politicians
- `top_similar_bills`: Bills with high similarity scores

---

## Examples

### Example 1: Find Similar Bills Using Embeddings

See `examples/embeddings_example.py` for a complete example of:
- Loading bills from database
- Generating embeddings
- Finding similar bills
- Storing results

Run with:
```bash
export DATABASE_URL="postgresql://user:pass@localhost:5432/congress"
python examples/embeddings_example.py
```

### Example 2: Complete Analysis Pipeline

See `examples/complete_analysis_pipeline.py` for a full pipeline that:
- Analyzes sentiment of bills
- Extracts entities
- Detects political bias
- Generates embeddings
- Stores all results

Run with:
```bash
export DATABASE_URL="postgresql://user:pass@localhost:5432/congress"
python examples/complete_analysis_pipeline.py
```

### Example 3: Query Analysis Results

```sql
-- Get bills with negative sentiment
SELECT
    b.bill_number,
    b.title,
    s.sentiment_label,
    s.compound_score
FROM bills b
JOIN sentiment_analysis s ON b.id = s.text_id AND s.text_type = 'bill'
WHERE s.sentiment_label = 'negative'
ORDER BY s.compound_score;

-- Find politically biased bills
SELECT
    b.bill_number,
    b.title,
    ba.overall_bias,
    ba.bias_score,
    ba.objectivity_score
FROM bills b
JOIN bias_analysis ba ON b.id = ba.text_id AND ba.text_type = 'bill'
WHERE ba.overall_bias IN ('left', 'right')
ORDER BY ABS(ba.bias_score) DESC;

-- Get most similar bill pairs
SELECT * FROM top_similar_bills LIMIT 10;

-- Get politician consistency summary
SELECT * FROM politician_consistency_summary
WHERE current_party = 'Democrat'
ORDER BY overall_consistency DESC;

-- Find entities mentioned in bills
SELECT
    b.bill_number,
    ee.entity_text,
    ee.entity_label
FROM bills b
JOIN extracted_entities ee ON b.id = ee.text_id AND ee.text_type = 'bill'
WHERE ee.entity_label = 'PERSON'
ORDER BY b.bill_number;
```

---

## API Reference

### EmbeddingsGenerator

```python
class EmbeddingsGenerator:
    def __init__(self, model_name: str = None, device: str = None)
    def encode(self, texts: List[str], batch_size: int = 32) -> np.ndarray
    def encode_bill(self, bill_text: str, bill_id: int) -> BillEmbeddings
    def encode_bills_batch(self, bills: List[Tuple[int, str]]) -> List[BillEmbeddings]
    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float
    def find_similar_bills(self, query_embedding: np.ndarray, bill_embeddings: List[BillEmbeddings], top_k: int = 10) -> List[Tuple[int, float]]
```

### SentimentAnalyzer

```python
class SentimentAnalyzer:
    def __init__(self, models: List[str] = None)
    def analyze(self, text: str, text_id: int = None, text_type: str = None) -> SentimentScore
    def analyze_batch(self, texts: List[str], text_ids: List[int] = None) -> List[SentimentScore]
    def get_aggregate_sentiment(self, scores: List[SentimentScore]) -> Dict[str, Any]
```

### NLPProcessor

```python
class NLPProcessor:
    def __init__(self, model_name: str = None, disable: List[str] = None)
    def process(self, text: str, text_id: int = None, text_type: str = None) -> ProcessedText
    def extract_entities_by_type(self, text: str, entity_types: List[str] = None) -> List[Entity]
    def extract_political_entities(self, text: str) -> Dict[str, List[Entity]]
    def get_key_phrases(self, text: str, top_n: int = 10) -> List[str]
    def analyze_complexity(self, text: str) -> Dict[str, float]
```

### BiasDetector

```python
class BiasDetector:
    def __init__(self, use_transformer: bool = False)
    def detect(self, text: str, text_id: int = None, text_type: str = None) -> BiasScore
    def analyze_framing(self, text: str) -> Dict[str, Any]
    def detect_rhetorical_devices(self, text: str) -> List[Dict[str, str]]
```

### ConsistencyAnalyzer

```python
class ConsistencyAnalyzer:
    def __init__(self)
    def analyze_voting_consistency(self, person_id: int, votes: List[VoteRecord], party: str = None) -> ConsistencyScore
    def calculate_bipartisan_score(self, person_id: int, sponsored_bills: List[Dict[str, Any]]) -> float
    def compare_politicians(self, person1_id: int, person2_id: int, votes1: List[VoteRecord], votes2: List[VoteRecord]) -> Dict[str, Any]
```

---

## Performance Considerations

### Embeddings
- **Model Size**: `all-MiniLM-L6-v2` (80MB) is fast, `all-mpnet-base-v2` (420MB) is more accurate
- **Batch Size**: Use batch_size=32 for CPU, 64+ for GPU
- **GPU**: Set device='cuda' for 10-100x speedup on large datasets

### NLP Processing
- **Model Choice**: `en_core_web_sm` (12MB) for speed, `en_core_web_lg` (560MB) for accuracy
- **Disable Unused**: Disable unused pipeline components with `disable=['parser', 'ner']`
- **Text Length**: Truncate very long texts (>10K chars) for faster processing

### Database
- **Indexes**: Ensure proper indexes on foreign keys and frequently queried columns
- **Vector Search**: Consider pgvector extension or external vector database for large-scale similarity search
- **Batch Inserts**: Use batch inserts for storing many analysis results

---

## Future Enhancements

1. **Advanced Models**
   - Fine-tuned BERT models for political text
   - Domain-specific embeddings for legal text
   - Multi-lingual support

2. **Additional Analysis**
   - Topic modeling (LDA, BERTopic)
   - Argument mining
   - Fact-checking integration
   - Disinformation detection

3. **Visualization**
   - Interactive dashboards
   - Network graphs of bill similarities
   - Voting pattern visualizations
   - Time-series analysis of positions

4. **Integration**
   - Real-time analysis via API
   - Scheduled batch processing
   - Alert system for position changes
   - Export to various formats

---

## Support

For issues or questions:
1. Check the example files
2. Review the module docstrings
3. Consult the database schema
4. Open an issue on GitHub

---

*Last Updated: 2025-10-14*
*Part of the OpenDiscourse.net project*
