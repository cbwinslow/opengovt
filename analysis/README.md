# Analysis Modules

This directory contains NLP and machine learning analysis modules for legislative data.

## Modules

### 1. embeddings.py
Generate vector representations of bills and speeches for similarity search.
- **Models**: sentence-transformers
- **Use cases**: Find similar bills, topic clustering, semantic search

### 2. sentiment.py
Analyze sentiment in legislative text.
- **Models**: VADER, TextBlob, transformers
- **Use cases**: Detect positive/negative tone, emotional analysis

### 3. nlp_processor.py
Extract entities and linguistic features from text.
- **Models**: spaCy
- **Use cases**: Named entity recognition, part-of-speech tagging, complexity analysis

### 4. bias_detector.py
Detect political bias and analyze framing.
- **Use cases**: Identify partisan language, measure objectivity, framing analysis

### 5. consistency_analyzer.py
Analyze voting patterns and position changes.
- **Use cases**: Voting consistency, party-line voting, flip-flop detection, politician comparison

## Quick Usage

```python
# Embeddings
from analysis.embeddings import EmbeddingsGenerator
gen = EmbeddingsGenerator()
emb = gen.encode_bill("bill text...", bill_id=1)

# Sentiment
from analysis.sentiment import SentimentAnalyzer
analyzer = SentimentAnalyzer()
score = analyzer.analyze("text...", text_id=1)

# NLP
from analysis.nlp_processor import NLPProcessor
processor = NLPProcessor()
result = processor.process("text...", text_id=1)

# Bias
from analysis.bias_detector import BiasDetector
detector = BiasDetector()
score = detector.detect("text...", text_id=1)

# Consistency
from analysis.consistency_analyzer import ConsistencyAnalyzer
analyzer = ConsistencyAnalyzer()
score = analyzer.analyze_voting_consistency(person_id=1, votes=votes)
```

## Installation

```bash
# Install dependencies
pip install -r requirements-analysis.txt

# Download models
python -m spacy download en_core_web_sm
```

## Documentation

See `../docs/ANALYSIS_MODULES.md` for complete documentation.

## Examples

See `../examples/` for working examples:
- `embeddings_example.py`: Complete embeddings workflow
- `complete_analysis_pipeline.py`: Full analysis pipeline
